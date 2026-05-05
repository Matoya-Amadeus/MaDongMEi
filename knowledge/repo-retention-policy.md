# Public Repo Retention Policy

This public repository keeps capability, templates, and compact benchmark evidence. It does not keep private bodies or device-local runtime state.

## Retention boundaries

- tracked worktree: keep public code, public docs, public templates, and compact benchmark snapshots
- ignored local artifacts: treat as rebuildable local state unless a task explicitly promotes them
- `.git` history: analyze separately from worktree size
- benchmark snapshots: keep compact public summary files in `benchmarks/longmemeval/`
- benchmark metrics: keep compact public latest/history artifacts in `manifests/metrics/`
- runtime cache: do not track `.madongmei-runtime` outputs in versioned files

## Cleanup order

1. report ignored artifacts
2. separate tracked worktree from ignored local artifacts
3. inspect rebuild cost before deletion
4. keep public release evidence compact and readable
