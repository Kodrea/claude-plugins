#!/usr/bin/env python3
"""
Session Distiller Pipeline

Processes Claude Code session data for a project, strips noise,
batches into context-sized chunks, and prepares analysis prompts.

Usage:
  # By project name (fuzzy matched from projects.json)
  python3 pipeline.py voicemode ios
  python3 pipeline.py dell poweredge
  python3 pipeline.py orin nano --top 5

  # By explicit path (local)
  python3 pipeline.py --project ~/.claude/projects/-home-cody-Projects-hardware-dell-poweredge

  # By explicit path (remote)
  python3 pipeline.py --remote codyserban@100.81.185.119 \
    --project ~/.claude/projects/-Users-codyserban-Projects-iOS-apps-voicemode-ios

  # List registered projects
  python3 pipeline.py --list
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
STRIP_SCRIPT = SCRIPT_DIR / "strip.py"
PROJECTS_FILE = SCRIPT_DIR / "projects.json"
MAX_BATCH_BYTES = 800 * 1024  # ~800KB per batch, fits in ~200K tokens


def load_projects():
    """Load the project registry."""
    if not PROJECTS_FILE.exists():
        return []
    with open(PROJECTS_FILE) as f:
        data = json.load(f)
    return data.get('projects', [])


def resolve_project(query_words):
    """Fuzzy-match a project from query words. Returns (name, remote_or_None, path) or None."""
    projects = load_projects()
    if not projects:
        return None

    query = ' '.join(query_words).lower().strip()
    if not query:
        return None

    # Exact name match first
    for p in projects:
        if p['name'].lower() == query:
            remote = p.get('remote') if p.get('machine') != 'pop-os' else None
            return p['name'], remote, p['path'], p.get('skip_reason')

    # Alias match
    best_match = None
    best_score = 0
    for p in projects:
        for alias in p.get('aliases', []):
            alias_lower = alias.lower()
            # Exact alias match
            if alias_lower == query:
                remote = p.get('remote') if p.get('machine') != 'pop-os' else None
                return p['name'], remote, p['path'], p.get('skip_reason')
            # Partial match — all query words appear in alias or name
            words = query.split()
            name_and_aliases = (p['name'] + ' ' + ' '.join(p.get('aliases', []))).lower()
            matches = sum(1 for w in words if w in name_and_aliases)
            score = matches / len(words) if words else 0
            if score > best_score:
                best_score = score
                best_match = p

    if best_match and best_score >= 0.5:
        remote = best_match.get('remote') if best_match.get('machine') != 'pop-os' else None
        return best_match['name'], remote, best_match['path'], best_match.get('skip_reason')

    return None


def resolve_group(query_words):
    """If query matches a group name, return all members."""
    projects = load_projects()
    query = ' '.join(query_words).lower().strip()
    members = [p for p in projects if p.get('group', '').lower() == query]
    if not members:
        return None
    group_name = members[0]['group']
    results = []
    for p in members:
        remote = p.get('remote') if p.get('machine') != 'pop-os' else None
        results.append((p['name'], remote, p['path']))
    return group_name, results


def list_projects():
    """Print all registered projects."""
    projects = load_projects()
    if not projects:
        print('No projects registered. Add them to projects.json.')
        return

    print(f'{"Name":25s} {"Machine":10s} {"Aliases"}')
    print('-' * 70)
    for p in projects:
        skip = ' [SKIP]' if p.get('skip_reason') else ''
        aliases = ', '.join(p.get('aliases', []))
        print(f'{p["name"]:25s} {p.get("machine","?"):10s} {aliases}{skip}')

ANALYSIS_PROMPT = """read {batch_file}. This file contains {session_count} stripped Claude Code sessions from the project "{project_name}" spanning {date_range}. These are real conversations between a user and an AI assistant.

This is a conversation between a user and an AI assistant — what do you notice about how it went? Look across all sessions for:
- Patterns that repeat (scope creep, premature success claims, ignored concerns, wasted actions)
- Moments where the interaction went sideways — quote the user message and assistant response
- Patterns in timing (late night sessions, long gaps, high-churn periods)
- What went well that should be preserved

For each pattern found, identify: the pattern type, frequency across sessions, specific quoted moments, and the single highest-impact change (user behavior, CLAUDE.md rule, skill, or architectural fix). Rank by frequency and impact."""

FOLLOWUP_PROMPT = """For each issue you identified, go back to the conversation and find the exact moments — quote the user message and the assistant response that followed. Identify the pattern type (scope creep, ignored concern, wasteful action, missing diagnostic step, premature assertion, stale memory). For patterns that could recur in future sessions, suggest the single highest-impact change — whether that's a user behavior change, a CLAUDE.md rule, a skill, a hook, or an architectural change. Rank by impact."""


