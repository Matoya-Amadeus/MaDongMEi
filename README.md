# MaDongMei

给 Codex 和其他 agent 用的公开记忆控制平面：把记忆抓取、请求时上下文注入、能力路由、公开治理门禁和 LongMemEval replay 放到一条可验证的开源链路里。  
A public memory control plane for Codex and other agents: memory capture, request-time context injection, capability routing, public governance gates, and LongMemEval replay in one verifiable open-source path.

MaDongMei 迁移的是公开能力，不迁移个人记忆、隐私数据、私有 wiki 正文、私有 skill 正文、设备路径或密钥。  
MaDongMei carries public capability only; it does not ship personal memories, private data, private wiki bodies, private skill bodies, device paths, or secrets.

![MaDongMei banner](./assets/readme-banner.svg)

## 近期更新
## Recent Notes

更新时间：2026-05-06 10:20

Update time: 2026-05-06 10:20

更新内容：README 改成新手优先的开源首页：先讲这是啥、能解决什么、1 分钟怎么跑、LongMemEval 命中与评分怎么读、Codex 专属安装链怎么生效。

Update content: Reworked the README into a beginner-first open-source home page: what it is, what it solves, the one-minute path, how to read LongMemEval hit/score results, and how the Codex-only install chain works.

### 2026-05-03

更新时间：2026-05-03 17:40

Update time: 2026-05-03 17:40

更新内容：补上最小公开 LongMemEval 迁移链：`scripts/longmemeval_madongmei_runner.py`、`scripts/longmemeval_benchmark_suite.py`、真实 compact snapshot、以及让 `eval` / `regression-gate` 读取真实 benchmark 指标；pre-hook 仍保持只公开 `codex_context`、`route_trace`、`tool_route`，不迁移私有记忆内容。

Update content: Added the minimal public LongMemEval migration chain: `scripts/longmemeval_madongmei_runner.py`, `scripts/longmemeval_benchmark_suite.py`, real compact snapshots, and benchmark-backed `eval` / `regression-gate`; the pre-hook still exposes only `codex_context`, `route_trace`, and `tool_route`, without migrating private memory content.

## 一眼看懂
## At a Glance

| 你关心什么 | 先看哪里 | 成功标志 |
| --- | --- | --- |
| 这是啥 / 谁该用 | `这是什么`、`解决什么问题` | 5 秒知道要不要继续读 |
| 先跑什么 | `安装`、`三分钟上手` | 看到 `passed=true` 和 `scorecard` 通过 |
| 长文本记忆评估 | `LongMemEval 评估、命中与结果解读` | 看到最新可验证快照 |
| Codex 专属自动注入 | `Codex 专属安装链` | `memoryctl pre-hook` 输出 `[MADONGMEI MEMORY]` |
| 维护状态 | `近期更新`、`FAQ` | 看到日期、反馈入口和当前状态 |

这张表先回答“这是啥、谁该用、先跑什么、哪里看结果”。  
This first panel answers what it is, who it is for, what to run first, and where to read the results.

## Table of Contents

