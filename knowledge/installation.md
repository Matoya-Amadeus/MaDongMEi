# Installation

1. Clone the repo on any machine with Python 3 and a POSIX shell.
2. Run `./bootstrap.sh` to create the public state layout.
3. Run `./scripts/install_context_bridge.sh` to install the Codex bridge and generated model instructions.
4. Run `./install_selfcheck.sh`.
5. Run `./install_validation_matrix.sh`.
6. Run `./quality_gate.sh`.
7. Use `./memoryctl pre-hook --query "<request>"` for Codex request-time public memory context.
8. Use `./memoryctl autopilot` for the public recall/classify/capture/promote flow.

The default data root is `~/.madongmei/`.
Set `MADONGMEI_HOME` to override it for a clean install or a test run.
Set `CODEX_HOME` when installing into an isolated Codex runtime.
Set `MADONGMEI_WIKI_DIR` and `MADONGMEI_SKILL_DIR` when promoted wiki/skill outputs should live outside the repo.

Tracked files must keep environment placeholders; generated runtime files may contain the local install paths under the configured homes.

## P0/P1 alignment

MaDongMei exposes MaDongMei-compatible public command names and governance checks as adapters over public data and templates. Skill/wiki content remains generic-template-only; individual private skill or wiki topic pages are not mirrored.
