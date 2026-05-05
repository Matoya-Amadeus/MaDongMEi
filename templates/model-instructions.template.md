# MaDongMei Codex Memory Bridge

Use the public MaDongMei memory bridge for request-time context.

- Runtime home: `{{madongmei_home}}`
- Bridge root: `{{bridge_root}}`
- Memory runtime: `{{memory_runtime_dir}}`
- Before a task that benefits from public memory, call `memoryctl pre-hook --query "<request>"`.
- Treat returned `[MADONGMEI MEMORY]` blocks as public summaries only.
- Capture reusable public notes with `memoryctl autopilot`.
- Do not import private paths, secrets, personal notes, or device-local state.