- [一眼看懂 / At a Glance](#一眼看懂)
- [近期更新 / Recent Notes](#近期更新)
- [这是什么 / What It Is](#这是什么)
- [解决什么问题 / What It Solves](#解决什么问题)
- [安装 / Installation](#安装)
- [三分钟上手 / Quick Start](#三分钟上手)
- [术语速查 / Terms](#术语速查)
- [LongMemEval 评估、命中与结果解读 / LongMemEval Evaluation, Hit Routing, and Results](#longmemeval-评估命中与结果解读)
- [Codex 专属安装链 / Codex-only Install Chain](#codex-专属安装链)
- [结构总览 / Structure Map](#结构总览)
- [工作链路 / How It Works](#工作链路)
- [常用场景 / Common Scenarios](#常用场景)
- [配置与参数 / Configuration & CLI Reference](#配置与参数)
- [常见问题 / FAQ](#常见问题)
- [故障排查 / Troubleshooting](#故障排查)
- [公开投影与隐私边界 / Public Projection and Privacy Boundary](#公开投影与隐私边界)
- [文档入口 / Docs Entry Points](#文档入口)
- [验证链 / Verification Chain](#验证链)
- [仓库里有什么 / What Is Included](#仓库里有什么)
- [License](#license)

## 这是什么
## What It Is

MaDongMei 是给 Codex 和其他 agent 用的公开记忆控制平面。  
MaDongMei is a public memory control plane for Codex and other agents.

它负责公开记忆抓取、请求时注入、能力路由、公开治理和可复现评估。  
It handles public memory capture, request-time injection, capability routing, public governance, and reproducible evaluation.

它不是单纯的 benchmark 仓库，也不是训练框架；它把安装链、上下文桥、路由元数据、scorecard 和 LongMemEval replay 放在同一条可审计链路里。  
It is not just a benchmark repository or a training framework; it puts the install chain, context bridge, route metadata, scorecard, and LongMemEval replay on one auditable rail.

## 解决什么问题
## What It Solves

如果你想把 agent 记忆能力开源，但又不想把个人资料、私有 wiki、设备路径和密钥带出去，MaDongMei 把公开能力、隐私边界和 release gate 放在一起。  
If you want to open-source agent memory without shipping personal data, private wiki bodies, device paths, or secrets, MaDongMei keeps public capability, privacy boundaries, and release gates together.

| 普通长评估工具 | MaDongMei |
| --- | --- |
| 只看 benchmark 分数 | benchmark + 安装链 + 上下文桥 + 隐私门禁 |
| 只跑离线脚本 | 还验证 Codex 请求时的 memory 注入 |
| 结果和发布分开 | scorecard、route suite、release gate 同链 |

这就是它比“只有评估脚本”的仓库更有用的地方。  
That is why it is more useful than a repository that only ships evaluation scripts.

## 安装
## Installation

最低要求是 Python 3、POSIX shell、可写的 `CODEX_HOME` 和 `MADONGMEI_HOME`。运行时状态不会写进 tracked 文件。  
The minimum requirements are Python 3, a POSIX shell, and writable `CODEX_HOME` plus `MADONGMEI_HOME`. Runtime state is not written into tracked files.

```bash
git clone <your-fork-or-this-repo-url> MaDongMei
cd MaDongMei
./bootstrap.sh
./scripts/install_context_bridge.sh
./install_selfcheck.sh
```

如果你只想在临时目录试跑，不污染默认 home，可以显式传入 `--home`。  
If you want an isolated trial without touching the default home, pass `--home` explicitly.

```bash
TMP_HOME="$(mktemp -d)"
./bootstrap.sh --home "$TMP_HOME"
./scripts/install_context_bridge.sh --home "$TMP_HOME" --json
```

## 三分钟上手
## Quick Start

其实 1 分钟内就能看见成效。  
You can usually see it working in about a minute.

```bash
./memoryctl pre-hook --query "public install memory" --json
./memoryctl context templates --json
python3 scripts/madongmei_code_scorecard.py --json --no-record
```

你要找的关键标记是：  
The key markers to look for are:

- `[MADONGMEI MEMORY]`
- `codex_context.repo == "MaDongMei"`
- `tool_route.auto_execute == false`
- `score == 100`

如果你想先喂一段最小样例，可以用 `templates/public-memory-sample.jsonl` 当 demo 载荷。  
If you want a tiny sample payload, start from `templates/public-memory-sample.jsonl`.

## 术语速查
## Terms

下面是最容易卡住的新术语。  
These are the terms most likely to trip up first-time readers.

| 术语 | 一句话解释 |
| --- | --- |
| LongMemEval | 500 题的长会话记忆评估，用来看 top-k 检索是否把正确 session 找回来。 |
| Recall@5 | 前 5 个结果里是否出现任一正确 session。 |
| Recall@10 | 前 10 个结果里是否出现任一正确 session。 |
| NDCG@10 | 前 10 个结果的排序质量，越靠前越高。 |
| 命中优化 | 用 query signals + conservative rerank 提升 top-k 命中。 |
| Codex-only 安装链 | 只在 Codex 请求时注入公开 memory，不做全局 shell hook。 |

这里的 LongMemEval 是检索回放，不是端到端问答；benchmark 评分和仓库 scorecard 也不是一回事。  
Here LongMemEval is retrieval replay, not end-to-end QA; benchmark scores and the repo scorecard are also not the same thing.

## LongMemEval 评估、命中与结果解读
## LongMemEval Evaluation, Hit Routing, and Results

本仓库公开验证的是 LongMemEval-S 的检索回放：同一数据集、同一 granularity、同一 profile，先看 top-k 命中，再看 NDCG。  
This repo publicly validates LongMemEval-S retrieval replay: same dataset, same granularity, same profile, first top-k hit rate, then NDCG.

当前公开回放覆盖 `madongmei_semantic_hybrid` 的 `default` 和 `tfidf_fallback`。  
The current public replay covers `madongmei_semantic_hybrid` with `default` and `tfidf_fallback`.

| 指标 | 看什么 |
| --- | --- |
| Recall@5 | top 5 是否命中任一 gold session |
| Recall@10 | top 10 是否命中任一 gold session |
| NDCG@10 | top 10 的排名质量 |
| 命中优化 | preference / temporal / multi-session 信号驱动的保守 rerank |

| profile | Recall@5 | Recall@10 | NDCG@10 | 备注 |
| --- | --- | --- | --- | --- |
| default | 1.0 | 1.0 | 1.0 | latest validated public compact snapshot |
| tfidf_fallback | 1.0 | 1.0 | 1.0 | fallback profile |

命中优化主要靠 `scripts/memory_query_signals.py`：它识别 preference、temporal、multi-session 信号，再把这些信号交给公开 route 和 replay 链路。  
Hit optimization mainly comes from `scripts/memory_query_signals.py`: it detects preference, temporal, and multi-session signals, then feeds them into the public route and replay chain.

`manifests/metrics/longmemeval_latest_suite.json` 是当前最新的公开 compact 快照；`benchmarks/longmemeval/official-suite-summary.json` 是对应的公开摘要。  
`manifests/metrics/longmemeval_latest_suite.json` is the current latest public compact snapshot; `benchmarks/longmemeval/official-suite-summary.json` is the corresponding public summary.

如果你要接新模型，先固定同一 dataset、profile、granularity 和 metrics，再重跑同一套 replay。  
If you plug in a new model, lock the same dataset, profile, granularity, and metrics, then rerun the same replay.

## Codex 专属安装链
## Codex-only Install Chain

这条链只给 Codex 请求时的上下文注入，不是全局 shell hook，也不是其他 agent 的自动注入。  
This chain only injects request-time context for Codex; it is not a global shell hook and not an automatic hook for other agents.

1. `./bootstrap.sh` 解析 `MADONGMEI_HOME`、`CODEX_HOME`、`MADONGMEI_BRIDGE_ROOT`，并创建公开运行时目录。  
   `./bootstrap.sh` resolves `MADONGMEI_HOME`, `CODEX_HOME`, and `MADONGMEI_BRIDGE_ROOT`, then creates the public runtime directories.

2. `./scripts/install_context_bridge.sh` 调 `memoryctl context install`，在配置好的 `CODEX_HOME` 下生成 Codex bridge 和公开 `model_instructions_file`。  
   `./scripts/install_context_bridge.sh` calls `memoryctl context install` to create the Codex bridge and public `model_instructions_file` under the configured `CODEX_HOME`.

3. `./memoryctl pre-hook --query "..." --json` 只在 Codex 请求路径里加载公开记忆、组装 `[MADONGMEI MEMORY]`、并发出保守的 `tool_route`。  
   `./memoryctl pre-hook --query "..." --json` loads public memory, assembles `[MADONGMEI MEMORY]`, and emits a conservative `tool_route` only in the Codex request path.

## 结构总览
## Structure Map

- `memoryctl` + `src/madongmei/cli.py` 是统一 CLI 入口，覆盖 memory、context、workspace、graph、MCP、eval 和 governance 命令。  
  `memoryctl` plus `src/madongmei/cli.py` is the unified CLI surface for memory, context, workspace, graph, MCP, eval, and governance commands.

- `src/madongmei/request_context.py` + `src/madongmei/codex_bridge.py` 负责 request pre-hook、公开 memory block、`model_instructions_file` 注入和 context bridge 安装。  
  `src/madongmei/request_context.py` plus `src/madongmei/codex_bridge.py` powers the request pre-hook, public memory block, `model_instructions_file` injection, and context bridge installation.

- `config/capability/` + `templates/capability/` 保存公开 route registry、template schema、authoring guide、real-prompt suite、llmwiki/wiki/phase 阈值和通用能力模板。  
  `config/capability/` plus `templates/capability/` stores the public route registry, template schema, authoring guide, real-prompt suite, llmwiki/wiki/phase thresholds, and generic capability templates.

- `src/madongmei/governance.py` + `scripts/` 提供 privacy audit、config schema gate、doctor、scorecard、push/release gate、ignored artifact report 和 LongMemEval replay。  
  `src/madongmei/governance.py` plus `scripts/` provides privacy audit, config schema gates, doctor, scorecard, push/release gates, ignored-artifact reporting, and LongMemEval replay.

- `knowledge/` 保存安装、排障、运行原则、storage audit、retention policy 和公开 wiki 入口。  
  `knowledge/` contains installation, troubleshooting, operating principles, storage audit, retention policy, and the public wiki entrypoint.

## 工作链路
## How It Works

1. `scripts/local_env.sh` 和 `bootstrap.sh` 解析环境变量，创建 `MADONGMEI_HOME`、`CODEX_HOME/.madongmei-runtime`、workspace registry、graph DB 等运行时根目录。  
   `scripts/local_env.sh` and `bootstrap.sh` resolve environment variables and create the runtime roots for `MADONGMEI_HOME`, `CODEX_HOME/.madongmei-runtime`, the workspace registry, and the graph database.

2. `scripts/install_context_bridge.sh` 调 `memoryctl context install`，在配置好的 `CODEX_HOME` 下生成 bridge 环境和公开 `model_instructions_file`。  
   `scripts/install_context_bridge.sh` calls `memoryctl context install` to generate the bridge environment and the public `model_instructions_file` under the configured `CODEX_HOME`.

3. 请求进入 Codex 时，`memoryctl pre-hook` 加载公开记录、做请求分类，并组装 `[MADONGMEI MEMORY]` block；同时从 `config/capability/request-route-registry.json` 生成 route trace 和 readonly tool hint。  
   When a request reaches Codex, `memoryctl pre-hook` loads public records, classifies the request, assembles the `[MADONGMEI MEMORY]` block, and derives a route trace plus readonly tool hint from `config/capability/request-route-registry.json`.

4. 公开 route metadata 受 `config/capability/request-route-template-schema.json`、`config/capability/request-route-authoring-guide.md`、`config/capability/request-route-real-prompt-suite.json`、`config/capability/llmwiki-v2-policy.json`、`config/capability/wiki-coverage-thresholds.json` 和 `config/capability/phase-thresholds.json` 约束。  
   Public route metadata is governed by `config/capability/request-route-template-schema.json`, `config/capability/request-route-authoring-guide.md`, `config/capability/request-route-real-prompt-suite.json`, `config/capability/llmwiki-v2-policy.json`, `config/capability/wiki-coverage-thresholds.json`, and `config/capability/phase-thresholds.json`.

5. 公开治理链把 tracked worktree、ignored local artifacts、`.git` history、compact benchmark snapshot 和 release readiness 分开检查。  
   The public governance chain checks tracked worktree, ignored local artifacts, `.git` history, compact benchmark snapshots, and release readiness as separate concerns.

## 常用场景
## Common Scenarios

- 抓取一条公开记忆。  
  Capture one public memory record.

  ```bash
  ./memoryctl capture --text "Prefer compact public reports." --json
  ```

- 搜索公开记忆。  
  Search public memory records.

  ```bash
  ./memoryctl search "compact reports" --json
  ```

- 生成 Codex 请求时上下文。  
  Generate request-time context for Codex.

  ```bash
  ./memoryctl pre-hook --query "How should this repo validate release readiness?" --json
  ```

- 检查公开 route registry 的真实 prompt 回放。  
  Replay real prompt cases against the public route registry.

  ```bash
  python3 scripts/request_route_real_prompt_suite.py --json
  ```

- 跑 LongMemEval compact suite。  
  Run the LongMemEval compact suite.

  ```bash
  python3 scripts/longmemeval_benchmark_suite.py <data-file> --backends madongmei_semantic_hybrid,madongmei_semantic_hybrid:tfidf_fallback --granularity session
  ```

- 查看 ignored local artifacts，不执行删除。  
  Inspect ignored local artifacts without deleting anything.

  ```bash
  python3 scripts/local_ignored_artifact_report.py --json
  ```

## 配置与参数
## Configuration & CLI Reference

| 名称 | 默认值 | 作用 |
| --- | --- | --- |
| `MADONGMEI_HOME` | `~/.madongmei` | 公开记忆和本地配置根目录 |
| `CODEX_HOME` | `~/.codex` | Codex 运行时根目录 |
| `MADONGMEI_BRIDGE_ROOT` | `CODEX_HOME/.madongmei-runtime` | context bridge 运行时根目录 |
| `MEMORY_RUNTIME_DIR` | `CODEX_HOME/.madongmei-runtime/memory` | workspace registry、graph、report 共用状态目录 |
| `WORKSPACE_SOURCE_ROOT` | 未固定 | workspace 源目录 |
| `WORKSPACE_REGISTRY_FILE` | runtime 内注册表 | workspace 注册表文件 |
| `MADONGMEI_GRAPH_DB_PATH` | runtime 内 SQLite DB | personal graph 数据库路径 |
| `MADONGMEI_GRAPH_SNAPSHOT_DIR` | runtime 内 snapshot 目录 | personal graph 快照目录 |
| `MADONGMEI_WIKI_DIR` | 可覆盖 | 公开 wiki 输出目录 |
| `MADONGMEI_SKILL_DIR` | 可覆盖 | 公开 skill 输出目录 |

常用 CLI 分组如下；完整参数以 `./memoryctl <command> --help` 和脚本 `--json` 输出为准。  
Common CLI groups are below; use `./memoryctl <command> --help` and script `--json` output as the final reference.

| 分组 | 命令 | 用途 |
| --- | --- | --- |
| Memory | `capture`, `search`, `recall`, `ingest`, `compact`, `export-jsonl`, `import-jsonl`, `autopilot`, `pre-hook` | 公开记忆读写、召回、导入导出和请求时注入 |
| Context | `context template`, `context templates`, `context install` | 公开 request context 模板和 Codex bridge 安装 |
| Workspace | `workspace status`, `workspace list`, `workspace register`, `workspace remove`, `workspace cleanup` | workspace 注册、状态和清理 |
| Graph / Personal | `graph`, `graph-build`, `graph-query`, `personal-capture`, `personal-search`, `personal-doctor`, `personal-snapshot`, `personal-restore` | 公开 personal graph 适配层 |
| MCP / Eval | `mcp-serve --manifest`, `eval`, `eval-ab`, `eval-dashboard`, `phase-gate`, `orchestrate`, `scripts/longmemeval_benchmark_suite.py` | MCP manifest、评估、阶段门禁、编排和 LongMemEval replay |
| Governance | `scripts/privacy_audit.sh`, `scripts/export_public_projection.py`, `scripts/madongmei_code_scorecard.py`, `scripts/push_readiness.sh`, `scripts/release_strict_gate.sh` | 隐私、公开投影、scorecard、push/release readiness |

## 常见问题
## FAQ

### 这是个什么仓库？
### What is this repository?

它是给 Codex 和其他 agent 用的公开记忆控制平面，不是只放 benchmark 的脚本仓库。  
It is a public memory control plane for Codex and other agents, not just a bucket of benchmark scripts.

### 它会自动把私有记忆写进开源仓库吗？
### Will it automatically write private memory into the open repository?

不会。`config/public-projection.yaml` 只允许公开能力、模板、schema 和可发布证据进入 tracked 文件。  
No. `config/public-projection.yaml` only allows public capability, templates, schemas, and publishable evidence into tracked files.

### `LongMemEval` 分数和 `scorecard` 为什么不一样？
### Why are the LongMemEval score and the scorecard different?

`LongMemEval` 看检索命中和排序质量；`scorecard` 看仓库健康、门禁和公开边界。  
`LongMemEval` measures retrieval hits and ranking quality; the scorecard measures repository health, gates, and public boundaries.

### `pre-hook` 为什么没有输出？
### Why does `pre-hook` produce no output?

先确认你是通过 Codex 请求路径调用它的，再检查 `./scripts/install_context_bridge.sh` 是否完成。  
First confirm that you are calling it through the Codex request path, then check whether `./scripts/install_context_bridge.sh` completed.

### 反馈和 bug 在哪里提？
### Where should feedback and bugs go?

优先走 GitHub Issues / PR；如果是本地安装问题，先看 `knowledge/troubleshooting.md`。  
Prefer GitHub Issues / PR; if it is a local install issue, start with `knowledge/troubleshooting.md`.

## 故障排查
## Troubleshooting

- `install_context_bridge.sh` 失败：先跑 `./bootstrap.sh --home <tmp>`，确认 `CODEX_HOME` 和 `MADONGMEI_HOME` 可写，再重试安装。  
  `install_context_bridge.sh` fails: run `./bootstrap.sh --home <tmp>` first, confirm `CODEX_HOME` and `MADONGMEI_HOME` are writable, then retry the install.

- `pre-hook` 没有 `[MADONGMEI MEMORY]`：确认这是 Codex 请求路径，不要只在普通 shell 里手动试。  
  `pre-hook` has no `[MADONGMEI MEMORY]`: confirm you are on the Codex request path instead of testing from a plain shell.

- `quality_gate` / `scorecard` 报错：先跑 `./scripts/privacy_audit.sh --json`、`python3 scripts/request_route_real_prompt_suite.py --json`、`python3 scripts/madongmei_code_scorecard.py --json --no-record`。  
  `quality_gate` / `scorecard` fails: run `./scripts/privacy_audit.sh --json`, `python3 scripts/request_route_real_prompt_suite.py --json`, and `python3 scripts/madongmei_code_scorecard.py --json --no-record` first.

- LongMemEval 分数异常：检查数据集、profile、granularity、backend 和 `manifests/metrics/longmemeval_latest_suite.json` 是否一致。  
  LongMemEval numbers look off: check that the dataset, profile, granularity, backend, and `manifests/metrics/longmemeval_latest_suite.json` match.

## 公开投影与隐私边界
## Public Projection and Privacy Boundary

`config/public-projection.yaml` 是公开投影规则源，动作只有 `copy`、`sanitize`、`template`、`omit` 四种。  
`config/public-projection.yaml` is the source of truth for public projection, with only four actions: `copy`, `sanitize`, `template`, and `omit`.

- 个人记忆、persona、identity、workspace private memory 不进入开源包。  
  Personal memory, persona, identity, and workspace-private memory stay out of the open bundle.

- 私有 wiki 正文、私有 skill 正文、私有引用样例不进入开源包。  
  Private wiki bodies, private skill bodies, and private reference examples stay out of the open bundle.

- 本机 runtime 状态、隐私路径、token、private key、私有 remote 不进入 tracked 文件。  
  Device-local runtime state, private paths, tokens, private keys, and private remotes never belong in tracked files.

- P2 单个 skill/wiki 不做逐页公开镜像，只保留 `templates/skill-page.template.md`、`templates/wiki-page.template.md` 和 `templates/capability/` 这类通用模板。  
  P2 does not publish per-skill or per-wiki mirrors; it keeps generic templates such as `templates/skill-page.template.md`, `templates/wiki-page.template.md`, and `templates/capability/`.

建议把下面几条当成公开包的隐私与 release 验收线。  
Treat these commands as the privacy and release acceptance line for the public bundle.

```bash
scripts/privacy_audit.sh --json
scripts/export_public_projection.py --check --json
scripts/llmwiki_source_ref_gate.py --json
scripts/local_ignored_artifact_report.py --json
python3 scripts/request_route_real_prompt_suite.py --json
python3 scripts/madongmei_code_scorecard.py --json --no-record
```

## 文档入口
## Docs Entry Points

- `knowledge/installation.md`：安装和 bridge 注入说明。  
  `knowledge/installation.md`: installation and bridge-injection guide.

- `knowledge/troubleshooting.md`：常见失败与排查路径。  
  `knowledge/troubleshooting.md`: common failures and troubleshooting paths.

- `knowledge/operating-principles.md`：公开运行原则。  
  `knowledge/operating-principles.md`: public operating principles.

- `knowledge/repo-storage-audit.md`：tracked worktree、ignored local artifacts、runtime cache 和 `.git` history 的检查入口。  
  `knowledge/repo-storage-audit.md`: entrypoint for checking tracked worktree, ignored local artifacts, runtime cache, and `.git` history.

- `knowledge/repo-retention-policy.md`：compact benchmark、metrics、audit、runtime cache 和 release 证据的保留边界。  
  `knowledge/repo-retention-policy.md`: retention boundaries for compact benchmarks, metrics, audits, runtime cache, and release evidence.

- `knowledge/wiki/README.md`：公开 wiki 入口。  
  `knowledge/wiki/README.md`: public wiki entrypoint.

## 验证链
## Verification Chain

当前公开验证链如下。  
The current public verification chain is:

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
./install_selfcheck.sh
./install_validation_matrix.sh
./quality_gate.sh
python3 scripts/request_route_real_prompt_suite.py --json
python3 scripts/madongmei_code_scorecard.py --json --no-record
python3 scripts/madongmei_doctor.py --json
python3 scripts/longmemeval_benchmark_suite.py <data-file> --backends madongmei_semantic_hybrid,madongmei_semantic_hybrid:tfidf_fallback --granularity session --record-history
scripts/push_readiness.sh --strict --task-type code --json
scripts/release_strict_gate.sh --json
```

README 只描述公开链路；如果验证命令发现隐私路径、硬编码、private remote marker、scorecard P0、compact snapshot 缺失或 route suite 回归，应先修复证据链，再发布。  
The README describes the public chain only; if validation finds private paths, hardcoded values, private remote markers, scorecard P0s, missing compact snapshots, or route-suite regressions, fix the evidence chain before publishing.

## 仓库里有什么
## What Is Included

- `src/madongmei/`：CLI、bridge、request context、store、workspace、graph、MCP 和 governance 代码。  
  `src/madongmei/`: CLI, bridge, request context, store, workspace, graph, MCP, and governance code.

- `scripts/`：安装、doctor、privacy、push/release gate、readonly scorecard、route suite、storage audit 和 benchmark 脚本。  
  `scripts/`: installation, doctor, privacy, push/release gates, readonly scorecard, route suite, storage audit, and benchmark scripts.

- `config/`：公开投影、治理策略、capability policy、request-route registry、gate matrix 和 scorecard 标准。  
  `config/`: public projection, governance policy, capability policy, request-route registry, gate matrix, and scorecard standard.

- `templates/`：公开 model instructions、request context、LLMWiki、skill/wiki、workspace registry 和 capability route 模板。  
  `templates/`: public model instructions, request context, LLMWiki, skill/wiki, workspace registry, and capability-route templates.

- `knowledge/`：安装、排障、运行原则、storage audit、retention policy 和公开 wiki 入口。  
  `knowledge/`: installation, troubleshooting, operating principles, storage audit, retention policy, and public wiki entrypoint.

- `tests/`：contract、smoke、store、route、scorecard、LongMemEval runner 和 public naming 测试。  
  `tests/`: contract, smoke, store, route, scorecard, LongMemEval runner, and public naming tests.

- `benchmarks/longmemeval/` + `manifests/metrics/`：公开 compact benchmark snapshot 和 latest suite alias。  
  `benchmarks/longmemeval/` plus `manifests/metrics/`: public compact benchmark snapshot and latest suite alias.

## License
## License

`LICENSE` 当前为 MIT License。  
`LICENSE` is currently the MIT License.

由 **AI·MaDongMei** 和 **人类·Matoya** 共同维护
Maintained jointly by **AI·MaDongMei** and **Human·Matoya**
