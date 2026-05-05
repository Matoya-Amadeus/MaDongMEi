# Request Route Capability Authoring Guide

新增 public skill / tool / memory / wiki route 能力时，先写模板实例，再接 registry、schema 和真实 prompt 回归。模板不是建议，是公开路由的强约束输入。

## Required files

- `templates/capability/skill-route.template.json`
- `templates/capability/tool-hint.template.json`
- `templates/capability/memory-route.template.json`
- `templates/capability/wiki-route.template.json`
- `templates/capability/real-prompt-case.template.json`
- `config/capability/request-route-registry.json`
- `config/capability/request-route-template-schema.json`
- `config/capability/request-route-real-prompt-suite.json`
- `config/capability/llmwiki-v2-policy.json`
- `config/capability/wiki-coverage-thresholds.json`
- `config/capability/phase-thresholds.json`

## New capability checklist

1. 写 registry 实例，并保证 id / topic_id 唯一。
2. 补 aliases、positive_examples、negative_examples。
3. 补 threshold_policy 或 route_threshold_band，并说明阈值来源。
4. skill route 要补 suppression_rules、tool_hints、wiki_affinity、llmwiki_affinity、capture_policy。
5. tool hint 必须 advisory-only，`auto_execute=false`，并补 paired_intents / paired_skills / paired_routes。
6. memory route 要补 capture、recall、privacy、budget、recording、promotion 决策。
7. wiki route 要补 capture_allowed、fallback_to_llmwiki、negative_routes。
8. 每个新 capability 至少补 `positive`、`negative`、`mixed`、`zh_natural` 四类真实 prompt 标签。
9. 跑 `python3 scripts/request_route_real_prompt_suite.py --json --no-record`。
10. 跑 `python3 scripts/config_schema_gate.py --json`、`python3 -m unittest tests.test_request_route_strengthening` 和 `bash ./quality_gate.sh`。
11. 更新 `README.md`、`AGENTS.md`、必要时更新 `config/public-projection.yaml`。

## Runtime rules

- Runtime source of truth: `config/capability/request-route-registry.json`.
- Authoring source: `templates/capability/*.template.json`.
- Schema source: `config/capability/request-route-template-schema.json`.
- Regression source: `config/capability/request-route-real-prompt-suite.json`.
- LLMWiki policy source: `config/capability/llmwiki-v2-policy.json`.
- Wiki coverage source: `config/capability/wiki-coverage-thresholds.json`.
- Capability phase threshold source: `config/capability/phase-thresholds.json`.
- `scripts/request_route_real_prompt_suite.py` is readonly and only verifies expected routes.
- Runtime should fail open when metadata is missing or malformed, but governance/schema checks must fail closed.