def run_ssh(remote, cmd, timeout=60):
    """Run a command on a remote host via SSH."""
    ssh_cmd = [
        "ssh", "-o", "IdentitiesOnly=yes",
        "-i", os.path.expanduser("~/.ssh/id_ed25519"),
        remote, cmd
    ]
    result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=timeout)
    return result.stdout, result.stderr, result.returncode


def list_sessions(project_path, remote=None):
    """List all session JSONL files in a project, sorted by size desc."""
    if remote:
        cmd = f'ls -lS $(eval echo "{project_path}")/*.jsonl 2>/dev/null'
        stdout, _, _ = run_ssh(remote, cmd)
        sessions = []
        for line in stdout.strip().split('\n'):
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 9:
                size = int(parts[4])
                path = parts[8]
                fname = os.path.basename(path)
                sessions.append({'path': path, 'fname': fname, 'size': size})
        return sessions
    else:
        project_path = Path(project_path)
        sessions = []
        for f in sorted(project_path.glob("*.jsonl"), key=lambda p: p.stat().st_size, reverse=True):
            sessions.append({
                'path': str(f),
                'fname': f.name,
                'size': f.stat().st_size,
            })
        return sessions


def copy_session(session_path, dest_path, remote=None):
    """Copy a session file locally (or from remote via scp)."""
    if remote:
        scp_cmd = [
            "scp", "-o", "IdentitiesOnly=yes",
            "-i", os.path.expanduser("~/.ssh/id_ed25519"),
            f"{remote}:{session_path}", dest_path
        ]
        subprocess.run(scp_cmd, capture_output=True, timeout=120)
    else:
        subprocess.run(["cp", session_path, dest_path])


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
    parser = argparse.ArgumentParser(description='Session Distiller Pipeline')
    parser.add_argument('query', nargs='*', help='Project name to fuzzy-match (e.g., "voicemode ios", "dell")')
    parser.add_argument('--project', default=None, help='Explicit path to .claude/projects/<project-id>/')
    parser.add_argument('--remote', default=None, help='SSH remote (user@host) for remote projects')
    parser.add_argument('--output', default=None, help='Output directory (default: ~/distiller-runs/<project-name>)')
    parser.add_argument('--top', type=int, default=None, help='Only process N largest sessions')
    parser.add_argument('--min-size', type=int, default=50000, help='Skip sessions smaller than N bytes (default: 50KB)')
    parser.add_argument('--name', default=None, help='Human-friendly project name')
    parser.add_argument('--list', action='store_true', help='List all registered projects')
    args = parser.parse_args()

    # Handle --list
    if args.list:
        list_projects()
        sys.exit(0)

    # Resolve project from query or explicit flags
    if args.query and not args.project:
        # Try group match first
        group = resolve_group(args.query)
        if group:
            group_name, members = group
            args.name = group_name
            args.remote = members[0][1]  # all share same remote
            args._multi_paths = [m[2] for m in members]
            print(f'Resolved group: {group_name} ({len(members)} projects, {args.remote or "local"})')
            for name, _, path in members:
                print(f'  - {name}: {path}')
        else:
            result = resolve_project(args.query)
            if result is None:
                print(f'No project matched: "{" ".join(args.query)}"')
                print('Use --list to see registered projects, or --project for explicit path.')
                sys.exit(1)
            resolved_name, resolved_remote, resolved_path, skip_reason = result
            if skip_reason:
                print(f'Project "{resolved_name}" is marked as skip: {skip_reason}')
                print('Use --project with explicit path to override.')
                sys.exit(1)
            args.project = resolved_path
            if resolved_remote and not args.remote:
                args.remote = resolved_remote
            if not args.name:
                args.name = resolved_name
            print(f'Resolved: {resolved_name} ({args.remote or "local"}) -> {args.project}')
    elif not args.project:
        parser.print_help()
        sys.exit(1)

    # Derive project name
    project_name = args.name or os.path.basename(args.project.rstrip('/'))
    project_name_short = project_name.replace('-home-cody-', '').replace('-Users-codyserban-', '')

    # Output directory
    if args.output:
        output_dir = Path(args.output)
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
            sessions.extend(list_sessions(p, args.remote))
        sessions.sort(key=lambda s: s['size'], reverse=True)
    else:
        sessions = list_sessions(args.project, args.remote)
    sessions = [s for s in sessions if s['size'] >= args.min_size]

    if args.top:
        sessions = sessions[:args.top]

    total_raw = sum(s['size'] for s in sessions)
    print(f'  Found {len(sessions)} sessions ({total_raw / 1048576:.1f}MB total)')
    print()

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

        copy_session(s['path'], raw_path, args.remote)
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
    print(f'\n  Stripped: {total_raw/1048576:.1f}MB -> {total_stripped/1048576:.1f}MB ({(1-total_stripped/total_raw)*100:.0f}% reduction)')
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
        'remote': args.remote,
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
