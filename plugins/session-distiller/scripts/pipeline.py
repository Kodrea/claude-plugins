#!/usr/bin/env python3
"""
Session Distiller Pipeline (plugin edition)

Processes Claude Code session data for a project, strips noise,
batches into context-sized chunks, and prepares analysis prompts.

"Local" is determined by **path existence**, not by a machine label. For each
project in the registry, if its `~/.claude/projects/<id>/` path exists on this
host, it's considered local. This avoids a footgun where `socket.gethostname()`
(e.g. `codyserban.local`) doesn't match the human-readable `machine` label
(e.g. `mac-mini`) in projects.json. The `machine` field is kept as metadata
for error messages and manifests but is NOT used for filter logic.

Projects are resolved against a bundled registry or a user override at
~/.claude/session-distiller/projects.json. Per-machine labelling is stored
in ~/.claude/session-distiller/config.json purely for manifest/error-message
metadata — no filtering depends on it.

This version runs LOCALLY ONLY — it never shells out to SSH/SCP. Each machine
installs the plugin and distills its own sessions.

Usage:
  # By project name (fuzzy matched from projects.json, local-machine only)
  python3 pipeline.py voicemode ios
  python3 pipeline.py dell poweredge
  python3 pipeline.py orin nano --top 5

  # By explicit path
  python3 pipeline.py --project ~/.claude/projects/-home-cody-Projects-hardware-dell-poweredge

  # List local projects (default filter)
  python3 pipeline.py --list

  # List every project in the registry regardless of machine
  python3 pipeline.py --list-all

  # Print the resolved config (machine, registry source)
  python3 pipeline.py --config
"""

import argparse
import json
import os
import socket
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
STRIP_SCRIPT = SCRIPT_DIR / "strip.py"
BUNDLED_PROJECTS_FILE = SCRIPT_DIR / "projects.json"

# User-level config / override locations (outside the plugin install dir so
# upgrades and uninstalls never clobber them).
USER_CONFIG_DIR = Path.home() / ".claude" / "session-distiller"
USER_CONFIG_FILE = USER_CONFIG_DIR / "config.json"
USER_PROJECTS_FILE = USER_CONFIG_DIR / "projects.json"

MAX_BATCH_BYTES = 800 * 1024  # ~800KB per batch, fits in ~200K tokens


def load_config():
    """Load per-machine config. First run: auto-create with detected hostname."""
    if USER_CONFIG_FILE.exists():
        try:
            with open(USER_CONFIG_FILE) as f:
                cfg = json.load(f)
            if not isinstance(cfg, dict):
                cfg = {}
        except Exception:
            cfg = {}
    else:
        cfg = {}

    if 'local_machine' not in cfg or not cfg['local_machine']:
        # Detect from hostname. User can edit config.json afterwards.
        detected = os.environ.get('SESSION_DISTILLER_MACHINE') or socket.gethostname() or 'unknown'
        cfg['local_machine'] = detected
        try:
            USER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(USER_CONFIG_FILE, 'w') as f:
                json.dump(cfg, f, indent=2)
                f.write('\n')
            print(f'[distiller] First run: wrote {USER_CONFIG_FILE} with local_machine="{detected}"', file=sys.stderr)
        except Exception as e:
            print(f'[distiller] WARNING: could not write {USER_CONFIG_FILE}: {e}', file=sys.stderr)

    return cfg


def projects_file_in_use():
    """Prefer user override at ~/.claude/session-distiller/projects.json, else bundled."""
    if USER_PROJECTS_FILE.exists():
        return USER_PROJECTS_FILE
    return BUNDLED_PROJECTS_FILE


def load_projects():
    """Load the project registry from whichever projects.json is active."""
    pf = projects_file_in_use()
    if not pf.exists():
        return []
    try:
        with open(pf) as f:
            data = json.load(f)
    except Exception as e:
        print(f'[distiller] WARNING: could not parse {pf}: {e}', file=sys.stderr)
        return []
    return data.get('projects', [])


