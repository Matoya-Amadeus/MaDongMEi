# Troubleshooting

## `memoryctl` cannot find data

Run `./bootstrap.sh` first. Then confirm `MADONGMEI_HOME` and `MADONGMEI_DB_PATH` point to a writable location.

## Codex automatic memory injection is missing

Run `./scripts/install_context_bridge.sh`, then check that `CODEX_HOME/config.toml` contains `model_instructions_file` and that the referenced file exists. Validate with:

```bash
./memoryctl pre-hook --query "public install memory" --json
```

The command should return a public `[MADONGMEI MEMORY]` block and should fail open instead of blocking the request.

## Search returns no results

Use a broader query, or capture at least one public note first.

## Autopilot writes into the wrong workspace

Check `MADONGMEI_WIKI_DIR` and `MADONGMEI_SKILL_DIR`. For isolated runs, point them at the temporary home before running `./bootstrap.sh`.

## Validation fails

Run the commands in this order:

1. `./install_selfcheck.sh`
2. `./install_validation_matrix.sh`
3. `./quality_gate.sh`
4. `python3 scripts/madongmei_doctor.py --json`

If one step fails, fix that layer before moving on.

## Privacy gate fails

Run `scripts/privacy_audit.sh --json` and remove private paths, tokens, copied private memory, private wiki bodies, private skill bodies, or device-local state from tracked files. Use templates instead.

## P0/P1 alignment

MaDongMei exposes MaDongMei-compatible public command names and governance checks as adapters over public data and templates. Skill/wiki content remains generic-template-only; individual private skill or wiki topic pages are not mirrored.
