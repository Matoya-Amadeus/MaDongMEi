# Public Repo Storage Audit

Use this public audit before proposing cleanup.

1. Split repository size into `tracked worktree`, `ignored local artifacts`, and `.git` history.
2. Treat ignored runtime and cache folders as local rebuildable state until proven otherwise.
3. Keep release-facing evidence and tracked benchmark snapshots distinct from ignored local output.
4. Prefer readonly reporting first: `scripts/local_ignored_artifact_report.py --json` and `python3 scripts/madongmei_code_scorecard.py --json --no-record`.

## Audit checklist

- tracked worktree: what is intentionally versioned
- ignored local artifacts: Finder metadata, Python cache, local runtime cache, build output
- `.git` history: commit/object storage separate from worktree size
- rebuild cost: whether the ignored artifact is cheap to recreate

Do not treat a large ignored directory as proof that the public repository should delete tracked files.