def is_local(project, config=None):
    """Return True if the project's `~/.claude/projects/<id>/` path exists on this host.

    Deliberately uses path existence rather than `project['machine']` label matching,
    so the plugin works on any host without requiring that `socket.gethostname()`
    equal the human-readable `machine` field in projects.json. `config` is accepted
    for backwards-compatible call sites but not consulted.
    """
    path = project.get('path', '')
    if not path:
        return False
    return os.path.exists(os.path.expanduser(path))


def resolve_project(query_words, config):
    """Fuzzy-match a project from query words. Only local-machine projects are searched.

    Returns (name, path, skip_reason, project) or None.
    """
    all_projects = load_projects()
    if not all_projects:
        return None

    projects = [p for p in all_projects if is_local(p, config)]
    if not projects:
        return None

    query = ' '.join(query_words).lower().strip()
    if not query:
        return None

    # Exact name match first
    for p in projects:
        if p['name'].lower() == query:
            return p['name'], p['path'], p.get('skip_reason'), p

    # Alias match
    best_match = None
    best_score = 0
    for p in projects:
        for alias in p.get('aliases', []):
            alias_lower = alias.lower()
            # Exact alias match
            if alias_lower == query:
                return p['name'], p['path'], p.get('skip_reason'), p
            # Partial match — all query words appear in alias or name
            words = query.split()
            name_and_aliases = (p['name'] + ' ' + ' '.join(p.get('aliases', []))).lower()
            matches = sum(1 for w in words if w in name_and_aliases)
            score = matches / len(words) if words else 0
            if score > best_score:
                best_score = score
                best_match = p

    if best_match and best_score >= 0.5:
        return best_match['name'], best_match['path'], best_match.get('skip_reason'), best_match

    return None


def find_non_local_match(query_words):
    """For the error path: does this query match anything on ANOTHER machine?"""
    all_projects = load_projects()
    query = ' '.join(query_words).lower().strip()
    if not query:
        return None
    for p in all_projects:
        if p['name'].lower() == query:
            return p
        for alias in p.get('aliases', []):
            if alias.lower() == query:
                return p
    return None


def resolve_group(query_words, config):
    """If query matches a group name, return local members only.

    Returns (group_name, [(name, path), ...]) or None.

    Behaviour trace:
      - No group with that name → returns None (caller falls through to
        resolve_project, then find_non_local_group, then generic error).
      - Group exists but no members have locally-existing paths → returns None
        (same fall-through). find_non_local_group will then detect it and
        print a machine-specific error ("group X has members on machines {...},
        run /distill there").
      - Group exists with at least one local member → returns the local subset.
    """
    all_projects = load_projects()
    query = ' '.join(query_words).lower().strip()
    members = [p for p in all_projects if p.get('group', '').lower() == query]
    if not members:
        return None
    members = [p for p in members if is_local(p, config)]
    if not members:
        return None
    group_name = members[0]['group']
    return group_name, [(p['name'], p['path']) for p in members]


def find_non_local_group(query_words):
    """For the error path: does this query match a group that has ONLY non-local members?

    Returns a list of dicts (raw project entries) or None. Used so we can print a
    helpful "this group lives on machine X" error instead of a generic not-found.
    """
    all_projects = load_projects()
    query = ' '.join(query_words).lower().strip()
    if not query:
        return None
    members = [p for p in all_projects if p.get('group', '').lower() == query]
    if not members:
        return None
    # If any member was local, resolve_group would have succeeded — by the time
    # we get here, none are local. Return the full non-local member list so the
    # error message can name the remote machines.
    return members


