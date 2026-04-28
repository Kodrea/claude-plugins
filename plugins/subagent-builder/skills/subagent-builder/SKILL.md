---
name: subagent-builder
description: >
  Design well-shaped subagents and agent teams with thinking effort matched to role.
  Triggers on: "build me an agent", "I need a critic / scout / analyst / subagent",
  "design an agent team for X", "help me scope this role", "turn this workflow into
  agents", "create an agent definition", "what frontmatter fields does a subagent need",
  "configure a subagent for Y task". Routes role characteristics to effort first;
  model and tools follow from that choice.
allowed-tools: [Read, Write, Glob, Grep, AskUserQuestion, Task]
---

# Subagent Builder

This skill produces validated Claude Code subagent definition files — YAML frontmatter +
system prompt body — for any role from cheap extractors to deep adversarial reviewers.

**Primary design lever: thinking effort.** Choose effort for the role first; model and
tools follow. A scout that inherits session effort silently burns max-cost deliberation
on pattern matching. Effort-first prevents this.

<decision_framework>

<effort_ladder>
Choose the lowest rung that meets the role's requirements.

| Level | Use when | Model gate |
|-|-|-|
| `low` | Extraction, routing, file listing, classification | All models except Haiku 4.5 |
| `medium` | Synthesis, drafting, code review (<300 lines) | All models except Haiku 4.5 |
| `high` | Complex refactors, multi-step reasoning | All models except Haiku 4.5 |
| `xhigh` | Deep agentic work, architecture, long chains | Opus 4.7 only |
| `max` | Only when evals show measurable headroom over `xhigh` | Opus 4.7, Opus 4.6, Sonnet 4.6, Mythos Preview |

Haiku 4.5 does not support the `effort` field at all — any value will error at runtime.
Re-verify gates before recommending: read the `effort` field caveats in subagent-frontmatter.xml.
</effort_ladder>

<model_routing>
Default routing — deviate only with a stated reason:
- Haiku 4.5 → `low` effort extraction roles (cheapest model with tool support)
- Sonnet 4.6 → `medium`/`high` roles (cite costs.md anchor "sonnet-handles-most-coding-tasks-well-and")
- Opus 4.7 → `xhigh`/`max` roles (cite costs.md anchor for complex reasoning workloads)

For agent teams: prefer Sonnet for most teammates; cite costs.md "to-keep-agent-team-costs-manageable".
</model_routing>

<tool_gating>
Principle: minimum tools for the role.

- Readers: `[Read, Grep, Glob]`
- Writers: readers + `[Write, Edit]`
- Networked: writers + `[WebFetch]`
- Spawners (lead roles): writers + `[Task, SendMessage]`
- Messengers: `[SendMessage]` only

Never add Bash without a stated reason. Never add Write or Edit to critic or reviewer roles.
</tool_gating>

<isolation_choice>
Default: single subagent via `Task(subagent_type=...)` until a concrete reason to use a team.

Use a team when ANY of the following apply:

1. **Direct mid-task communication** — agents must share state or challenge each other
   in real-time, not through the parent session (SendMessage).
2. **Persistent workflow state** — work spans multiple Task calls; needs a task record
   that survives between calls (TaskCreate / TaskGet).
3. **Shared work queue** — multiple parallel agents pull from a common queue (TaskList).
4. **Parallel execution with lead aggregation** — agents work simultaneously and a
   coordinator synthesizes results. Offloads stateful aggregation from the main session
   to a lead agent; not achievable with parallel Task calls from the parent alone.
5. **Task dependency graph** — workflow has a non-linear shape (A→B, A→C, B+C→D);
   use TaskUpdate `addBlocks`/`addBlockedBy` to declare dependencies declaratively
   rather than forcing the parent to sequence everything manually.

If none apply: three sequential Task calls beat a three-agent team — lower overhead,
easier debugging, no SendMessage round-trips. Premature teams are anti-pattern #5.
</isolation_choice>

</decision_framework>

<required_outputs>
For every agent definition, justify these six decisions in the body or a comment block:

1. **archetype** — which entry in `reference/role-archetypes.xml` this matches, or "bespoke"
2. **model** — full model ID + one-sentence rationale citing a `costs.md` anchor
3. **effort** — level + one-sentence rationale; cite the `effort` field excerpt in subagent-frontmatter.xml
4. **tools** — list + minimum-capability rationale (why not more, why not less)
5. **permissionMode** — explicit choice + why (never rely on session inheritance)
6. **isolation** — single-subagent or team-teammate + one-sentence rationale
</required_outputs>

## Agent File Destination

Ask the user unless context makes it obvious:

- **User scope** (`~/.claude/agents/<name>.md`) — available in all projects; personal agents
- **Project scope** (`.claude/agents/<name>.md`) — committed to repo; team or project-specific
- **Plugin-bound** — part of an existing plugin; not available until plugin is installed

Do not default silently. "A personal agent I can use anywhere" → user scope.
"For our team repo" → project scope.

## Reference

Open once per session; grep per decision. Never state field behavior from training data — always
retrieve and cite the verbatim `excerpt`.

