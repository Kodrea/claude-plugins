# session-distiller (Claude Code plugin)

Installable packaging of the `session-distiller` tool: strips noise from Claude
Code session JSONLs, batches them into context-sized chunks, and emits
ready-to-run analysis prompts. Output lands in `~/distiller-runs/` so it
survives plugin updates / uninstalls.

Slash command: **`/distill`**

## What this plugin does

- Adds a `/distill` slash command that runs the distiller pipeline on any
  registered project (fuzzy-matched by name/alias)
- Filters registered projects by the *local* machine so `/distill --list` only
  shows projects that actually live on the machine you're running on
- Loads bundled defaults, but prefers user overrides at
  `~/.claude/session-distiller/{config,projects}.json`
- Leaves the existing `~/Projects/utilities/claude-plugins/session-distiller/`
  tool untouched for backward compatibility

## Prerequisites

- `python3` on PATH (stdlib only — no pip installs needed)
- A configured GitHub SSH key, since the upstream `install.sh` clones via
  `git@github.com:Kodrea/claude-plugins.git`. On a fresh machine without an
  SSH key, configure one (or clone the marketplace manually via HTTPS) before
  step 1.
- Claude Code CLI (`claude plugin ...` is used to install)

## Install (per machine)

1. Install the `local` marketplace (if not already done on this machine):

   ```bash
   bash <(curl -sL https://raw.githubusercontent.com/Kodrea/claude-plugins/main/install.sh)
   ```

2. From your shell:

   ```bash
   claude plugin install session-distiller@local
   ```

   (or `/plugin install session-distiller@local` from inside a Claude Code session)

3. First run detects the machine name (metadata only — see below) and writes
   `~/.claude/session-distiller/config.json`:

   ```
   /distill --config
   ```

4. (Optional) edit `~/.claude/session-distiller/config.json` if you want the
   `machine` label stamped on manifests to differ from `socket.gethostname()`.
   **This value does not affect which projects are considered local** — that
   is decided by path existence, not hostname matching:

   ```json
   {
     "local_machine": "pop-os"
   }
   ```

5. (Optional) drop a custom registry at
   `~/.claude/session-distiller/projects.json` to override the bundled one.

## Usage

```
/distill --list                # local projects only
/distill --list-all            # every registered project
/distill --config              # show resolved machine/registry
/distill dell                  # fuzzy-match a project
/distill voicemode ios --top 5 # limit to N largest sessions
/distill --project ~/.claude/projects/-home-cody-Projects-web-web-dev-USTC
```

## Files

```
plugins/session-distiller/
├── .claude-plugin/plugin.json    # plugin manifest
├── commands/distill.md           # /distill slash command
├── scripts/pipeline.py           # pipeline (stdlib only)
├── scripts/strip.py              # per-session strip logic
├── scripts/projects.json         # bundled default registry
└── README.md                     # this file
```

## Relation to the existing tool

- The plugin ships its *own* copy of `pipeline.py` and `strip.py` under
  `scripts/`. This keeps the install self-contained and avoids depending on a
  path that may not exist on another machine.
- The existing
  `~/Projects/utilities/claude-plugins/session-distiller/{pipeline,strip}.py`
  files are **not** modified by this plugin. The old invocation
  `python3 ~/Projects/utilities/claude-plugins/session-distiller/pipeline.py …`
  continues to work unchanged.
- When the plugin version drifts forward, the old directory can be deprecated at
  the user's discretion.

## Cross-machine behaviour

By design each machine only distills its own sessions. The plugin pipeline has
no SSH/remote-invocation code path at all — to distill sessions on another
machine, install this plugin on that machine and run `/distill` there.

"Local" is determined by **path existence**, not machine labels. For each
entry in `projects.json`, the plugin expands `~` and checks whether the
`~/.claude/projects/<id>/` directory exists on this host. If it does, the
project is local and shows up in `/distill --list`. This means:

- No per-machine config editing is needed on Mac vs Linux vs c4130 — the
  hostname doesn't have to match anything.
- The `machine` field in `projects.json` stays as metadata (used in error
  messages and in the manifest stamp) but is ignored by filter logic.
- If a registry entry's path doesn't exist on this host, `/distill` will
  point the user at the `machine` label for context ("run on machine X").

The legacy `~/Projects/utilities/claude-plugins/session-distiller/pipeline.py`
still ships with SSH support for backward compatibility, but this plugin's copy
does not.

## Future work (out of scope for v1)

- Cross-project synthesis / review-team agents (synthesizer, verifier,
  pattern-hunter from the original docs). These could be added as
  `agents/` under the plugin in a v2.
- A bundled `analyze` command that orchestrates the headless `claude -p`
  analysis step end-to-end. v1 stops at `prompts.md`.

## Uninstalling

```
/plugin uninstall session-distiller@local
```

This removes `~/.claude/plugins/cache/local/session-distiller/`. Neither
`~/.claude/session-distiller/` (user config) nor `~/distiller-runs/` (outputs)
are touched.