def list_projects(config, show_all=False):
    """Print registered projects. By default only projects whose paths exist on this host."""
    all_projects = load_projects()
    if not all_projects:
        pf = projects_file_in_use()
        print(f'No projects registered in {pf}.')
        print('Edit that file or create ~/.claude/session-distiller/projects.json to override.')
        return

    if show_all:
        projects = all_projects
        header_note = '(all machines, ? = path missing on this host)'
    else:
        projects = [p for p in all_projects if is_local(p)]
        header_note = '(paths that exist on this host)'

    print(f'Registry: {projects_file_in_use()}')
    print(f'Showing {len(projects)} of {len(all_projects)} projects {header_note}')
    print()
    print(f'{"Name":25s} {"Machine":12s} {"Aliases"}')
    print('-' * 72)
    for p in projects:
        skip = ' [SKIP]' if p.get('skip_reason') else ''
        missing = '' if is_local(p) else ' [missing]'
        aliases = ', '.join(p.get('aliases', []))
        print(f'{p["name"]:25s} {p.get("machine","?"):12s} {aliases}{skip}{missing}')

    if not show_all and len(projects) < len(all_projects):
        print()
        print(f'(use --list-all to see all {len(all_projects)} projects including other machines)')


def print_config(config):
    """Print the resolved runtime config for debugging."""
    print(f'local_machine:   {config.get("local_machine", "?")}  (metadata only — not used for filtering)')
    print(f'filter method:   path existence ({"~/.claude/projects/<id>/ must exist on this host"})')
    print(f'config file:     {USER_CONFIG_FILE} ({"exists" if USER_CONFIG_FILE.exists() else "will be created on next run"})')
    print(f'projects file:   {projects_file_in_use()}')
    print(f'bundled registry:{BUNDLED_PROJECTS_FILE}')
    print(f'user override:   {USER_PROJECTS_FILE} ({"active" if USER_PROJECTS_FILE.exists() else "not set"})')
    print(f'strip script:    {STRIP_SCRIPT}')
    all_projects = load_projects()
    local_count = sum(1 for p in all_projects if is_local(p))
    print(f'projects:        {local_count} local (by path existence) / {len(all_projects)} total')


ANALYSIS_PROMPT = """read {batch_file}. This file contains {session_count} stripped Claude Code sessions from the project "{project_name}" spanning {date_range}. These are real conversations between a user and an AI assistant.

This is a conversation between a user and an AI assistant — what do you notice about how it went? Look across all sessions for:
- Patterns that repeat (scope creep, premature success claims, ignored concerns, wasted actions)
- Moments where the interaction went sideways — quote the user message and assistant response
- Patterns in timing (late night sessions, long gaps, high-churn periods)
- What went well that should be preserved

For each pattern found, identify: the pattern type, frequency across sessions, specific quoted moments, and the single highest-impact change (user behavior, CLAUDE.md rule, skill, or architectural fix). Rank by frequency and impact."""

FOLLOWUP_PROMPT = """For each issue you identified, go back to the conversation and find the exact moments — quote the user message and the assistant response that followed. Identify the pattern type (scope creep, ignored concern, wasteful action, missing diagnostic step, premature assertion, stale memory). For patterns that could recur in future sessions, suggest the single highest-impact change — whether that's a user behavior change, a CLAUDE.md rule, a skill, a hook, or an architectural change. Rank by impact."""


def get_last_timestamp(session_path):
    """Return ISO-8601 timestamp of the last jsonl entry with a 'timestamp'
    field, or None. Reads the file tail (escalating 8KB -> 64KB) so large
    sessions don't pay full-file I/O. Walks backward past sentinel records
    like 'last-prompt' that lack timestamps.
    """
    try:
        size = os.path.getsize(session_path)
        if size == 0:
            return None
        for buf_size in (8192, 65536):
            seek_pos = max(0, size - buf_size)
            with open(session_path, 'rb') as f:
                f.seek(seek_pos)
                chunk = f.read().decode('utf-8', errors='replace')
            lines = [ln for ln in chunk.splitlines() if ln.strip()]
            for line in reversed(lines):
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ts = obj.get('timestamp')
                if ts:
                    return ts
            if seek_pos == 0:
                break  # already read the whole file
        return None
    except Exception:
        return None


