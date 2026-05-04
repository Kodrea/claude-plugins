# Session Distiller — Requirements Draft

## Purpose

Turn raw Claude Code session JSONL files (~700MB across ~2,300 sessions) into compressed, readable narratives that reveal how Cody uses Claude Code — where time goes, where sessions go sideways, and where context switching burns focus.

Serves two consumers:
1. **Cody directly** — read a 3-5KB summary of a 2MB session and understand what happened
2. **Project dashboard** (future) — structured output feeds into a cross-project overview tool

## Data Sources

| Source | Location | Contains |
|-|-|-|
| Session JONLs | `~/.claude/projects/<project-id>/*.jsonl` | Full conversation: messages, tool calls, results, errors, timestamps, token usage |
| Sessions index | `~/.claude/projects/<project-id>/sessions-index.json` | Session ID, first prompt, file mtime per project |
| Global history | `~/.claude/history.jsonl` | Every user prompt across all projects with timestamps (6,220 entries) |
| Session metadata | `~/.claude/sessions/*.json` | PID, cwd, start time, session name, entrypoint |

## Processing Layers

### Layer 1 — Extract
Parse session JSONL. For each message, pull:
- Role (user / assistant / system)
- Timestamp
- Tool calls: name, file paths, command strings
- Errors (tool failures, API errors)
- Token usage from assistant messages
- Message content (user messages kept, assistant text kept, tool result bodies discarded)

Pasted content and context dumps detected and collapsed to labels: `[pasted: ~200 lines]`

Output: structured intermediate JSON, one per session. ~95% size reduction.

### Layer 2 — Collapse
Group consecutive same-role tool actions into summaries:
- "reads boot-monitor.sh, config.sh" instead of 2 separate read entries
- "5 bash commands (3 failed)" instead of 5 entries
- "edits boot-monitor.sh (3 times)" to flag churn

Preserve user messages verbatim (truncated at ~300 chars with full text available).
Preserve assistant *text* responses (the conversational parts, not tool calls).

Output: collapsed timeline JSON.

### Layer 3 — Annotate
Walk the collapsed timeline and flag patterns:

| Flag | Trigger | What it means |
|-|-|-|
| 🔄 Churn | Same file edited 3+ times in 10 turns | Iteration without progress, or evolving requirements |
| ↩️ Direction change | User contradicts or redirects Claude's approach | Possible miscommunication or Claude went wrong way |
| ❌ Error cluster | 3+ consecutive failed tool calls | Debugging spiral |
| ⏸️ Long gap | 10+ min between messages (configurable) | Cody left to think, research, or got distracted |
| 📖 Re-read | File read that was already read this session | Context was lost (compression?) or approach reset |
| 🔥 Token burn | Turn exceeds Nth percentile token usage | Expensive operation — worth reviewing |

### Layer 4 — Summarize (optional, AI-assisted)
Feed distilled timeline (~3-5KB) to Claude and ask for:
- Plain-english session narrative
- What went well / what went sideways
- Suggested "what I'd do differently" if patterns are clear

This layer is opt-in and costs tokens. Layers 1-3 are free and deterministic.

---

## Feature: Cross-Session Timeline

<!-- TODO: flesh out with Cody -->

Build an absolute timeline across all projects showing when sessions were active, when switching occurred, and total active time per project.

**Key problems to solve:**
- Defining "active" vs "idle" within a session (inactivity threshold)
- Overlapping sessions (multiple terminals / IDE instances)
- Distinguishing intentional multitasking from unintentional context thrashing

---

## Sections to discuss before writing

### Output Formats
- What does the CLI interface look like? (`distill <session-id>`? `distill --project dell-poweredge --last 5`?)
- Terminal rendering vs markdown file vs JSON for dashboard
- Do we want a "browse" mode or just generate-and-read?

### Storage & Indexing
- SQLite index of all sessions? Or flat JSON files per session?
- Incremental processing (only distill new/changed sessions)
- Where does output live? Next to the JONLs? Separate dir?

### Scope & Prioritization
- Retroactive processing of all 2,300 sessions vs forward-only?
- Which layers ship first?
- Standalone tool vs Claude Code plugin/skill?

### Privacy & Portability
- Session data contains full code, commands, file contents
- If distilled output is shared or stored separately, what gets redacted?
- Does this need to work on other machines or just this one?
