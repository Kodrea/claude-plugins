---
name: insight-capture
description: This skill should be used when the user says "capture this", "that's a gotcha", "we should remember this", "future me needs to know this", or "don't repeat this mistake". Also use when Claude's reasoning reveals sudden synthesis, reframing, non-obvious implications, discovers a prior assumption was wrong, or catches a sloppy AI habit worth preventing.
version: 1.0.0
---

# Insight Capture

**Trigger:** A response reveals sudden synthesis, reframing, or non-obvious implications. Your own reasoning derives a structural insight, reveals a prior assumption was wrong, or catches a sloppy habit worth preventing.

**Goal:** Capture the insight before it's lost to the session ether.

---

## When This Fires

You (the AI) should suggest invoking this when:
- A response reveals a sudden synthesis or reframing
- Reasoning derives a non-obvious structural insight
- A prior assumption turns out to be wrong
- A non-obvious implication emerges from the work
- A pattern clicks that wasn't explicit before
- You catch yourself about to make a common AI mistake
- You notice a sloppy habit that could become a rule to prevent it

---

## Capture Flow

### Step 1: Acknowledge
Pause. Say: "That's interesting - should I capture this insight?"

### Step 2: Quick Classification
- **Synthesis** - Connected dots that weren't obvious
- **Reframe** - Shifted how to think about the problem
- **Correction** - Prior assumption was wrong
- **Pattern** - Could become a rule
- **System insight** - Reveals how things actually work
- **Sloppy habit** - AI tendency that causes problems (prime rule candidate!)

### Step 3: Capture Location

| Size | Where | Format |
|------|-------|--------|
| One-liner | SCRATCHPAD.mdc Insights section | `- [DATE] Description` |
| Paragraph | SCRATCHPAD + brief reference | `- [DATE] Brief. Details below.` |
| Full write-up | notes/DISCOVERY-*.md | Then reference in SCRATCHPAD |

### Step 4: Rule Potential Check
Ask: "Could this become a rule?"
- If yes: Add to SCRATCHPAD Proposed Rules section
- If no: Just the insight capture is enough

---

## Example Captures

### Quick Insight (SCRATCHPAD only)
```markdown
- [2025-01-15] Firebase timestamps need serverTimestamp() not new Date() for consistency
```

### With Details (SCRATCHPAD + note)
```markdown
- [2025-01-15] Event listeners on dynamic elements need delegation pattern. See notes/DISCOVERY-event-delegation.md
```

### Rule Proposal (SCRATCHPAD)
```markdown
- [2025-01-15] Delegation pattern for dynamic elements -> notes/PROPOSED-event-delegation-rule.md
```

---

## Backup Trigger

If the AI doesn't catch it, user can say:
- "Capture this"
- "That's a gotcha"
- "We should remember this"
- "Future me needs to know this"
- "Don't repeat this mistake"
