---
description: Distill Claude Code sessions for pattern analysis. Strips noise, batches into context-sized chunks, and emits ready-to-run analysis prompts.
argument-hint: "<project query> | --list | --list-all | --config | --top N | --recent HOURS | --project PATH"
allowed-tools: [Bash, Read]
---

# /distill — Session Distiller

Run the session distiller pipeline against Claude Code session JSONLs for a
project on **this machine**, producing stripped batches under
`~/distiller-runs/`.

## Arguments

$ARGUMENTS

Parse the arguments:

- `--list`          — show projects registered for *this* machine (default filter)
- `--list-all`      — show every project in the registry (all machines)
- `--config`        — print resolved runtime config (local machine, registry paths) and exit
- `--project PATH`  — use an explicit path to `~/.claude/projects/<id>/`
- `--top N`         — process only the N largest sessions
- `--min-size N`    — skip sessions smaller than N bytes (default 50KB)
- `--recent HOURS`  — keep only sessions with activity within the last HOURS hours (float OK, e.g. 0.5 = 30min)
- `--name NAME`     — override the human-friendly project name
- otherwise         — fuzzy-match a project name/alias from the registry

Filters apply in order: `--min-size` → `--recent` → `--top`.

This plugin is **local-only**: there is no SSH / remote path. To distill
sessions on a different machine, install this plugin on that machine and run
`/distill` there.

## Pre-flight

Before running the pipeline, verify `python3` is on PATH. If it isn't, report a
clear error and stop — the pipeline is stdlib Python 3 and cannot run without it.

```bash
command -v python3 >/dev/null 2>&1 || { echo "distill: python3 not found on PATH. Install python3 and retry."; exit 127; }
```

## Behaviour

The pipeline lives at `${CLAUDE_PLUGIN_ROOT}/scripts/pipeline.py`. It:

1. On first run, auto-creates `~/.claude/session-distiller/config.json` with
   `{"local_machine": "<hostname>"}`. This value is **metadata only** — it gets
   stamped into manifest.json so runs are traceable, but it is NOT used to
   decide which projects are local.
2. Reads the project registry from `~/.claude/session-distiller/projects.json`
   if it exists, otherwise from the bundled
   `${CLAUDE_PLUGIN_ROOT}/scripts/projects.json`.
3. Filters resolved projects by **path existence**: for each registry entry,
   if `~/.claude/projects/<id>/` exists on this host, it's local. No hostname
   matching required, so the plugin works on any machine without tweaking the
   config. Non-local matches produce a clear error telling the user where to
   run the command.
4. Writes output to `~/distiller-runs/<name>_<timestamp>/` — outside the plugin
   install dir, so updates/uninstalls never touch existing runs.

## Execute

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/pipeline.py" $ARGUMENTS
```

Relay the stdout to the user. If the pipeline exits non-zero, relay the error
verbatim so they can see the exact diagnostic.

When the pipeline produces batches (look for `Done. Output in ...` in stdout):

- Report the output directory, session count, compression ratio, and batch count
- Point the user at `<output-dir>/prompts.md` for pre-formatted analysis prompts
- Offer to kick off the headless analysis step (per
  `~/distiller-runs/CLAUDE.md`) but do NOT run it automatically — always
  confirm with the user first.

## Notes

- The legacy invocation
  `python3 ~/Projects/utilities/claude-plugins/session-distiller/pipeline.py ...`
  still works from its original location (the plugin does not touch those
  files). The plugin is a parallel, installable copy with per-machine config
  and a local-only execution model.
- The analysis step (`claude -p --dangerously-skip-permissions ...`) is
  deliberately NOT run automatically by this command. See
  `~/distiller-runs/CLAUDE.md` for the analysis workflow.
