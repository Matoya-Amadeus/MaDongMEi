# MaDongMei Agent Notes

- Use `bootstrap -> install_context_bridge -> install_selfcheck -> install_validation_matrix -> quality_gate -> madongmei_doctor` as the canonical public chain.
- Keep the public surface self-contained and free of private paths, secrets, personal data, private wiki bodies, private skill bodies, audit receipts, and device-local state.
- Prefer `memoryctl` as the only user-facing memory entrypoint; use `memoryctl autopilot` for public recall/classify/capture/promote and `memoryctl pre-hook` for Codex request-time public memory injection.
- If a change touches runtime behavior, add or update a test in `tests/` first and follow Red-Green TDD.
- Keep the repo installable on a clean machine with only Python 3 and a POSIX shell.
- Default writable targets are `MADONGMEI_HOME`, `MADONGMEI_WIKI_DIR`, `MADONGMEI_SKILL_DIR`, and `CODEX_HOME/.madongmei-runtime`; override them only for tests or isolated installs.
- `scripts/install_context_bridge.sh` must keep Codex model instructions injection working and must not hardcode machine-specific paths in tracked files.
- Public projection rules live in `config/public-projection.yaml`; migrate capabilities as copy/sanitize/template/omit, never by copying private content.
- Public storage audit lives in `knowledge/repo-storage-audit.md`, and public retention rules live in `knowledge/repo-retention-policy.md`.
- `scripts/local_ignored_artifact_report.py --json` must stay readonly and expose target-scoped `target_id`, `path`, `size_bytes`, `risk`, `rebuild_cost`, and `cleanable` fields.
- `scripts/madongmei_code_scorecard.py --json --no-record` is the readonly repository scorecard entrypoint; it must not write audit or metrics files.
- `scripts/madongmei_code_scorecard.py --json --no-record --reference-style` is the readonly reference-style parity view; keep it read-only and keep the default public scorecard surface green.
- Request routing metadata lives in `config/capability/request-route-registry.json`; authoring rules and schema live in `config/capability/request-route-authoring-guide.md` plus `config/capability/request-route-template-schema.json`; real-prompt route checks live in `scripts/request_route_real_prompt_suite.py` plus `config/capability/request-route-real-prompt-suite.json`.
- Public route sidecar policies live in `config/capability/llmwiki-v2-policy.json`, `config/capability/wiki-coverage-thresholds.json`, and `config/capability/phase-thresholds.json`; keep them sanitized, repo-relative, and free of private knowledge rows.
- `memoryctl pre-hook --json` should explain the public route through `codex_context`, `route_trace`, and a conservative `tool_route`; tool hints are readonly and must keep `auto_execute=false`.
- Public LongMemEval replay lives in `scripts/longmemeval_benchmark_suite.py` plus `scripts/longmemeval_madongmei_runner.py`; keep artifacts compact, public-path-safe, and aligned with `benchmarks/longmemeval/official-suite-summary.json`.
- P0/P1 alignment should preserve MaDongMei-compatible public command names and governance checks while implementing them as public adapters over MaDongMei data and templates.
- Do not add individual skill pages or individual wiki-topic pages for P2; generic skill/wiki templates are the intended public representation.