Use Glob to find the plugin's installed reference directory:
```
Glob: ~/.claude/plugins/cache/local/subagent-builder/*/skills/subagent-builder/reference/schemas/subagent-frontmatter.xml
```
Then substitute the resolved prefix for all paths below.

- `reference/schemas/subagent-frontmatter.xml` — all frontmatter field specs: types, defaults, caveats, excerpts
- `reference/schemas/agent-teams-frontmatter.xml` — teammate-specific fields
- `reference/schemas/send-message-tool.xml` — SendMessage parameters and delivery semantics
- `reference/schemas/task-tools.xml` — TaskCreate/Update/List/Get/Stop; note: TaskStop uses
  `task_id` (snake_case) vs TaskGet/TaskUpdate `taskId` (camelCase) — confirmed schema inconsistency
- `reference/schemas/tools-catalog.xml` — full 35-tool catalog with behavior blocks
- `reference/annotated/costs.md` + `costs.tags.json` — cost and model guidance; grep sidecar for anchors
- `reference/annotated/adaptive-thinking.md` + sidecar — when and how thinking applies to roles
- `reference/role-archetypes.xml` — starter 8 archetypes; pick closest match before going bespoke
- `reference/anti-patterns.md` — full citations for the anti-patterns summary below

## Decision Examples

<example name="scout-todo-finder">
Ask: "Build a subagent that finds every TODO comment in a Python project grouped by file."

1. archetype: scout
2. model: claude-haiku-4-5-20251001 — extraction, no deliberation; minimum-cost tool-capable model
3. effort: low — pattern grep, zero synthesis
4. tools: [Read, Grep, Glob] — read-only; no write surface needed or appropriate
5. permissionMode: default — read-only role
6. isolation: single-subagent — one-shot extraction; no inter-agent communication

Full file: `examples/01-scout-haiku-low.md`
</example>

<example name="gap-analyst">
Ask: "Synthesize these scout outputs into a structured gap report."

1. archetype: analyst
2. model: claude-sonnet-4-6 — cross-source synthesis; cite costs.md "sonnet-handles-most-coding-tasks-well-and"
3. effort: medium — judgment required; not trivial extraction, not adversarial deliberation
4. tools: [Read, Grep, Glob, Write] — must read sources and write the output report
5. permissionMode: default — writes only to a designated output path
6. isolation: single-subagent — sequential synthesis; no inter-agent communication needed

Full file: `examples/02-analyst-sonnet-medium.md`
</example>

<example name="pr-critic">
Ask: "I need an adversarial code reviewer for my PRs."

1. archetype: critic
2. model: claude-opus-4-7 — adversarial review needs full-context deliberation
3. effort: xhigh — recommended Opus 4.7 starting point for deliberation (official-effort.md, 2026-04-28);
   xhigh is Opus 4.7 only — use high on Sonnet 4.6 or Opus 4.6 if cost requires
4. tools: [Read, Grep, Glob] — critic MUST NOT have Write or Edit (anti-pattern #3)
5. permissionMode: default — read-only role
6. isolation: single-subagent — one-shot review; no team communication needed

Full file: `examples/03-critic-opus-high.md`
</example>

## Anti-Pattern Quick Check

Before handing off an agent file, verify none of these apply. Full context: `reference/anti-patterns.md`.

1. **effort-drift** — `effort` not set; subagent inherits session level silently
2. **max-for-scout** — `effort: max` on an extraction or routing role
3. **write-tools-on-reviewer** — critic or reviewer role has Write or Edit
4. **model-effort-mismatch** — `xhigh` on non-Opus-4.7; any `effort` on Haiku 4.5
5. **premature-team** — team where sequential Task calls would suffice
6. **plugin-subagent-hook-gap** — `hooks`/`mcpServers`/`permissionMode` in a plugin-distributed teammate
7. **tools-overgrant** — Bash or Write granted without a stated reason
8. **missing-permission-mode** — no explicit `permissionMode`; relying on session inheritance
9. **no-justification** — agent file has no rationale for effort/model/tools choices
10. **copy-paste-archetype** — archetype YAML copied verbatim without project-specific tuning

## Navigating the Reference Layer

First, find the installed plugin path:

```
Glob: ~/.claude/plugins/cache/local/subagent-builder/*/skills/subagent-builder/reference/schemas/subagent-frontmatter.xml
→  note the resolved path prefix
```

Then read schemas once per session and grep per field:

```
Read:  <prefix>/reference/schemas/subagent-frontmatter.xml
Grep:  name="<field>"  →  locates block in ≤2 operations
```

For cost and effort guidance, use the sidecar to find anchors first:

```
Grep:  "thinking" + "decision"  in  <prefix>/reference/annotated/costs.tags.json
→  retrieve anchor name
→  Read that paragraph in <prefix>/reference/annotated/costs.md
→  cite anchor in every model or effort rationale
```

Use the verbatim `excerpt` value from the schema block. If a field's behavior conflicts with
training-data memory, the file is authoritative — not memory.