def list_sessions(project_path):
    """List all session JSONL files in a local project, sorted by size desc."""
    project_path = Path(os.path.expanduser(project_path))
    if not project_path.exists():
        return []
    sessions = []
    for f in sorted(project_path.glob("*.jsonl"), key=lambda p: p.stat().st_size, reverse=True):
        sessions.append({
            'path': str(f),
            'fname': f.name,
            'size': f.stat().st_size,
        })
    return sessions


def copy_session(session_path, dest_path):
    """Copy a session file locally."""
    subprocess.run(["cp", os.path.expanduser(session_path), dest_path])


def strip_session(raw_path, stripped_path):
    """Run the strip script on a session file."""
    result = subprocess.run(
        [sys.executable, str(STRIP_SCRIPT), raw_path, stripped_path],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"  Strip failed: {result.stderr}")
        return None
    # Parse output for stats
    for line in result.stdout.split('\n'):
        if 'Size:' in line:
            return line.strip()
    return result.stdout.strip()


def get_session_meta(stripped_path):
    """Extract basic metadata from a stripped session."""
    with open(stripped_path) as f:
        first_line = f.readline()
        try:
            meta = json.loads(first_line)
        except:
            return {}

    # Find date range from timestamps
    timestamps = []
    f_obj = open(stripped_path)
    for line in f_obj:
        try:
            d = json.loads(line)
            ts = d.get('timestamp', '')
            if ts:
                timestamps.append(ts)
        except:
            continue
    f_obj.close()

    if timestamps:
        timestamps.sort()
        meta['first_ts'] = timestamps[0]
        meta['last_ts'] = timestamps[-1]

    meta['file_size'] = os.path.getsize(stripped_path)
    return meta


def batch_sessions(stripped_files, max_bytes=MAX_BATCH_BYTES):
    """Group stripped sessions into batches that fit in context."""
    batches = []
    current_batch = []
    current_size = 0

    for sf in stripped_files:
        size = os.path.getsize(sf)
        if current_size + size > max_bytes and current_batch:
            batches.append(current_batch)
            current_batch = []
            current_size = 0
        current_batch.append(sf)
        current_size += size

    if current_batch:
        batches.append(current_batch)

    return batches


def create_batch_file(batch_files, batch_path, batch_num):
    """Merge stripped sessions into a single batch file with dividers."""
    with open(batch_path, 'w') as out:
        for i, sf in enumerate(batch_files):
            fname = os.path.basename(sf)
            size_kb = os.path.getsize(sf) // 1024

            # Get first user message for context
            first_msg = ""
            with open(sf) as f:
                for line in f:
                    try:
                        d = json.loads(line)
                        if d.get('type') == 'user':
                            content = d.get('content', '')
                            if isinstance(content, list):
                                for block in content:
                                    if isinstance(block, dict) and block.get('type') == 'text':
                                        text = block.get('text', '').strip()
                                        if text and not text.startswith('[Request') and not text.startswith('<'):
                                            first_msg = text[:150]
                                            break
                            elif isinstance(content, str) and content.strip():
                                first_msg = content[:150]
                            if first_msg:
                                break
                    except:
                        continue

            meta = get_session_meta(sf)
            date = meta.get('first_ts', 'unknown')[:10]

            divider = {
                'type': 'divider',
                'note': f'=== SESSION {i+1}: {date} | {size_kb}KB | {first_msg[:100]}'
            }
            out.write(json.dumps(divider) + '\n')

            with open(sf) as f:
                for line in f:
                    out.write(line)

    return os.path.getsize(batch_path)


