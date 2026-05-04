# Distiller Rules

Confirmed interaction patterns from session analysis. These rules were verified
against source session data and reviewed for redundancy, mechanism strength, and
scope before inclusion.

Rules are loaded by the `/distill` command so they travel with the plugin across
machines. To propose a new rule, run a distiller analysis, verify the finding,
and add it here with the required fields.

## Format

Each rule includes:
- **Rule:** the actionable instruction
- **Source:** project, date, and session count that produced the finding
- **Why:** the specific failure mode observed
- **Enforcement:** where/how this rule is applied (CLAUDE.md, memory, hook)

---

## File Safety

**Rule:** Never delete files unless the user explicitly asks. If files should be removed, offer to delete and wait for confirmation.

**Source:** radxa-rock5b, 2026-04-10, 2 sessions

**Why:** Claude deleted an HTML checklist after converting it to markdown without being asked. The user never requested deletion and the HTML could have been useful as a visual reference.

**Enforcement:** CLAUDE.md rule (global)

---

## Hardware Verification

**Rule:** For hardware/driver projects, the deployed device is the source of truth. When verifying installation state, check the device first, documentation second. Docs describe intent; the device describes reality.

**Source:** radxa-rock5b, 2026-04-10, 2 sessions

**Why:** Claude trusted local setup.sh documentation to push back on the user's claim that DKMS was abandoned. After SSH into the Rock 5B+, DKMS wasn't even installed. The docs were stale.

**Enforcement:** CLAUDE.md rule (global), extends feedback_verify_before_asserting memory

---

## Progress Before Long Writes

**Rule:** Before writing a file over 200 lines, emit a short status message with the file path and approximate size.

**Source:** radxa-rock5b, 2026-04-10, 2 sessions

**Why:** Claude spent ~8 minutes generating a large HTML flowchart with zero output. The user asked "did you get stuck?" because there was no way to tell if it was working or hung.

**Enforcement:** CLAUDE.md rule (under Context Efficiency > Responses)

---

## Confirm Document Audience

**Rule:** When creating a document whose primary consumer is ambiguous (human vs. machine/agent), confirm format before writing. Skip the question when context makes it obvious.

**Source:** radxa-rock5b, 2026-04-10, 2 sessions

**Why:** Claude built a 481-line HTML checklist for "the other engineer" who turned out to be Claude Code. Had to redo the entire document as markdown. Asking the audience question upfront would have avoided the rework.

**Enforcement:** CLAUDE.md rule (under Context Efficiency > Responses)

---

## No Blind Retry After Errors

**Rule:** Never retry a tool call with identical parameters after it fails. Diagnose the error, adjust parameters, then retry. Before reading any file produced by a subagent or pipeline, check its size first (wc -l or stat). Never retry a Read with the same parameters after a token-limit error.

**Source:** radxa-rock5b, 2026-04-10, 5 sessions (observed in 4 of 5)

**Why:** Claude retried the same Read call up to 5 times on a 36,597-token file before checking the line count. In another session, retried identical Read on an 11,916-token agent output file and got the same error. The pattern burns tool calls and time on actions already known to fail. Particularly ironic: one session's own analysis had flagged "excessive sequential reads" as a pattern.

**Enforcement:** CLAUDE.md rule (under Context Efficiency > File Reading), feedback memory

---

## Completion Verification

**Rule:** Before declaring a task "done" or "ready," enumerate what was NOT verified. For hardware: was the device checked? For plugins/tools: was cross-machine portability considered? For cross-system changes: were all affected systems updated? If anything is unverified, say so explicitly instead of declaring completion.

**Source:** radxa-rock5b, 2026-04-10, 5 sessions (observed in 3 of 5)

**Why:** Claude declared "ready to test" after implementing CLAUDE.md rules without considering they were local-only and wouldn't travel to other machines. This opened an entire unplanned phase of work. In the same project, Claude gave install instructions referencing a marketplace that hadn't been created yet. Both cases: premature completion claims led to trust erosion and rework.

**Enforcement:** CLAUDE.md rule (global, after Hardware Verification), feedback memory
