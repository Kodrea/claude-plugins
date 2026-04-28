# Subagent Anti-Patterns

Ten patterns to avoid when designing subagents and agent teams.
This file is the full-citation reference for the SKILL.md inline summary.

---

### 1. effort-drift

When `effort` is not explicitly set in the subagent frontmatter, the subagent inherits
the session's effort level — whatever the parent conversation happens to be running at.
A scout intended to run cheaply at `low` will silently run at `max` if the parent session
uses `max`, burning deliberation tokens on pattern matching that adds no value.

**Source**: `research/schemas/subagent-frontmatter.xml` — `effort` field excerpt: "Default: inherits from session."
**Instead**: Always set `effort` explicitly for any role where cost/quality matching is intentional.

---

### 2. max-for-scout

Using `effort: max` on extraction or routing roles. These roles do not benefit from
extended deliberation — the additional thinking time adds cost without improving output
quality for pattern-match or file-listing tasks. `max` is reserved for frontier-problem
deliberation where evals confirm headroom over `xhigh`.

**Source**: `research/annotated/costs.md` — extended-thinking-settings paragraph; `research/sources/official-effort.md`
**Instead**: Use `effort: low` for scouts and messengers. Reserve `max` for critic/architect
roles only after evals confirm the quality gain justifies the cost.

---

### 3. write-tools-on-reviewer

Giving a critic or reviewer role Write or Edit tools. Reviewers identify gaps and
surface objections — they do not fix them. Adding write tools blurs the separation of
concerns and creates blast radius where a review agent might silently modify files it
was only meant to evaluate. This is the most common tool-overgrant on adversarial roles.

**Source**: `plans/subagent-builder-skill-plan.md` §5 — critic archetype: `typical_tools: [Read, Grep, Glob]`
**Instead**: Critic and adversarial-critic roles get `[Read, Grep, Glob]` only. If fixes
are needed, have a separate writer role act on the critic's output.

---

### 4. model-effort-mismatch

Combining an effort level with a model that does not support it. Key gates, verified
2026-04-28 against `research/sources/official-effort.md`:

| Effort | Supported models |
|-|-|
| `xhigh` | Opus 4.7 only |
| `max` | Mythos Preview, Opus 4.7, Opus 4.6, Sonnet 4.6 |
| `high`, `medium`, `low` | All models except Haiku 4.5 |
| any effort field | Haiku 4.5: NOT supported — will error at runtime |

Setting `effort: xhigh` on Sonnet 4.6, or setting any `effort` on Haiku 4.5, causes
a runtime error. This gating may shift across model releases — always cite the source doc
rather than training-data memory.

**Source**: `research/schemas/subagent-frontmatter.xml` — `effort` field caveats; `research/sources/official-effort.md`
**Instead**: Verify model support before setting effort. The `<effort_ladder>` in the skill's
`<decision_framework>` lists model gates per rung.

---

### 5. premature-team

Using an agent team when a single subagent with sequential Task calls is sufficient.
Teams add SendMessage and TaskCreate overhead on every inter-agent communication. If
roles don't need to communicate mid-task and work is strictly sequential, a chain of
Task calls is simpler, cheaper, and easier to debug.

**Source**: `research/schemas/send-message-tool.xml`; `plans/subagent-builder-skill-plan.md` §4 team-vs-single decision tree
**Instead**: Default to single subagent. Use a team only when roles need real-time
communication (SendMessage) or tasks must persist across multiple Task calls (TaskCreate/Get).

---

### 6. plugin-subagent-hook-gap

Subagents distributed via plugins silently drop `hooks`, `mcpServers`, and `permissionMode`
when used as teammates in a team context. These fields work correctly in standalone
subagents invoked via Task, but are not honored in the plugin-distributed teammate case.
This is one of the harder-to-notice gaps because the agent runs without error — it just
ignores the configuration.

**Source**: `research/sources/official-sub-agents.md` §plugin subagents (plugin-subagent-limits caveat)
**Instead**: For plugin-distributed agents intended for team use, do not rely on `hooks`,
`mcpServers`, or `permissionMode` in the agent frontmatter. Configure these at the session
level or in a project CLAUDE.md.

---

### 7. tools-overgrant

Giving every agent Bash, Write, and Edit "just in case." Overly broad tool grants widen
the blast radius of mistakes and violate the principle of minimum capability. A scout
that only needs to read files should not have Bash — if it hallucinates a shell command,
the command will run. This is the tool-surface equivalent of running everything as root.

**Source**: `plans/subagent-builder-skill-plan.md` §4 `<tool_gating>` principle: "minimum tools for the role"
**Instead**: Start from the minimum tool set for the role archetype and add tools only
with a stated reason. The `<tool_gating>` section in the decision framework provides
tiered lists by role type.

---

### 8. missing-permission-mode

Relying on the session's default permission mode instead of setting it explicitly in
the agent frontmatter. A reviewer role that inherits `bypassPermissions` from an
automated pipeline session will not prompt before making destructive tool calls —
even if the reviewer was designed to be read-only.

**Source**: `research/schemas/subagent-frontmatter.xml` — `permissionMode` field; caveats on parent-override behavior
**Instead**: Set `permissionMode` explicitly for every role with a stated rationale.
Planners get `plan`. Scouts get `default`. `acceptEdits` is opt-in only — never implicit.
`bypassPermissions` requires explicit user authorization per session.

---

### 9. no-justification

Shipping an agent file with no comment explaining why effort, model, and tools were
chosen. Without rationale, a future reviewer cannot tell whether choices were deliberate
or copied arbitrarily. An xhigh/Opus critic looks the same as an accidentally-inherited-max
extractor from the outside if neither has a rationale block.

**Source**: `plans/subagent-builder-skill-plan.md` §7 pass criteria: "All 6 required decisions justified"
**Instead**: The SKILL.md `<required_outputs>` checklist requires one-sentence justifications
for model, effort, tools, permissionMode, isolation, and archetype. Write them in the
agent body or a `<!-- Rationale -->` comment block.

---

### 10. copy-paste-archetype

Taking archetype YAML from `reference/role-archetypes.xml` verbatim without tuning
it to the specific project. Archetypes encode typical values for typical cases. Most
projects have constraints — cost targets, tool restrictions, permission boundaries,
model version pinning — that require deviating from the typical configuration.
Verbatim archetype YAML becomes stale the moment the project context diverges.

**Source**: `plans/subagent-builder-skill-plan.md` §5: "Archetypes are starting points."
**Instead**: Use the archetype as a first draft. Check `when_NOT_to_use` and
`example_prompt_shape` in the archetype block to confirm fit. Adjust model, effort,
and tools as needed, and record each deviation with a one-line rationale.