def main():
    parser = argparse.ArgumentParser(description='Session Distiller Pipeline (local-only)')
    parser.add_argument('query', nargs='*', help='Project name to fuzzy-match (e.g., "voicemode v2", "dell")')
    parser.add_argument('--project', default=None, help='Explicit path to .claude/projects/<project-id>/')
    parser.add_argument('--output', default=None, help='Output directory (default: ~/distiller-runs/<project-name>)')
    parser.add_argument('--top', type=int, default=None, help='Only process N largest sessions')
    parser.add_argument('--min-size', type=int, default=50000, help='Skip sessions smaller than N bytes (default: 50KB)')
    parser.add_argument('--recent', type=float, default=None, metavar='HOURS',
                        help='Keep only sessions active within the last HOURS (float OK, e.g. 0.5 = 30min; --top still picks largest by size within the window)')
    parser.add_argument('--name', default=None, help='Human-friendly project name')
    parser.add_argument('--list', action='store_true', help='List projects registered for this machine')
    parser.add_argument('--list-all', action='store_true', help='List every project in the registry (all machines)')
    parser.add_argument('--config', action='store_true', help='Print the resolved runtime config and exit')
    args = parser.parse_args()

    # Always load config first so the first-run init happens before any action.
    config = load_config()

    if args.config:
        print_config(config)
        sys.exit(0)

    if args.list or args.list_all:
        list_projects(config, show_all=args.list_all)
        sys.exit(0)

    # Resolve project from query or explicit flags
    if args.query and not args.project:
        # Try group match first
        group = resolve_group(args.query, config)
        if group:
            group_name, members = group
            args.name = group_name
            args._multi_paths = [m[1] for m in members]
            print(f'Resolved group: {group_name} ({len(members)} local projects)')
            for name, path in members:
                print(f'  - {name}: {path}')
        else:
            result = resolve_project(args.query, config)
            if result is None:
                query_str = " ".join(args.query)
                print(f'No project matched: "{query_str}"')
                # Was this actually a group name with no local members?
                non_local_group = find_non_local_group(args.query)
                if non_local_group:
                    machines = sorted({p.get('machine', '?') for p in non_local_group})
                    print(f'Group "{query_str}" has {len(non_local_group)} members on machine(s): {", ".join(machines)}')
                    print('None of those paths exist on this host. Install and run /distill on that machine.')
                    sys.exit(1)
                # Or a single-project non-local match we hid?
                non_local = find_non_local_match(args.query)
                if non_local:
                    other_machine = non_local.get('machine', '?')
                    print(f'Found on machine "{other_machine}": {non_local["name"]}')
                    print(f'This plugin runs local-only. Install and run /distill on that machine.')
                else:
                    print('Use --list to see projects for this machine, --list-all to see every registered project,')
                    print('or --project to pass an explicit path.')
                sys.exit(1)
            resolved_name, resolved_path, skip_reason, _proj = result
            if skip_reason:
                print(f'Project "{resolved_name}" is marked as skip: {skip_reason}')
                print('Use --project with explicit path to override.')
                sys.exit(1)
            args.project = resolved_path
            if not args.name:
                args.name = resolved_name
            print(f'Resolved: {resolved_name} -> {args.project}')
    elif not args.project:
        parser.print_help()
        sys.exit(1)

    # Derive project name
    project_name = args.name or os.path.basename(args.project.rstrip('/'))
    project_name_short = project_name.replace('-home-cody-', '').replace('-Users-codyserban-', '')

    # Output directory (outside the plugin install dir — survives uninstall)
    if args.output:
        output_dir = Path(os.path.expanduser(args.output))
    else:
        run_id = datetime.now().strftime('%Y%m%d-%H%M')
        output_dir = Path.home() / 'distiller-runs' / f'{project_name_short}_{run_id}'

    output_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = output_dir / 'raw'
    stripped_dir = output_dir / 'stripped'
    batch_dir = output_dir / 'batches'
    raw_dir.mkdir(exist_ok=True)
    stripped_dir.mkdir(exist_ok=True)
    batch_dir.mkdir(exist_ok=True)

    print(f'Project: {project_name_short}')
    print(f'Output:  {output_dir}')
    print()

    # Step 1: List sessions
    print('Step 1: Listing sessions...')
    if hasattr(args, '_multi_paths'):
        sessions = []
        for p in args._multi_paths:
            sessions.extend(list_sessions(p))
        sessions.sort(key=lambda s: s['size'], reverse=True)
    else:
        sessions = list_sessions(args.project)
    sessions = [s for s in sessions if s['size'] >= args.min_size]

    # --recent filter: drop sessions whose last timestamped entry is older than cutoff
    if args.recent is not None:
        if args.recent < 0:
            print(f'error: --recent must be >= 0 (got {args.recent})', file=sys.stderr)
            sys.exit(2)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=args.recent)
        kept, out_of_window, no_ts, parse_err = [], 0, 0, 0
        for s in sessions:
            ts_str = get_last_timestamp(s['path'])
            if not ts_str:
                no_ts += 1
                continue
            try:
                ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
            except ValueError:
                parse_err += 1
                continue
            if ts >= cutoff:
                kept.append(s)
            else:
                out_of_window += 1
        print(f'  --recent {args.recent}h: kept {len(kept)}, out-of-window {out_of_window}, no-timestamp {no_ts}, parse-err {parse_err}')
        if no_ts + parse_err > len(kept):
            print('  WARNING: most sessions had no parseable timestamp — possible schema drift', file=sys.stderr)
        sessions = kept

    if args.top:
        sessions = sessions[:args.top]

    total_raw = sum(s['size'] for s in sessions)
    print(f'  Found {len(sessions)} sessions ({total_raw / 1048576:.1f}MB total)')
    print()

    if not sessions:
        print('No sessions to process (after min-size filter). Exiting.')
        sys.exit(0)

    # Step 2: Copy and strip
    print('Step 2: Copying and stripping sessions...')
    stripped_files = []
    session_stats = []

    for i, s in enumerate(sessions):
        short_id = s['fname'][:8]
        raw_path = str(raw_dir / s['fname'])
        stripped_path = str(stripped_dir / s['fname'])

        print(f'  [{i+1}/{len(sessions)}] {short_id} ({s["size"]//1024}KB)', end=' ')
        sys.stdout.flush()

        copy_session(s['path'], raw_path)
        stats = strip_session(raw_path, stripped_path)

        if os.path.exists(stripped_path) and os.path.getsize(stripped_path) > 100:
            stripped_files.append(stripped_path)
            meta = get_session_meta(stripped_path)
            session_stats.append({
                'id': short_id,
                'raw_size': s['size'],
                'stripped_size': os.path.getsize(stripped_path),
                'date': meta.get('first_ts', 'unknown')[:10],
            })
            print(f'-> {os.path.getsize(stripped_path)//1024}KB')
        else:
            print('-> SKIPPED (empty after strip)')

        # Clean up raw to save disk
        if os.path.exists(raw_path):
            os.remove(raw_path)

    # Remove raw dir if empty
    try:
        raw_dir.rmdir()
    except:
        pass

    total_stripped = sum(s['stripped_size'] for s in session_stats)
    if total_raw:
        print(f'\n  Stripped: {total_raw/1048576:.1f}MB -> {total_stripped/1048576:.1f}MB ({(1-total_stripped/total_raw)*100:.0f}% reduction)')

    # F1 safety: if strip yielded essentially nothing, something is off (schema drift,
    # wrong project dir, etc.). Warn loudly rather than silently produce empty batches.
    if not session_stats:
        print('\n  WARNING: no sessions survived the strip step. Possible causes: empty project,', file=sys.stderr)
        print('           all sessions below --min-size threshold, or session JSONL schema drift.', file=sys.stderr)
    elif total_raw and total_stripped and (total_stripped / total_raw) < 0.02:
        print(f'\n  WARNING: stripped size is {total_stripped/total_raw*100:.2f}% of raw —', file=sys.stderr)
        print('           unusually aggressive reduction may indicate session JSONL schema drift.', file=sys.stderr)
        print('           Spot-check one file in stripped/ before trusting the analysis output.', file=sys.stderr)
    print()

    # Step 3: Batch
    print('Step 3: Batching sessions...')
    # Sort by date for chronological batches
    stripped_files_with_meta = []
    for sf in stripped_files:
        meta = get_session_meta(sf)
        stripped_files_with_meta.append((meta.get('first_ts', 'zzz'), sf))
    stripped_files_with_meta.sort()
    stripped_files = [sf for _, sf in stripped_files_with_meta]

    batches = batch_sessions(stripped_files)
    print(f'  {len(batches)} batches created')

    for i, batch in enumerate(batches):
        batch_path = str(batch_dir / f'batch-{i+1:02d}.jsonl')
        batch_size = create_batch_file(batch, batch_path, i+1)
        print(f'  Batch {i+1}: {len(batch)} sessions, {batch_size//1024}KB')

    # Step 4: Generate analysis prompts
    print('\nStep 4: Generating analysis prompts...')

    # Date range across all sessions
    all_dates = [s['date'] for s in session_stats if s['date'] != 'unknown']
    if all_dates:
        date_range = f"{min(all_dates)} to {max(all_dates)}"
    else:
        date_range = "unknown"

    prompts_file = output_dir / 'prompts.md'
    with open(prompts_file, 'w') as f:
        f.write(f'# Distiller Prompts: {project_name_short}\n\n')
        f.write(f'Date range: {date_range}\n')
        f.write(f'Sessions: {len(session_stats)}\n')
        f.write(f'Batches: {len(batches)}\n\n')

        for i, batch in enumerate(batches):
            batch_path = str(batch_dir / f'batch-{i+1:02d}.jsonl')
            batch_size = os.path.getsize(batch_path)

            prompt = ANALYSIS_PROMPT.format(
                batch_file=batch_path,
                session_count=len(batch),
                project_name=project_name_short,
                date_range=date_range,
            )

            f.write(f'## Batch {i+1} ({len(batch)} sessions, {batch_size//1024}KB)\n\n')
            f.write(f'### Initial prompt\n```\n{prompt}\n```\n\n')
            f.write(f'### Follow-up prompt\n```\n{FOLLOWUP_PROMPT}\n```\n\n')

    # Step 5: Write manifest
    manifest = {
        'project': project_name_short,
        'machine': config.get('local_machine'),
        'date_range': date_range,
        'generated': datetime.now().isoformat()[:19],
        'sessions': session_stats,
        'batches': [
            {
                'file': f'batches/batch-{i+1:02d}.jsonl',
                'session_count': len(batch),
                'size': os.path.getsize(str(batch_dir / f'batch-{i+1:02d}.jsonl')),
            }
            for i, batch in enumerate(batches)
        ],
        'total_raw_bytes': total_raw,
        'total_stripped_bytes': total_stripped,
        'compression_ratio': round(total_raw / total_stripped, 1) if total_stripped else 0,
    }
    with open(output_dir / 'manifest.json', 'w') as f:
        json.dump(manifest, f, indent=2)

    print(f'\nDone. Output in {output_dir}')
    print(f'\nTo analyze, start a Claude session and paste the prompt from:')
    print(f'  {prompts_file}')

    # Print summary
    print(f'\n--- Summary ---')
    print(f'Project:     {project_name_short}')
    print(f'Sessions:    {len(session_stats)}')
    print(f'Date range:  {date_range}')
    print(f'Raw size:    {total_raw/1048576:.1f}MB')
    print(f'Stripped:    {total_stripped/1048576:.1f}MB')
    print(f'Compression: {manifest["compression_ratio"]}x')
    print(f'Batches:     {len(batches)}')


if __name__ == '__main__':
    main()
