# Review Notes for Auditor

## TODO Markers

- [ ] **WebSocket upgrade() method** — No `upgrade()` documentation found in extracted sources. WebSocket handler interface was captured but the HTTP-to-WebSocket upgrade flow is undocumented. (DRAFT.md: Gaps and Open Questions)
- [ ] **Watch mode / test discovery interaction** — No documentation on how `--watch` interacts with file changes and test file discovery. (DRAFT.md: Gaps and Open Questions)
- [ ] **AI agent detection flags** — `CLAUDECODE`, `REPLIT`, `AGENT` environment flags mentioned in bun-apis.md but detection mechanism not explained. (DRAFT.md: Gaps and Open Questions)
- [ ] **SQLite serialize/deserialize** — `serialize()` and `deserialize()` methods exist on the `Database` class but no usage context or examples were extracted. (DRAFT.md: Gaps and Open Questions)
- [ ] **`.prepare()` vs `.query()` caching** — Both methods exist for creating statements; no documentation on whether caching behavior differs. (DRAFT.md: Gaps and Open Questions)
- [ ] **FFI FinalizationRegistry** — Memory management documentation references this but no JS-side examples were found in sources. (DRAFT.md: Gaps and Open Questions)
- [ ] **FFI struct alignment** — No documentation on pointer alignment requirements for custom struct types in FFI. (DRAFT.md: Gaps and Open Questions)
- [ ] **HTTP export default syntax** — `export default` server syntax exists but is not demonstrated or compared to `Bun.serve()` in extracted sources. (DRAFT.md: Gaps and Open Questions)
- [ ] **Bun.file + Bun.write streaming** — No examples of combining `Bun.file` with `Bun.write` or with readable streams. (DRAFT.md: Gaps and Open Questions)
- [ ] **DOM testing examples** — HappyDOM, DOM Testing Library, and React Testing Library compatibility is listed as a feature but no usage examples exist in extracted sources. (DRAFT.md: Gaps and Open Questions)
- [ ] **Missing Jest API list** — Scout notes that not all Jest APIs are implemented; the specific list of unimplemented features was not present in extracted sources. (DRAFT.md: Additional Notes)
- [ ] **`--concurrent` default max-concurrency** — Source states "Default: 20" in a CLI flag code comment. Verify this is the confirmed runtime default and not a documentation placeholder. (DRAFT.md: Test Runner / Concurrent Execution)

## Unresolved Contradictions

No contradictions between sources were identified. All five source documents are in agreement on overlapping topics (e.g., bun-apis.md is a table of references, not a contradictory source).

## Low-Confidence Items

- [ ] **HTTP performance benchmark (Node 16 comparison)** — The benchmark in http-server.md compares against Node 16, which is end-of-life. The figure may not reflect current Node.js performance. Flagged with `<!-- TEMPORAL: verify currency -->` in DRAFT.md (HTTP Server / Performance section).
- [ ] **FFI performance (2–6x vs Node-API)** — No benchmark date or methodology details were provided in the source. The range (2x–6x) is wide; conditions under which each bound applies are unspecified.
- [ ] **JSCallback thread-safe callbacks** — Marked "experimental" in source. Production suitability is unknown.
- [ ] **Scout metadata finding count discrepancy** — The scout JSON reports `total_findings: 71` via per-source counts (18+16+14+15+8=71), but the `category_breakdown` field in the same metadata sums to only 46. The per-source counts are used in the draft as the authoritative total. The category_breakdown appears to be an undercounting artifact in the scout output itself and does not affect the synthesized findings.
