# Auditor Verification Checklist (Opus)

You are the final quality gate for a generated REFERENCE.md. Your job is to verify the draft against the source scout JSONs and fix any issues before producing the final output.

## Inputs

- `DRAFT`: the REFERENCE_DRAFT.md from the processor stage
- `SCOUT_JSONS`: all scout extraction JSONs (ground truth)
- `RAW_FILES`: the original raw markdown files (for spot-checking)

## Verification Checklist

### 1. Completeness
- [ ] Every scout JSON source file is represented in the draft
- [ ] Every command from scout JSONs appears in the draft
- [ ] Every warning from scout JSONs appears in the draft
- [ ] Every table from scout JSONs is included or merged
- [ ] Hex values and pinouts are not missing

### 2. Code Block Integrity
- [ ] All code blocks have correct language tags (```bash, ```python, etc.)
- [ ] No markdown artifacts inside code blocks (no stray `**`, `_`, `>` that aren't part of the code)
- [ ] Commands are copy-pasteable — no line-wrapping artifacts, no prompt symbols ($, #) unless they're part of the actual command
- [ ] Multi-line commands preserve their line breaks correctly

### 3. Accuracy
- [ ] Cross-references resolve to actual sections in the document
- [ ] Anchor links (`#section-name`) match actual heading anchors
- [ ] Conditional context is preserved (commands marked with their conditions)
- [ ] No contradictions between sections (e.g., "use X" in one section, "never use X" in another)
- [ ] Sequence ordering matches the logical workflow

### 4. Structure
- [ ] Quick Navigation links all work
- [ ] Heading hierarchy is consistent (no H4 under H2 without H3)
- [ ] Related content is properly grouped (not scattered across unrelated sections)
- [ ] Warnings appear next to the content they apply to

### 5. No Hallucination
- [ ] No commands that don't appear in any scout JSON
- [ ] No URLs that aren't from the source material
- [ ] No file paths that aren't mentioned in the sources
- [ ] All `<!-- TODO: verify -->` comments are reviewed

## Output

Produce the final REFERENCE.md with all issues fixed. If you made changes, add a brief comment at the end:

```markdown
<!-- Auditor changes:
- Fixed: [description]
- Fixed: [description]
-->
```

If the draft passes all checks with no changes needed, produce it as-is (no audit comment needed).

## Common Issues to Watch For

1. **Markdownify artifacts**: `\_` instead of `_` in code blocks, `\*` instead of `*`
2. **Missing conditions**: A command that only works on Ubuntu shown without that context
3. **Broken anchors**: Heading was renamed during synthesis but nav link wasn't updated
4. **Duplicate content**: Same command appearing twice under different headings
5. **Lost warnings**: CAUTION/WARNING blocks that got dropped during synthesis
6. **Wrong language tags**: `bash` on a Python block or vice versa
