---
description: Audit an existing Claude Code agent definition against the subagent-builder framework. Usage: /review-agent [path/to/agent.md]
allowed-tools: [Read, Glob, Grep]
---

Audit the specified agent definition against the subagent-builder decision framework.

## Steps

**1. Find the file**

If a path was given as an argument, use it. Otherwise:
- Check `.claude/agents/` (project scope) and `~/.claude/agents/` (user scope) for `.md` files
- If multiple are found, ask the user which one to review
- If none are found, ask the user for the path

**2. Read the agent file completely**

**3. Apply the six required decisions as a checklist**

For each, mark: ✓ correct | ⚠ present but questionable | ✗ missing or wrong

| # | Decision | What to check |
|-|-|-|
| 1 | archetype | Named from the catalog or explicitly "bespoke"? Does it match the role's behavior? |
| 2 | model | Full model ID stated? Rationale given? Does the model support the effort level? |
| 3 | effort | Set explicitly (not inherited from session)? Matches role requirements per effort ladder? |
| 4 | tools | Listed? Minimum-capability? No unjustified Bash, Write, or Edit on read-only roles? |
| 5 | permissionMode | Explicit choice? Appropriate for what the agent does? |
| 6 | isolation | Single-subagent or team-teammate? Rationale given? Is the choice justified? |

**4. Run the anti-pattern quick check**

First, find the installed reference:
```
Glob: ~/.claude/plugins/cache/local/subagent-builder/*/skills/subagent-builder/reference/anti-patterns.md
```

Check each of the 10 anti-patterns. Flag every match with its number and a one-line explanation of what triggered it.

**5. Report findings**

Format:

```
## Decision Checklist
1. archetype — ✓/⚠/✗  [explanation if ⚠ or ✗]
2. model — ...
3. effort — ...
4. tools — ...
5. permissionMode — ...
6. isolation — ...

## Anti-Pattern Flags
[list any matches, or "None"]

## Overall Assessment
[one paragraph]
```

Do NOT rewrite the agent file unless the user explicitly asks after seeing the report.
