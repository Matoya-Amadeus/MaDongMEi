# MaDongMei Open Source Manifest

Date: 2026-04-17

## Included surface

- `README.md`
- `AGENTS.md`
- `LICENSE`
- `.env.example`
- `bootstrap.sh`
- `install_selfcheck.sh`
- `install_validation_matrix.sh`
- `quality_gate.sh`
- `memoryctl`
- `scripts/`
- `knowledge/`
- `knowledge/wiki/`
- `templates/`
- `skills/public-autopilot/`
- `tests/`
- `src/madongmei/`

## Excluded surface

- Personal secrets.
- Private paths.
- Device-local runtime state.
- Cache, bytecode, logs, and temporary backups.

## Validation contract

- `bootstrap -> install_selfcheck -> install_validation_matrix -> quality_gate`
- `memoryctl` must support `autopilot`, `capture`, `search`, `recall`, `review`, `doctor`, `weekly-review`, `export-jsonl`, and `import-jsonl`.
- Public framework entrypoints should also cover `context`, `workspace`, `graph`, and `mcp-serve`.

## Notes

This manifest records the public boundary only. It is not a mirror of any private repository.
The open bundle keeps framework and templates only; private memory content, wiki content, and skill content are intentionally excluded.

## Migration checklist

- Request context bridge: templates, install scaffold, and Codex-targeted install chain.
- Workspace registry: register, list, remove, cleanup, and status.
- Personal graph framework: capture, search, connect, timeline, review, doctor, snapshot, and restore.
- MCP service surface: stdio serve plus manifest export.
- Template-only content: request context, wiki page, skill page, graph page, workspace registry, and sample config.
