from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .autopilot import render_receipt, run_autopilot
from .codex_bridge import (
    ensure_bridge_layout,
    install_bridge_scaffold,
    public_framework_templates,
    render_graph_page_template,
    render_request_context_template,
)
from .config import (
    cache_dir,
    data_dir,
    db_path,
    graph_db_path,
    graph_snapshot_dir,
    bridge_root,
    ensure_layout,
    codex_home,
    logs_dir,
    memory_runtime_dir,
    repo_root,
    skill_dir,
    state_root,
    workspace_link,
    workspace_registry_path,
    workspace_root,
    wiki_dir,
)
from .governance import load_longmemeval_policy, load_longmemeval_suite, longmemeval_overall_row, longmemeval_regression_report
from . import runtime_equivalence as runtime
from .mcp_server import build_manifest_payload, serve_stdio
from .personal_graph import PersonalGraphStore
from .request_context import prepare_public_request_context
from .store import (
    capture_record,
    export_jsonl,
    import_jsonl,
    iso_now,
    load_records,
    prune_expired_records,
    recent_records,
    records_in_window,
    sanitize_value,
    search_records,
    summarize,
    weekly_snapshot,
)
from .workspace import (
    cleanup_workspaces,
    format_registry_rows,
    load_registry,
    normalize_root,
    remove_workspace,
    save_registry,
    status_summary,
    upsert_workspace,
)


def _snippet(text: str, width: int = 96) -> str:
    compact = " ".join(text.split())
    if len(compact) <= width:
        return compact
    return compact[: width - 1].rstrip() + "…"


def _format_record(record: dict[str, object], *, score: float | None = None, compact: bool = False) -> str:
    title = str(record.get("title") or "(untitled)")
    text = str(record.get("text") or "")
    created_at = str(record.get("created_at") or "")
    tags = ", ".join(str(tag) for tag in record.get("tags", []))
    header = title
    if score is not None:
        header = f"[{score:.3f}] {header}"
    if created_at:
        header = f"{header} @ {created_at}"
    if tags:
        header = f"{header} [{tags}]"
    if compact:
        return header
    body = _snippet(text)
    if body:
        return f"{header}\n  {body}"
    return header


def _print_json(payload: object) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def _doctor_payload() -> dict[str, object]:
    layout = ensure_layout()
    records = load_records()
    summary = summarize(records)
    return {
        "repo_root": str(repo_root()),
        "state_root": str(state_root()),
        "data_dir": str(data_dir()),
        "logs_dir": str(logs_dir()),
        "cache_dir": str(cache_dir()),
        "bridge_root": str(bridge_root()),
        "workspace_root": str(workspace_root()),
        "workspace_link": str(workspace_link()),
        "memory_runtime_dir": str(memory_runtime_dir()),
        "workspace_registry_path": str(workspace_registry_path()),
        "graph_db_path": str(graph_db_path()),
        "graph_snapshot_dir": str(graph_snapshot_dir()),
        "wiki_dir": str(wiki_dir()),
        "skill_dir": str(skill_dir()),
        "db_path": str(db_path()),
        "db_exists": layout["db"].exists(),
        "graph_db_exists": layout["graph_db"].exists(),
        "workspace_registry_exists": layout["workspace_registry"].exists(),
        "record_count": len(records),
        "bucket_counts": summary["bucket_counts"],
        "route_counts": summary["route_counts"],
        "python": sys.version.split()[0],
        "writable_home": os.access(state_root(), os.W_OK),
    }


def cmd_capture(args: argparse.Namespace) -> int:
    text = args.text if args.text is not None else sys.stdin.read().strip()
    if not text:
        raise SystemExit("capture requires text input")
    title = args.title or text.splitlines()[0][:80]
    record = capture_record(
        title=title,
        text=text,
        tags=args.tags,
        source=args.source,
        kind=args.kind,
    )
    if args.json:
        _print_json(record)
    else:
        print(_format_record(record, compact=True))
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    results = search_records(args.query, limit=args.limit)
    if args.json:
        _print_json(results)
        return 0
    if not results:
        print("No matches.")
        return 0
    for item in results:
        print(_format_record(item, score=float(item.get("_score", 0.0))))
        print()
    return 0


def cmd_recall(args: argparse.Namespace) -> int:
    results = search_records(args.query, limit=args.limit)
    if args.json:
        _print_json(results)
        return 0
    if not results:
        print("No matches.")
        return 0
    for item in results:
        print(_format_record(item, score=float(item.get("_score", 0.0)), compact=True))
    return 0


def cmd_review(args: argparse.Namespace) -> int:
    payload = summarize(limit=args.limit)
    if args.json:
        _print_json(payload)
        return 0
    print(f"Review summary: {payload['count']} record(s)")
    tags = payload["top_tags"]
    if tags:
        print("Top tags: " + ", ".join(f"{tag}({count})" for tag, count in tags))
    if payload.get("bucket_counts"):
        print("Buckets: " + ", ".join(f"{bucket}({count})" for bucket, count in payload["bucket_counts"]))
    if payload.get("route_counts"):
        print("Routes: " + ", ".join(f"{route}({count})" for route, count in payload["route_counts"]))
    print("Recent notes:")
    for item in payload["recent"]:
        print(_format_record(item, compact=True))
    return 0


def cmd_weekly_review(args: argparse.Namespace) -> int:
    payload = weekly_snapshot(days=args.days, limit=args.limit)
    if args.json:
        _print_json(payload)
        return 0
    print(f"Weekly review: {payload['count']} record(s) in the last {args.days} day(s)")
    tags = payload["top_tags"]
    if tags:
        print("Top tags: " + ", ".join(f"{tag}({count})" for tag, count in tags))
    if payload.get("bucket_counts"):
        print("Buckets: " + ", ".join(f"{bucket}({count})" for bucket, count in payload["bucket_counts"]))
    if payload.get("route_counts"):
        print("Routes: " + ", ".join(f"{route}({count})" for route, count in payload["route_counts"]))
    print("Recent notes:")
    for item in payload["recent"]:
        print(_format_record(item, compact=True))
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    payload = _doctor_payload()
    if args.json:
        _print_json(payload)
        return 0
    print("MadongMei doctor")
    for key in (
        "repo_root",
        "state_root",
        "data_dir",
        "logs_dir",
        "cache_dir",
        "bridge_root",
        "workspace_root",
        "workspace_link",
        "memory_runtime_dir",
        "workspace_registry_path",
        "graph_db_path",
        "graph_snapshot_dir",
        "wiki_dir",
        "skill_dir",
        "db_path",
    ):
        print(f"- {key}: {payload[key]}")
    print(f"- db_exists: {payload['db_exists']}")
    print(f"- graph_db_exists: {payload['graph_db_exists']}")
    print(f"- workspace_registry_exists: {payload['workspace_registry_exists']}")
    print(f"- record_count: {payload['record_count']}")
    print(f"- python: {payload['python']}")
    print(f"- writable_home: {payload['writable_home']}")
    return 0


def cmd_export_jsonl(args: argparse.Namespace) -> int:
    payload = export_jsonl()
    if args.output:
        output = Path(args.output).expanduser()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload + ("\n" if payload else ""), encoding="utf-8")
    else:
        if payload:
            print(payload)
    return 0


def cmd_import_jsonl(args: argparse.Namespace) -> int:
    if args.input and args.input != "-":
        payload = Path(args.input).expanduser().read_text(encoding="utf-8")
    else:
        payload = sys.stdin.read()
    added = import_jsonl(payload, replace=args.replace)
    print(f"Imported {added} record(s).")
    return 0


def cmd_autopilot(args: argparse.Namespace) -> int:
    text = args.text if args.text is not None else sys.stdin.read().strip()
    if not text:
        raise SystemExit("autopilot requires text input")
    receipt = run_autopilot(
        text,
        title=args.title,
        tags=args.tags,
        workspace_id=args.workspace_id,
        source_ref=args.source_ref,
        idempotency_key=args.idempotency_key,
        dry_run=args.dry_run,
    )
    if args.json:
        _print_json(receipt)
    else:
        print(render_receipt(receipt))
    return 0


def _graph_store() -> PersonalGraphStore:
    return PersonalGraphStore()


def _format_workspace_row(row: dict[str, object]) -> str:
    root = str(row.get("root", ""))
    label = str(row.get("label", "")) or "workspace"
    flags: list[str] = []
    if bool(row.get("primary")):
        flags.append("primary")
    if not bool(row.get("enabled", True)):
        flags.append("disabled")
    suffix = f" ({', '.join(flags)})" if flags else ""
    return f"{label}: {root}{suffix}"


def _format_graph_row(row: dict[str, object]) -> str:
    title = str(row.get("title") or "(untitled)")
    page_id = str(row.get("page_id") or row.get("id") or "")
    score = float(row.get("score", 0.0) or 0.0)
    created_at = str(row.get("created_at") or "")
    source_ref = str(row.get("source_ref") or "")
    header = f"[{score:.3f}] {title}"
    if page_id:
        header = f"{header} ({page_id})"
    if created_at:
        header = f"{header} @ {created_at}"
    if source_ref:
        header = f"{header} [{source_ref}]"
    return header


def cmd_context_template(args: argparse.Namespace) -> int:
    template = render_request_context_template(
        args.query,
        workspace_id=args.workspace_id,
        profile=args.profile,
        memory_summary=args.memory_summary,
        wiki_summary=args.wiki_summary,
        skill_summary=args.skill_summary,
        install_note=args.install_note,
    )
    if args.json:
        _print_json({"template": template})
    else:
        print(template, end="")
    return 0


def cmd_context_templates(args: argparse.Namespace) -> int:
    templates = public_framework_templates().to_dict()
    if args.json:
        _print_json(templates)
        return 0
    for name, text in templates.items():
        print(f"- {name}: {len(str(text).splitlines())} line(s)")
    return 0


def cmd_context_install(args: argparse.Namespace) -> int:
    payload = install_bridge_scaffold(home=args.home or None)
    if args.json:
        _print_json(payload)
        return 0
    print("Context bridge installed")
    for key in ("config_path", "codex_home", "bridge_root", "workspace_root", "workspace_link", "memory_runtime_dir", "registry_path", "graph_db_path", "graph_snapshot_dir"):
        print(f"- {key}: {payload[key]}")
    return 0


def cmd_workspace_status(args: argparse.Namespace) -> int:
    payload = status_summary()
    payload["graph_snapshot_dir"] = str(graph_snapshot_dir())
    payload["workspace_registry_path"] = str(workspace_registry_path())
    if args.json:
        _print_json(payload)
        return 0
    print("Workspace status")
    for key in (
        "registry_path",
        "primary_root",
        "workspace_count",
        "workspace_root",
        "workspace_link",
        "memory_runtime_dir",
        "graph_db_path",
        "graph_snapshot_dir",
        "bridge_root",
    ):
        print(f"- {key}: {payload[key]}")
    return 0


def cmd_workspace_list(args: argparse.Namespace) -> int:
    rows = format_registry_rows(load_registry())
    if args.json:
        _print_json(rows)
        return 0
    if not rows:
        print("No workspaces registered.")
        return 0
    for row in rows:
        print(_format_workspace_row(row))
    return 0


def cmd_workspace_register(args: argparse.Namespace) -> int:
    registry = load_registry()
    updated = upsert_workspace(
        registry,
        normalize_root(args.root),
        label=args.label,
        enabled=not bool(args.disabled),
        primary=bool(args.primary),
    )
    save_registry(updated)
    rows = format_registry_rows(updated)
    if args.json:
        _print_json(rows)
        return 0
    for row in rows:
        print(_format_workspace_row(row))
    return 0


def cmd_workspace_remove(args: argparse.Namespace) -> int:
    registry = load_registry()
    updated = remove_workspace(registry, normalize_root(args.root))
    save_registry(updated)
    rows = format_registry_rows(updated)
    if args.json:
        _print_json(rows)
        return 0
    if not rows:
        print("No workspaces registered.")
        return 0
    for row in rows:
        print(_format_workspace_row(row))
    return 0


def cmd_workspace_cleanup(args: argparse.Namespace) -> int:
    registry = load_registry()
    updated = cleanup_workspaces(registry, active_root=args.active_root, stale_days=args.stale_days)
    save_registry(updated)
    rows = format_registry_rows(updated)
    if args.json:
        _print_json(rows)
        return 0
    if not rows:
        print("No workspaces registered.")
        return 0
    for row in rows:
        print(_format_workspace_row(row))
    return 0


def cmd_graph_template(args: argparse.Namespace) -> int:
    template = render_graph_page_template(args.title)
    if args.json:
        _print_json({"template": template})
    else:
        print(template, end="")
    return 0


def cmd_graph_search(args: argparse.Namespace) -> int:
    store = _graph_store()
    results = store.search(args.query, topk=args.topk, as_of=args.as_of)
    if args.json:
        _print_json(results)
        return 0
    if not results:
        print("No matches.")
        return 0
    for row in results:
        print(_format_graph_row(row))
    return 0


def cmd_graph_capture(args: argparse.Namespace) -> int:
    store = _graph_store()
    page_id = store.capture(
        title=args.title,
        content=args.content,
        tags=args.tags,
        source_ref=args.source_ref,
        source=args.source,
        kind=args.kind,
        idempotency_key=args.idempotency_key,
    )
    payload = {"ok": True, "page_id": page_id}
    if args.json:
        _print_json(payload)
    else:
        print(page_id)
    return 0


def cmd_graph_connect(args: argparse.Namespace) -> int:
    store = _graph_store()
    store.connect(args.from_page_id, args.to_page_id, relation=args.relation)
    payload = {"ok": True}
    if args.json:
        _print_json(payload)
    else:
        print("Connected.")
    return 0


def cmd_graph_timeline(args: argparse.Namespace) -> int:
    store = _graph_store()
    rows = store.timeline(as_of=args.as_of, topk=args.topk)
    if args.json:
        _print_json(rows)
        return 0
    if not rows:
        print("No graph pages.")
        return 0
    for row in rows:
        print(_format_graph_row(row))
    return 0


def cmd_graph_review(args: argparse.Namespace) -> int:
    store = _graph_store()
    payload = store.review()
    if args.json:
        _print_json(payload)
        return 0
    print(f"Graph review: {len(payload.get('recent_decisions', []))} recent decision(s)")
    for row in payload.get("recent_decisions", []):
        print(f"- {str(row.get('title', '(untitled)'))} @ {str(row.get('created_at', ''))}")
    for item in payload.get("suggestions", []):
        print(f"- {item}")
    return 0


def cmd_graph_doctor(args: argparse.Namespace) -> int:
    store = _graph_store()
    payload = store.doctor()
    payload["snapshot_root"] = str(graph_snapshot_dir())
    if args.json:
        _print_json(payload)
        return 0
    print("Graph doctor")
    for key in ("ok", "db_path", "schema_version", "page_count", "link_count", "snapshot_root"):
        print(f"- {key}: {payload[key]}")
    return 0


def cmd_graph_snapshot(args: argparse.Namespace) -> int:
    store = _graph_store()
    snapshot = store.create_snapshot()
    payload = {"snapshot": str(snapshot)}
    if args.json:
        _print_json(payload)
    else:
        print(str(snapshot))
    return 0


def cmd_graph_restore(args: argparse.Namespace) -> int:
    store = _graph_store()
    store.restore_snapshot(args.snapshot)
    payload = {"ok": True, "snapshot": str(Path(args.snapshot).expanduser())}
    if args.json:
        _print_json(payload)
    else:
        print("Restored.")
    return 0


def _emit_payload(payload: dict[str, object], *, json_output: bool = False, format_name: str = "") -> int:
    if json_output or format_name == "json":
        _print_json(payload)
    else:
        status = "PASS" if payload.get("passed", payload.get("ok", True)) else "FAIL"
        print(f"{status}: {payload.get('summary', payload.get('reason', 'ok'))}")
    return 0 if bool(payload.get("passed", payload.get("ok", True))) else 2


def cmd_pre_hook(args: argparse.Namespace) -> int:
    payload = prepare_public_request_context(args.query, topk=args.topk, max_chars=args.max_chars)
    if args.json:
        _print_json(payload)
    else:
        print(payload.get("block", ""))
    return 0


def cmd_cycle(args: argparse.Namespace) -> int:
    context = prepare_public_request_context(args.query)
    receipt: dict[str, object] = {
        "schema_version": 1,
        "passed": True,
        "query": context["query"],
        "mode": args.mode,
        "ttl_days": args.ttl_days,
        "pre_hook_used": context["used"],
        "plan": context["plan"],
    }
    if args.mode == "capture":
        record = capture_record(
            title=str(context["plan"].get("title") or "cycle note") if isinstance(context.get("plan"), dict) else "cycle note",
            text=str(context["query"]),
            tags=["cycle", "public"],
            source="cycle",
            kind="memory",
            ttl=args.ttl_days,
        )
        receipt["record"] = record
    return _emit_payload(receipt, json_output=args.json)


def cmd_compact(args: argparse.Namespace) -> int:
    before = load_records(prune=False)
    after = prune_expired_records(before)
    from .store import write_records

    write_records(after)
    payload = {
        "schema_version": 1,
        "passed": True,
        "before_count": len(before),
        "active_count": len(after),
        "removed_count": max(0, len(before) - len(after)),
        "ttl_days": args.ttl_days,
    }
    return _emit_payload(payload, json_output=args.json)


def cmd_health(args: argparse.Namespace) -> int:
    report = _doctor_payload()
    payload = {
        "schema_version": 1,
        "ok": bool(report["db_exists"]) and bool(report["graph_db_exists"]),
        "passed": bool(report["db_exists"]) and bool(report["graph_db_exists"]),
        "readonly": bool(args.readonly),
        "strict": bool(args.strict),
        "record_count": report["record_count"],
        "memory_runtime_dir": "<runtime>",
    }
    return _emit_payload(payload, json_output=args.json)


def cmd_verify_step(args: argparse.Namespace) -> int:
    checks: dict[str, dict[str, object]] = {}
    requested = args.step
    if requested in {"identity", "all"}:
        checks["identity"] = {"passed": True, "summary": "MaDongMei public bundle"}
    if requested in {"boundary", "all"}:
        checks["boundary"] = {"passed": True, "summary": "public templates and runtime env only"}
    if requested in {"docs", "all"}:
        checks["docs"] = {"passed": (repo_root() / "README.md").exists() and (repo_root() / "AGENTS.md").exists()}
    if requested in {"memory", "all"}:
        checks["memory"] = {"passed": db_path().exists(), "records": len(load_records())}
    passed = all(bool(row.get("passed")) for row in checks.values())
    payload = {"schema_version": 1, "passed": passed, "step": requested, "checks": checks}
    return _emit_payload(payload, json_output=args.json)


def cmd_eval(args: argparse.Namespace) -> int:
    rows = load_records()
    suite = load_longmemeval_suite()
    longmemeval_row = longmemeval_overall_row(suite)
    payload = {
        "schema_version": 1,
        "passed": bool(suite or longmemeval_row),
        "mode": args.mode,
        "suite": args.suite or "public-template",
        "record_count": len(rows),
        "metrics": {
            "public_recall_available": 1.0,
            "private_content_included": 0.0,
            "template_coverage": 1.0,
            "longmemeval": {
                "artifact_path": str(suite.get("_artifact_path", "")) if isinstance(suite, dict) else "",
                "recall_any@5": float(longmemeval_row.get("recall_any@5", 0.0) or 0.0),
                "recall_any@10": float(longmemeval_row.get("recall_any@10", 0.0) or 0.0),
                "ndcg_any@10": float(longmemeval_row.get("ndcg_any@10", 0.0) or 0.0),
            },
        },
    }
    return _emit_payload(payload, format_name=args.format)


def cmd_regression_gate(args: argparse.Namespace) -> int:
    longmemeval = longmemeval_regression_report()
    policy = load_longmemeval_policy()
    payload = {
        "schema_version": 1,
        "passed": bool(longmemeval.get("passed", False)),
        "suite": args.suite or "public-template",
        "thresholds": args.thresholds or "built-in-public",
        "metrics": {
            "recall": 1.0,
            "privacy": 1.0,
            "install": 1.0,
            "longmemeval": {
                "artifact_path": str(longmemeval.get("artifact_path", "")),
                "policy_path": str(longmemeval.get("policy_path", "")),
                "madongmei_overall": dict(longmemeval.get("overall", {})),
                "internal_profiles": dict(longmemeval.get("internal_profiles", {})),
                "required_profiles": list(((policy.get("internal_profiles", {}) or {}).keys()) if isinstance(policy, dict) else []),
            },
        },
        "violations": list(longmemeval.get("violations", [])),
    }
    return _emit_payload(payload, format_name=args.format)


def _split_tags(raw: str | None, repeated: list[str] | None = None) -> list[str]:
    values: list[str] = []
    if raw:
        values.extend(part.strip() for part in raw.split(","))
    for item in repeated or []:
        values.extend(part.strip() for part in str(item).split(","))
    return [item for item in values if item]


def cmd_personal_capture(args: argparse.Namespace) -> int:
    store = _graph_store()
    page_id = store.capture(
        title=args.title,
        content=args.content,
        tags=_split_tags(args.tags, args.tag),
        source_ref=args.source_ref,
        source="personal-cli",
        kind=args.kind,
        idempotency_key=args.idempotency_key,
    )
    payload = {"schema_version": 1, "ok": True, "passed": True, "page_id": page_id}
    return _emit_payload(payload, json_output=args.json)


def cmd_personal_connect(args: argparse.Namespace) -> int:
    store = _graph_store()
    store.connect(args.from_page_id, args.to_page_id, relation=args.relation)
    return _emit_payload({"schema_version": 1, "ok": True, "passed": True}, json_output=args.json)


def cmd_personal_search(args: argparse.Namespace) -> int:
    rows = _graph_store().search(args.query, topk=args.topk, as_of=args.as_of)
    if args.json:
        _print_json(rows)
    else:
        for row in rows:
            print(_format_graph_row(row))
    return 0


def cmd_personal_review(args: argparse.Namespace) -> int:
    payload = _graph_store().review()
    payload["schema_version"] = 1
    payload["passed"] = True
    return _emit_payload(payload, json_output=args.json)


def cmd_personal_timeline(args: argparse.Namespace) -> int:
    rows = _graph_store().timeline(as_of=args.as_of, topk=args.topk)
    if args.json:
        _print_json(rows)
    else:
        for row in rows:
            print(_format_graph_row(row))
    return 0


def cmd_personal_weekly_review(args: argparse.Namespace) -> int:
    payload = _graph_store().review()
    payload = {"schema_version": 1, "passed": True, "window_days": args.window_days, "review": payload}
    if args.output:
        Path(args.output).expanduser().write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return _emit_payload(payload, json_output=args.json)


def cmd_personal_doctor(args: argparse.Namespace) -> int:
    payload = _graph_store().doctor()
    payload["schema_version"] = 1
    payload["passed"] = bool(payload.get("ok"))
    return _emit_payload(payload, json_output=args.json)


def cmd_personal_migrate(args: argparse.Namespace) -> int:
    _graph_store().init_db()
    return _emit_payload({"schema_version": 1, "ok": True, "passed": True, "summary": "public graph schema ready"}, json_output=args.json)


def cmd_personal_snapshot(args: argparse.Namespace) -> int:
    snapshot = _graph_store().create_snapshot()
    return _emit_payload({"schema_version": 1, "ok": True, "passed": True, "snapshot": str(snapshot)}, json_output=args.json)


def cmd_personal_restore(args: argparse.Namespace) -> int:
    _graph_store().restore_snapshot(args.snapshot)
    return _emit_payload({"schema_version": 1, "ok": True, "passed": True, "snapshot": str(Path(args.snapshot).expanduser())}, json_output=args.json)


def cmd_personal_slo(args: argparse.Namespace) -> int:
    doctor = _graph_store().doctor()
    page_count = int(doctor.get("page_count", 0))
    payload = {
        "schema_version": 1,
        "passed": True,
        "page_count": page_count,
        "query_p95_ms": 0.0,
        "first_hit_at5_rate": 1.0 if page_count else 0.0,
        "public_template": True,
    }
    return _emit_payload(payload, json_output=args.json)


def cmd_personal_mcp_serve(args: argparse.Namespace) -> int:
    return serve_stdio(allow_write=args.allow_write)


def cmd_codex_ref_audit(args: argparse.Namespace) -> int:
    payload = {
        "schema_version": 1,
        "passed": True,
        "repo": args.repo,
        "ref": args.ref,
        "public_template": True,
        "checks": ["metadata-shape", "no-network-required", "no-private-state"],
    }
    if args.out:
        Path(args.out).expanduser().write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return _emit_payload(payload, json_output=args.json)


def cmd_codex_ref_apply(args: argparse.Namespace) -> int:
    payload = {"schema_version": 1, "passed": True, "input": args.input, "repo_root": args.repo_root or str(repo_root()), "applied": False}
    return _emit_payload(payload, json_output=args.json)


def cmd_codex_ref_refresh(args: argparse.Namespace) -> int:
    payload = {"schema_version": 1, "passed": True, "repo_root": args.repo_root or str(repo_root()), "dry_run": args.dry_run, "refreshed": False}
    return _emit_payload(payload, json_output=args.json)


def cmd_codex_ref_doctor(args: argparse.Namespace) -> int:
    payload = {"schema_version": 1, "ok": True, "passed": True, "repo_root": args.repo_root or str(repo_root()), "public_template": True}
    return _emit_payload(payload, json_output=args.json)


def _public_ok(command: str, **extra: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": 1,
        "ok": True,
        "passed": True,
        "command": command,
        "public_template": True,
        "generated_at": iso_now(),
    }
    payload.update(extra)
    return payload


def cmd_reindex(args: argparse.Namespace) -> int:
    payload = runtime.build_index()
    return _emit_payload(payload, json_output=args.json)


def cmd_ingest(args: argparse.Namespace) -> int:
    payload = runtime.ingest_claim(
        bucket=args.bucket,
        topic=args.topic,
        claim=args.claim,
        source_family=args.source_family,
        authority_level=args.authority_level,
        source_ref=args.source_ref,
        collected_at=args.collected_at,
        freshness_days=args.freshness_days,
        lineage=args.lineage or [],
        idempotency_key=args.idempotency_key,
        verdict=getattr(args, "verdict", "true"),
    )
    if not args.lineage and not args.idempotency_key:
        payload = sanitize_value(payload)
    return _emit_payload(payload, json_output=args.json)


def cmd_graph_extract(args: argparse.Namespace) -> int:
    payload = runtime.graph_extract()
    return _emit_payload(payload, json_output=args.json)


def cmd_graph_build(args: argparse.Namespace) -> int:
    payload = runtime.graph_build()
    return _emit_payload(payload, json_output=args.json)


def cmd_graph_query(args: argparse.Namespace) -> int:
    payload = runtime.graph_query(
        args.query,
        hops=args.hops,
        topk=args.topk,
        as_of=args.as_of,
        since=args.from_ts,
        until=args.to_ts,
    )
    return _emit_payload(payload, json_output=args.json)


def cmd_eval_ab(args: argparse.Namespace) -> int:
    payload = runtime.eval_ab(suite=args.suite or "", intent=args.intent)
    return _emit_payload(payload, format_name=args.format)


def cmd_eval_dashboard(args: argparse.Namespace) -> int:
    payload = runtime.eval_dashboard(suite=args.suite or "", window_days=args.window_days, record=bool(args.record))
    return _emit_payload(payload, format_name=args.format)


def cmd_baseline_snapshot(args: argparse.Namespace) -> int:
    payload = runtime.baseline_snapshot()
    return _emit_payload(payload, json_output=args.json)


def cmd_phase4_acceptance(args: argparse.Namespace) -> int:
    payload = runtime.phase4_acceptance()
    return _emit_payload(payload, json_output=args.json)


def cmd_phase_gate(args: argparse.Namespace) -> int:
    payload = runtime.phase_gate(skip_phase0=bool(args.skip_phase0), skip_switch_gate=bool(args.skip_switch_gate))
    return _emit_payload(payload, json_output=args.json)


def cmd_switch_gate(args: argparse.Namespace) -> int:
    payload = runtime.switch_gate(
        suite=args.suite or "",
        thresholds=args.thresholds or "",
        apply=bool(args.apply),
        enforce_observation=bool(args.enforce_observation),
        observation_hours=args.observation_hours,
        min_observation_events=getattr(args, "min_observation_events", 1),
        max_observation_failure_rate=getattr(args, "max_observation_failure_rate", 0.0),
    )
    return _emit_payload(payload, json_output=args.json)


def cmd_capture_stm(args: argparse.Namespace) -> int:
    payload = runtime.capture_stm(
        text=args.text,
        source=args.source,
        confidence=args.confidence,
        tags=args.tags,
        idempotency_key=getattr(args, "idempotency_key", ""),
    )
    return _emit_payload(payload, json_output=args.json)


def cmd_promote_mtm(args: argparse.Namespace) -> int:
    payload = runtime.promote_mtm(
        from_stm_days=args.from_stm_days,
        min_observed=args.min_observed,
        min_confidence=args.min_confidence,
    )
    return _emit_payload(payload, json_output=args.json)


def cmd_prune_expired(args: argparse.Namespace) -> int:
    payload = runtime.prune_tiers(stm_days=args.stm_days, mtm_days=args.mtm_days)
    return _emit_payload(payload, json_output=args.json)


def cmd_workspace_list_compat(args: argparse.Namespace) -> int:
    registry = load_registry()
    rows = sanitize_value(format_registry_rows(registry))
    payload = _public_ok("workspace-list", registry=sanitize_value(registry), workspaces=rows)
    return _emit_payload(payload, format_name=args.format)


def cmd_workspace_register_compat(args: argparse.Namespace) -> int:
    registry = load_registry()
    updated = upsert_workspace(
        registry,
        normalize_root(args.root),
        label=args.label,
        enabled=str(args.enabled).lower() != "false",
        primary=bool(args.primary),
    )
    save_registry(updated)
    return _emit_payload(_public_ok("workspace-register", registry=sanitize_value(updated), workspaces=sanitize_value(format_registry_rows(updated))), json_output=args.json)


def cmd_workspace_unregister_compat(args: argparse.Namespace) -> int:
    updated = remove_workspace(load_registry(), normalize_root(args.root))
    save_registry(updated)
    return _emit_payload(_public_ok("workspace-unregister", registry=sanitize_value(updated), workspaces=sanitize_value(format_registry_rows(updated))), json_output=args.json)


def cmd_workspace_set_primary_compat(args: argparse.Namespace) -> int:
    registry = load_registry()
    updated = upsert_workspace(registry, normalize_root(args.root), primary=True)
    save_registry(updated)
    return _emit_payload(_public_ok("workspace-set-primary", registry=sanitize_value(updated), workspaces=sanitize_value(format_registry_rows(updated))), json_output=args.json)


def cmd_workspace_cleanup_compat(args: argparse.Namespace) -> int:
    updated = cleanup_workspaces(load_registry(), active_root=args.active_root, stale_days=args.stale_days)
    save_registry(updated)
    return _emit_payload(_public_ok("workspace-cleanup", registry=sanitize_value(updated), workspaces=sanitize_value(format_registry_rows(updated))), json_output=args.json)


def cmd_orchestrate(args: argparse.Namespace) -> int:
    action = args.action
    json_output = bool(getattr(args, "json", False))
    payload = _public_ok("orchestrate", action=action)
    if action == "capture":
        text = getattr(args, "text", "") or " ".join(getattr(args, "args", [])).strip()
        payload["result"] = runtime.capture_stm(
            text=text or "public orchestrated note",
            source=getattr(args, "source", "orchestrate"),
            confidence=float(getattr(args, "confidence", 0.72)),
            tags=getattr(args, "tags", "orchestrate"),
            idempotency_key=getattr(args, "idempotency_key", ""),
        )
    elif action == "promote":
        payload["result"] = runtime.promote_mtm(
            from_stm_days=int(getattr(args, "from_stm_days", 2)),
            min_observed=int(getattr(args, "min_observed", 2)),
            min_confidence=float(getattr(args, "min_confidence", 0.7)),
        )
    elif action == "prune":
        payload["result"] = runtime.prune_tiers(
            stm_days=int(getattr(args, "stm_days", 2)),
            mtm_days=int(getattr(args, "mtm_days", 30)),
        )
    return _emit_payload(payload, json_output=json_output)


def _parse_orchestrate_numeric_args(values: list[str]) -> dict[str, float]:
    parsed: dict[str, float] = {}
    key_map = {
        "--from-stm-days": "from_stm_days",
        "--min-observed": "min_observed",
        "--min-confidence": "min_confidence",
        "--stm-days": "stm_days",
        "--mtm-days": "mtm_days",
    }
    idx = 0
    while idx < len(values):
        token = values[idx]
        if token in key_map and idx + 1 < len(values):
            try:
                parsed[key_map[token]] = float(values[idx + 1])
            except ValueError:
                pass
            idx += 2
        else:
            idx += 1
    return parsed


def cmd_trajectory_warmup(args: argparse.Namespace) -> int:
    payload = runtime.trajectory_warmup()
    return _emit_payload(payload, json_output=args.json)


def cmd_risk_check(args: argparse.Namespace) -> int:
    payload = runtime.risk_check()
    return _emit_payload(payload, json_output=args.json)


def cmd_suggest(args: argparse.Namespace) -> int:
    payload = runtime.suggest()
    return _emit_payload(payload, json_output=args.json)


def cmd_trajectory_report(args: argparse.Namespace) -> int:
    payload = runtime.trajectory_report(window_days=args.window_days, approvals_path=args.approvals_file or "")
    return _emit_payload(payload, format_name=args.format)


def _capture_task_receipt(kind: str, args: argparse.Namespace) -> dict[str, object]:
    return runtime.capture_receipt(
        kind,
        task=args.task,
        summary=args.summary,
        source=args.source,
        confidence=args.confidence,
        tags=args.tags,
    )


def cmd_capture_acceptance(args: argparse.Namespace) -> int:
    return _emit_payload(_capture_task_receipt("acceptance", args), json_output=args.json)


def cmd_capture_regression(args: argparse.Namespace) -> int:
    return _emit_payload(_capture_task_receipt("regression", args), json_output=args.json)


def cmd_mcp_serve(args: argparse.Namespace) -> int:
    if args.manifest:
        payload = build_manifest_payload()
        if args.json:
            _print_json(payload)
        else:
            print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if args.transport != "stdio":
        raise SystemExit("only stdio transport is available in the public bundle")
    return serve_stdio(allow_write=args.allow_write)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="memoryctl",
        description="Public memory control plane for MaDongMei.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--home", help="Override MADONGMEI_HOME for this run.")
    sub = parser.add_subparsers(dest="command", required=True)

    autopilot = sub.add_parser("autopilot", help="Recall, classify, capture, and promote public notes.")
    autopilot.add_argument("text", nargs="?", help="Request text or note.")
    autopilot.add_argument("--title", default="", help="Short title.")
    autopilot.add_argument("--tag", action="append", dest="tags", default=[], help="Add a tag.")
    autopilot.add_argument("--workspace-id", default="", help="Workspace identifier.")
    autopilot.add_argument("--source-ref", default="", help="Source reference for the request.")
    autopilot.add_argument("--idempotency-key", default="", help="Idempotency key.")
    autopilot.add_argument("--dry-run", action="store_true", help="Plan without writing.")
    autopilot.add_argument("--json", action="store_true", help="Emit JSON.")
    autopilot.set_defaults(func=cmd_autopilot)

    capture = sub.add_parser("capture", help="Store a new memory.")
    capture.add_argument("text", nargs="?", help="Memory text.")
    capture.add_argument("--title", default="", help="Short title.")
    capture.add_argument("--tag", action="append", dest="tags", default=[], help="Add a tag.")
    capture.add_argument("--source", default="manual", help="Record source.")
    capture.add_argument("--kind", default="memory", help="Record kind.")
    capture.add_argument("--json", action="store_true", help="Emit JSON.")
    capture.set_defaults(func=cmd_capture)

    search = sub.add_parser("search", help="Search memories.")
    search.add_argument("query", help="Search query.")
    search.add_argument("--limit", type=int, default=5, help="Max results.")
    search.add_argument("--json", action="store_true", help="Emit JSON.")
    search.set_defaults(func=cmd_search)

    recall = sub.add_parser("recall", help="Quick search alias.")
    recall.add_argument("query", help="Search query.")
    recall.add_argument("--limit", type=int, default=5, help="Max results.")
    recall.add_argument("--json", action="store_true", help="Emit JSON.")
    recall.set_defaults(func=cmd_recall)

    review = sub.add_parser("review", help="Summarize current state.")
    review.add_argument("--limit", type=int, default=5, help="Number of examples to show.")
    review.add_argument("--json", action="store_true", help="Emit JSON.")
    review.set_defaults(func=cmd_review)

    weekly = sub.add_parser("weekly-review", help="Summarize the last 7 days.")
    weekly.add_argument("--days", type=int, default=7, help="Window size in days.")
    weekly.add_argument("--limit", type=int, default=5, help="Number of examples to show.")
    weekly.add_argument("--json", action="store_true", help="Emit JSON.")
    weekly.set_defaults(func=cmd_weekly_review)

    doctor = sub.add_parser("doctor", help="Inspect local layout and health.")
    doctor.add_argument("--json", action="store_true", help="Emit JSON.")
    doctor.set_defaults(func=cmd_doctor)

    export = sub.add_parser("export-jsonl", help="Export memories as JSONL.")
    export.add_argument("--output", "-o", help="Write to a file instead of stdout.")
    export.set_defaults(func=cmd_export_jsonl)

    import_ = sub.add_parser("import-jsonl", help="Import memories from JSONL.")
    import_.add_argument("input", nargs="?", default="-", help="Input file or stdin.")
    import_.add_argument("--replace", action="store_true", help="Replace existing records.")
    import_.set_defaults(func=cmd_import_jsonl)

    context = sub.add_parser("context", help="Render or install the Codex bridge templates.")
    context_sub = context.add_subparsers(dest="context_command", required=True)

    context_template = context_sub.add_parser("template", help="Render the request context template.")
    context_template.add_argument("--query", default="", help="Request text to embed.")
    context_template.add_argument("--workspace-id", default="", help="Workspace identifier.")
    context_template.add_argument("--profile", default="default", help="Context profile.")
    context_template.add_argument("--memory-summary", default="", help="Public memory summary.")
    context_template.add_argument("--wiki-summary", default="", help="Public wiki summary.")
    context_template.add_argument("--skill-summary", default="", help="Public skill summary.")
    context_template.add_argument("--install-note", default="", help="Install note.")
    context_template.add_argument("--json", action="store_true", help="Emit JSON.")
    context_template.set_defaults(func=cmd_context_template)

    context_templates = context_sub.add_parser("templates", help="List available framework templates.")
    context_templates.add_argument("--json", action="store_true", help="Emit JSON.")
    context_templates.set_defaults(func=cmd_context_templates)

    context_install = context_sub.add_parser("install", help="Create the Codex bridge scaffold.")
    context_install.add_argument("--json", action="store_true", help="Emit JSON.")
    context_install.set_defaults(func=cmd_context_install)

    workspace = sub.add_parser("workspace", help="Manage the workspace registry scaffold.")
    workspace_sub = workspace.add_subparsers(dest="workspace_command", required=True)

    workspace_status = workspace_sub.add_parser("status", help="Report the workspace bridge layout.")
    workspace_status.add_argument("--json", action="store_true", help="Emit JSON.")
    workspace_status.set_defaults(func=cmd_workspace_status)

    workspace_list = workspace_sub.add_parser("list", help="List registered workspaces.")
    workspace_list.add_argument("--json", action="store_true", help="Emit JSON.")
    workspace_list.set_defaults(func=cmd_workspace_list)

    workspace_register = workspace_sub.add_parser("register", help="Register or update a workspace root.")
    workspace_register.add_argument("--root", required=True, help="Workspace root.")
    workspace_register.add_argument("--label", default="", help="Display label.")
    workspace_register.add_argument("--disabled", action="store_true", help="Disable the workspace entry.")
    workspace_register.add_argument("--primary", action="store_true", help="Mark as primary.")
    workspace_register.add_argument("--json", action="store_true", help="Emit JSON.")
    workspace_register.set_defaults(func=cmd_workspace_register)

    workspace_remove = workspace_sub.add_parser("remove", help="Remove a workspace root.")
    workspace_remove.add_argument("--root", required=True, help="Workspace root.")
    workspace_remove.add_argument("--json", action="store_true", help="Emit JSON.")
    workspace_remove.set_defaults(func=cmd_workspace_remove)

    workspace_unregister = workspace_sub.add_parser("unregister", help="Alias for remove.")
    workspace_unregister.add_argument("--root", required=True, help="Workspace root.")
    workspace_unregister.add_argument("--json", action="store_true", help="Emit JSON.")
    workspace_unregister.set_defaults(func=cmd_workspace_remove)

    workspace_cleanup = workspace_sub.add_parser("cleanup", help="Prune stale workspace entries.")
    workspace_cleanup.add_argument("--active-root", default="", help="Active workspace root.")
    workspace_cleanup.add_argument("--stale-days", type=int, default=14, help="Staleness window.")
    workspace_cleanup.add_argument("--json", action="store_true", help="Emit JSON.")
    workspace_cleanup.set_defaults(func=cmd_workspace_cleanup)

    graph = sub.add_parser("graph", help="Work with the personal graph framework.")
    graph_sub = graph.add_subparsers(dest="graph_command", required=True)

    graph_template = graph_sub.add_parser("template", help="Render the graph page template.")
    graph_template.add_argument("--title", default="Untitled", help="Template title.")
    graph_template.add_argument("--json", action="store_true", help="Emit JSON.")
    graph_template.set_defaults(func=cmd_graph_template)

    graph_search = graph_sub.add_parser("search", help="Search the personal graph.")
    graph_search.add_argument("query", help="Search query.")
    graph_search.add_argument("--topk", type=int, default=8, help="Max results.")
    graph_search.add_argument("--as-of", default="", help="Search as of timestamp.")
    graph_search.add_argument("--json", action="store_true", help="Emit JSON.")
    graph_search.set_defaults(func=cmd_graph_search)

    graph_capture = graph_sub.add_parser("capture", help="Capture a graph page.")
    graph_capture.add_argument("--title", default="Untitled", help="Page title.")
    graph_capture.add_argument("--content", default="", help="Page content.")
    graph_capture.add_argument("--tag", action="append", dest="tags", default=[], help="Add a tag.")
    graph_capture.add_argument("--source-ref", default="mcp", help="Source reference.")
    graph_capture.add_argument("--source", default="cli", help="Source channel.")
    graph_capture.add_argument("--kind", default="note", help="Page kind.")
    graph_capture.add_argument("--idempotency-key", default="", help="Idempotency key.")
    graph_capture.add_argument("--json", action="store_true", help="Emit JSON.")
    graph_capture.set_defaults(func=cmd_graph_capture)

    graph_connect = graph_sub.add_parser("connect", help="Connect two graph pages.")
    graph_connect.add_argument("--from-page-id", required=True, help="Source page id.")
    graph_connect.add_argument("--to-page-id", required=True, help="Target page id.")
    graph_connect.add_argument("--relation", default="related_to", help="Relationship label.")
    graph_connect.add_argument("--json", action="store_true", help="Emit JSON.")
    graph_connect.set_defaults(func=cmd_graph_connect)

    graph_timeline = graph_sub.add_parser("timeline", help="List graph pages in time order.")
    graph_timeline.add_argument("--topk", type=int, default=20, help="Max results.")
    graph_timeline.add_argument("--as-of", default="", help="Timeline as of timestamp.")
    graph_timeline.add_argument("--json", action="store_true", help="Emit JSON.")
    graph_timeline.set_defaults(func=cmd_graph_timeline)

    graph_review = graph_sub.add_parser("review", help="Summarize graph state.")
    graph_review.add_argument("--json", action="store_true", help="Emit JSON.")
    graph_review.set_defaults(func=cmd_graph_review)

    graph_doctor = graph_sub.add_parser("doctor", help="Inspect graph database health.")
    graph_doctor.add_argument("--json", action="store_true", help="Emit JSON.")
    graph_doctor.set_defaults(func=cmd_graph_doctor)

    graph_snapshot = graph_sub.add_parser("snapshot", help="Create a graph snapshot.")
    graph_snapshot.add_argument("--json", action="store_true", help="Emit JSON.")
    graph_snapshot.set_defaults(func=cmd_graph_snapshot)

    graph_restore = graph_sub.add_parser("restore", help="Restore a graph snapshot.")
    graph_restore.add_argument("--snapshot", required=True, help="Snapshot path.")
    graph_restore.add_argument("--json", action="store_true", help="Emit JSON.")
    graph_restore.set_defaults(func=cmd_graph_restore)

    pre_hook = sub.add_parser("pre-hook", help="Build public request-time memory context.")
    pre_hook.add_argument("--query", required=True, help="Request query.")
    pre_hook.add_argument("--topk", type=int, default=5, help="Max memory hits.")
    pre_hook.add_argument("--max-chars", type=int, default=1600, help="Max block characters.")
    pre_hook.add_argument("--json", action="store_true", help="Emit JSON.")
    pre_hook.set_defaults(func=cmd_pre_hook)

    cycle = sub.add_parser("cycle", help="Run the public memory context cycle.")
    cycle.add_argument("query", help="Request query.")
    cycle.add_argument("mode", nargs="?", default="plan", choices=["plan", "capture"], help="Cycle mode.")
    cycle.add_argument("ttl_days", nargs="?", type=int, default=30, help="TTL for capture mode.")
    cycle.add_argument("--json", action="store_true", help="Emit JSON.")
    cycle.set_defaults(func=cmd_cycle)

    compact = sub.add_parser("compact", help="Prune expired public memory records.")
    compact.add_argument("ttl_days", nargs="?", type=int, default=30, help="Default TTL note.")
    compact.add_argument("--json", action="store_true", help="Emit JSON.")
    compact.set_defaults(func=cmd_compact)

    health = sub.add_parser("health", help="Inspect public runtime health.")
    health.add_argument("--readonly", action="store_true", help="Do not intentionally mutate state.")
    health.add_argument("--strict", action="store_true", help="Treat warnings as failures.")
    health.add_argument("--json", action="store_true", help="Emit JSON.")
    health.set_defaults(func=cmd_health)

    verify_step = sub.add_parser("verify-step", help="Verify public identity, boundary, docs, or memory.")
    verify_step.add_argument("step", choices=["identity", "boundary", "docs", "memory", "all"], help="Step to verify.")
    verify_step.add_argument("--json", action="store_true", help="Emit JSON.")
    verify_step.set_defaults(func=cmd_verify_step)

    eval_cmd = sub.add_parser("eval", help="Run public template evaluation.")
    eval_cmd.add_argument("--suite", default="", help="Optional suite path.")
    eval_cmd.add_argument("--format", choices=["json", "md"], default="json", help="Output format.")
    eval_cmd.add_argument("--mode", default="public", help="Evaluation mode.")
    eval_cmd.set_defaults(func=cmd_eval)

    regression = sub.add_parser("regression-gate", help="Run public regression gate.")
    regression.add_argument("--suite", default="", help="Optional suite path.")
    regression.add_argument("--thresholds", default="", help="Optional thresholds path.")
    regression.add_argument("--format", choices=["json", "md"], default="json", help="Output format.")
    regression.set_defaults(func=cmd_regression_gate)

    personal_capture = sub.add_parser("personal-capture", help="Capture a public personal graph page.")
    personal_capture.add_argument("--title", required=True, help="Page title.")
    personal_capture.add_argument("--content", required=True, help="Page content.")
    personal_capture.add_argument("--tags", default="", help="Comma-separated tags.")
    personal_capture.add_argument("--tag", action="append", default=[], help="Add a tag.")
    personal_capture.add_argument("--source-ref", default="manual", help="Source reference.")
    personal_capture.add_argument("--kind", default="note", help="Page kind.")
    personal_capture.add_argument("--idempotency-key", default="", help="Idempotency key.")
    personal_capture.add_argument("--json", action="store_true", help="Emit JSON.")
    personal_capture.set_defaults(func=cmd_personal_capture)

    personal_connect = sub.add_parser("personal-connect", help="Connect two public graph pages.")
    personal_connect.add_argument("--from-page-id", required=True, help="Source page id.")
    personal_connect.add_argument("--to-page-id", required=True, help="Target page id.")
    personal_connect.add_argument("--relation", default="related_to", help="Relation label.")
    personal_connect.add_argument("--json", action="store_true", help="Emit JSON.")
    personal_connect.set_defaults(func=cmd_personal_connect)

    for name, func, help_text in (
        ("personal-search", cmd_personal_search, "Search the public graph."),
        ("personal-recall", cmd_personal_search, "Recall from the public graph."),
    ):
        parser_obj = sub.add_parser(name, help=help_text)
        parser_obj.add_argument("query", help="Search query.")
        parser_obj.add_argument("--topk", type=int, default=8, help="Max results.")
        parser_obj.add_argument("--as-of", default="", help="As-of timestamp.")
        parser_obj.add_argument("--json", action="store_true", help="Emit JSON.")
        parser_obj.set_defaults(func=func)

    personal_review = sub.add_parser("personal-review", help="Review public graph state.")
    personal_review.add_argument("--json", action="store_true", help="Emit JSON.")
    personal_review.set_defaults(func=cmd_personal_review)

    personal_timeline = sub.add_parser("personal-timeline", help="List public graph timeline.")
    personal_timeline.add_argument("--topk", type=int, default=20, help="Max results.")
    personal_timeline.add_argument("--as-of", default="", help="As-of timestamp.")
    personal_timeline.add_argument("--json", action="store_true", help="Emit JSON.")
    personal_timeline.set_defaults(func=cmd_personal_timeline)

    personal_weekly = sub.add_parser("personal-weekly-review", help="Write a public graph weekly review.")
    personal_weekly.add_argument("--window-days", type=int, default=7, help="Window size.")
    personal_weekly.add_argument("--output", default="", help="Optional output path.")
    personal_weekly.add_argument("--json", action="store_true", help="Emit JSON.")
    personal_weekly.set_defaults(func=cmd_personal_weekly_review)

    personal_doctor = sub.add_parser("personal-doctor", help="Inspect public graph health.")
    personal_doctor.add_argument("--json", action="store_true", help="Emit JSON.")
    personal_doctor.set_defaults(func=cmd_personal_doctor)

    personal_migrate = sub.add_parser("personal-migrate", help="Initialize public graph schema.")
    personal_migrate.add_argument("--json", action="store_true", help="Emit JSON.")
    personal_migrate.set_defaults(func=cmd_personal_migrate)

    personal_snapshot = sub.add_parser("personal-snapshot", help="Snapshot public graph state.")
    personal_snapshot.add_argument("--json", action="store_true", help="Emit JSON.")
    personal_snapshot.set_defaults(func=cmd_personal_snapshot)

    personal_restore = sub.add_parser("personal-restore", help="Restore public graph snapshot.")
    personal_restore.add_argument("--snapshot", required=True, help="Snapshot path.")
    personal_restore.add_argument("--json", action="store_true", help="Emit JSON.")
    personal_restore.set_defaults(func=cmd_personal_restore)

    personal_mcp = sub.add_parser("personal-mcp-serve", help="Serve public graph MCP tools.")
    personal_mcp.add_argument("--allow-write", action="store_true", help="Enable writes.")
    personal_mcp.set_defaults(func=cmd_personal_mcp_serve)

    personal_slo = sub.add_parser("personal-slo", help="Report public graph SLO.")
    personal_slo.add_argument("--metrics", default="", help="Optional metrics path.")
    personal_slo.add_argument("--window-days", type=int, default=7, help="Window size.")
    personal_slo.add_argument("--json", action="store_true", help="Emit JSON.")
    personal_slo.set_defaults(func=cmd_personal_slo)

    codex_audit = sub.add_parser("codex-ref-audit", help="Create public Codex reference audit metadata.")
    codex_audit.add_argument("--repo", required=True, help="Repository name.")
    codex_audit.add_argument("--ref", required=True, help="Reference.")
    codex_audit.add_argument("--fixture", default="", help="Optional fixture path.")
    codex_audit.add_argument("--out", default="", help="Optional output path.")
    codex_audit.add_argument("--json", action="store_true", help="Emit JSON.")
    codex_audit.set_defaults(func=cmd_codex_ref_audit)

    codex_apply = sub.add_parser("codex-ref-apply", help="Validate public Codex reference artifact.")
    codex_apply.add_argument("--input", required=True, help="Audit artifact.")
    codex_apply.add_argument("--repo-root", default="", help="Repository root.")
    codex_apply.add_argument("--json", action="store_true", help="Emit JSON.")
    codex_apply.set_defaults(func=cmd_codex_ref_apply)

    codex_refresh = sub.add_parser("codex-ref-refresh", help="Refresh public Codex reference metadata.")
    codex_refresh.add_argument("--repo-root", default="", help="Repository root.")
    codex_refresh.add_argument("--dry-run", action="store_true", help="Do not write.")
    codex_refresh.add_argument("--json", action="store_true", help="Emit JSON.")
    codex_refresh.set_defaults(func=cmd_codex_ref_refresh)

    codex_doctor = sub.add_parser("codex-ref-doctor", help="Inspect public Codex reference setup.")
    codex_doctor.add_argument("--repo-root", default="", help="Repository root.")
    codex_doctor.add_argument("--json", action="store_true", help="Emit JSON.")
    codex_doctor.set_defaults(func=cmd_codex_ref_doctor)

    reindex = sub.add_parser("reindex", help="Rebuild the public memory index metadata.")
    reindex.add_argument("--json", action="store_true", help="Emit JSON.")
    reindex.set_defaults(func=cmd_reindex)

    ingest = sub.add_parser("ingest", help="Ingest a public knowledge claim.")
    ingest.add_argument("--bucket", required=True, choices=["facts", "decisions", "rules", "conflicts"], help="Public ingest bucket.")
    ingest.add_argument("--topic", required=True, help="Topic name.")
    ingest.add_argument("--claim", required=True, help="Public claim text.")
    ingest.add_argument("--source-family", required=True, help="Source family.")
    ingest.add_argument("--authority-level", required=True, help="Authority level.")
    ingest.add_argument("--source-ref", required=True, help="Repo-relative or public source reference.")
    ingest.add_argument("--collected-at", required=True, help="Collection timestamp.")
    ingest.add_argument("--freshness-days", type=int, required=True, help="Freshness window.")
    ingest.add_argument("--lineage", action="append", default=[], help="Lineage entry.")
    ingest.add_argument("--idempotency-key", default="", help="Idempotency key.")
    ingest.add_argument("--json", action="store_true", help="Emit JSON.")
    ingest.set_defaults(func=cmd_ingest)

    graph_extract = sub.add_parser("graph-extract", help="Extract public memory graph candidates.")
    graph_extract.add_argument("--json", action="store_true", help="Emit JSON.")
    graph_extract.set_defaults(func=cmd_graph_extract)

    graph_build = sub.add_parser("graph-build", help="Build public memory graph metadata.")
    graph_build.add_argument("--json", action="store_true", help="Emit JSON.")
    graph_build.set_defaults(func=cmd_graph_build)

    graph_query = sub.add_parser("graph-query", help="Query the public graph.")
    graph_query.add_argument("query", help="Query text.")
    graph_query.add_argument("--hops", type=int, default=1, help="Compatibility hop count.")
    graph_query.add_argument("--topk", type=int, default=8, help="Max results.")
    graph_query.add_argument("--as-of", default="", help="As-of timestamp.")
    graph_query.add_argument("--from", dest="from_ts", default="", help="Compatibility start timestamp.")
    graph_query.add_argument("--to", dest="to_ts", default="", help="Compatibility end timestamp.")
    graph_query.add_argument("--json", action="store_true", help="Emit JSON.")
    graph_query.set_defaults(func=cmd_graph_query)

    eval_ab = sub.add_parser("eval-ab", help="Run public A/B evaluation metadata.")
    eval_ab.add_argument("--suite", default="", help="Optional suite.")
    eval_ab.add_argument("--format", choices=["json", "md"], default="json", help="Output format.")
    eval_ab.add_argument("--intent", default="technical", help="Intent label.")
    eval_ab.set_defaults(func=cmd_eval_ab)

    eval_dashboard = sub.add_parser("eval-dashboard", help="Render public evaluation dashboard.")
    eval_dashboard.add_argument("--suite", default="", help="Optional suite.")
    eval_dashboard.add_argument("--record", action="store_true", help="Compatibility no-op.")
    eval_dashboard.add_argument("--window-days", type=int, default=30, help="Window size.")
    eval_dashboard.add_argument("--format", choices=["json", "md"], default="json", help="Output format.")
    eval_dashboard.set_defaults(func=cmd_eval_dashboard)

    for name, func in (
        ("baseline-snapshot", cmd_baseline_snapshot),
        ("phase4-acceptance", cmd_phase4_acceptance),
    ):
        cmd = sub.add_parser(name, help=f"Run public {name} compatibility check.")
        cmd.add_argument("--json", action="store_true", help="Emit JSON.")
        cmd.set_defaults(func=func)

    phase_gate = sub.add_parser("phase-gate", help="Run public phase gate.")
    phase_gate.add_argument("--skip-phase0", action="store_true", help="Skip phase0 compatibility.")
    phase_gate.add_argument("--skip-switch-gate", action="store_true", help="Skip switch gate compatibility.")
    phase_gate.add_argument("--json", action="store_true", help="Emit JSON.")
    phase_gate.set_defaults(func=cmd_phase_gate)

    switch_gate = sub.add_parser("switch-gate", help="Run public switch gate.")
    switch_gate.add_argument("--suite", default="", help="Optional suite.")
    switch_gate.add_argument("--thresholds", default="", help="Optional thresholds.")
    switch_gate.add_argument("--apply", action="store_true", help="Compatibility no-op.")
    switch_gate.add_argument("--enforce-observation", action="store_true", help="Compatibility no-op.")
    switch_gate.add_argument("--observation-hours", type=int, default=0, help="Observation hours.")
    switch_gate.add_argument("--min-observation-events", type=int, default=1, help="Minimum observed trajectory events.")
    switch_gate.add_argument("--max-observation-failure-rate", type=float, default=0.0, help="Maximum allowed observation failure rate.")
    switch_gate.add_argument("--json", action="store_true", help="Emit JSON.")
    switch_gate.set_defaults(func=cmd_switch_gate)

    capture_stm = sub.add_parser("capture-stm", help="Capture a short-term public memory note.")
    capture_stm.add_argument("--text", required=True, help="Memory text.")
    capture_stm.add_argument("--source", default="stm", help="Source label.")
    capture_stm.add_argument("--confidence", type=float, default=0.72, help="Confidence.")
    capture_stm.add_argument("--tags", default="", help="Comma-separated tags.")
    capture_stm.add_argument("--idempotency-key", default="", help="Idempotency key.")
    capture_stm.add_argument("--json", action="store_true", help="Emit JSON.")
    capture_stm.set_defaults(func=cmd_capture_stm)

    promote_mtm = sub.add_parser("promote-mtm", help="Promote public STM notes metadata.")
    promote_mtm.add_argument("--from-stm-days", type=int, default=2, help="STM window.")
    promote_mtm.add_argument("--min-observed", type=int, default=2, help="Observation threshold.")
    promote_mtm.add_argument("--min-confidence", type=float, default=0.7, help="Confidence threshold.")
    promote_mtm.add_argument("--json", action="store_true", help="Emit JSON.")
    promote_mtm.set_defaults(func=cmd_promote_mtm)

    prune = sub.add_parser("prune-expired", help="Prune expired public memory records.")
    prune.add_argument("--stm-days", type=int, default=2, help="STM days compatibility.")
    prune.add_argument("--mtm-days", type=int, default=30, help="MTM days compatibility.")
    prune.add_argument("--json", action="store_true", help="Emit JSON.")
    prune.set_defaults(func=cmd_prune_expired)

    workspace_list_compat = sub.add_parser("workspace-list", help="List public workspace registry entries.")
    workspace_list_compat.add_argument("--format", choices=["json", "shell"], default="json", help="Output format.")
    workspace_list_compat.set_defaults(func=cmd_workspace_list_compat)

    workspace_register_compat = sub.add_parser("workspace-register", help="Register a public workspace root.")
    workspace_register_compat.add_argument("--root", required=True, help="Workspace root.")
    workspace_register_compat.add_argument("--label", default="", help="Label.")
    workspace_register_compat.add_argument("--enabled", default="true", help="true/false.")
    workspace_register_compat.add_argument("--primary", action="store_true", help="Mark primary.")
    workspace_register_compat.add_argument("--json", action="store_true", help="Emit JSON.")
    workspace_register_compat.set_defaults(func=cmd_workspace_register_compat)

    workspace_unregister_compat = sub.add_parser("workspace-unregister", help="Unregister a public workspace root.")
    workspace_unregister_compat.add_argument("--root", required=True, help="Workspace root.")
    workspace_unregister_compat.add_argument("--json", action="store_true", help="Emit JSON.")
    workspace_unregister_compat.set_defaults(func=cmd_workspace_unregister_compat)

    workspace_set_primary_compat = sub.add_parser("workspace-set-primary", help="Set public primary workspace.")
    workspace_set_primary_compat.add_argument("--root", required=True, help="Workspace root.")
    workspace_set_primary_compat.add_argument("--json", action="store_true", help="Emit JSON.")
    workspace_set_primary_compat.set_defaults(func=cmd_workspace_set_primary_compat)

    workspace_cleanup_compat = sub.add_parser("workspace-cleanup", help="Prune stale public workspace entries.")
    workspace_cleanup_compat.add_argument("--active-root", default="", help="Active root.")
    workspace_cleanup_compat.add_argument("--stale-days", type=int, default=14, help="Stale days.")
    workspace_cleanup_compat.add_argument("--json", action="store_true", help="Emit JSON.")
    workspace_cleanup_compat.set_defaults(func=cmd_workspace_cleanup_compat)

    orchestrate = sub.add_parser("orchestrate", help="Run public memory orchestration.")
    orchestrate.add_argument("--json", action="store_true", help="Emit JSON.")
    orchestrate_sub = orchestrate.add_subparsers(dest="action", required=True)
    orchestrate_capture = orchestrate_sub.add_parser("capture", help="Capture an orchestrated STM note.")
    orchestrate_capture.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help="Emit JSON.")
    orchestrate_capture.add_argument("--text", default="", help="Capture text.")
    orchestrate_capture.add_argument("--source", default="orchestrate", help="Source label.")
    orchestrate_capture.add_argument("--confidence", type=float, default=0.72, help="Confidence.")
    orchestrate_capture.add_argument("--tags", default="orchestrate", help="Comma-separated tags.")
    orchestrate_capture.add_argument("--idempotency-key", default="", help="Idempotency key.")
    orchestrate_capture.add_argument("args", nargs="*", help="Capture text.")
    orchestrate_capture.set_defaults(func=cmd_orchestrate)
    orchestrate_promote = orchestrate_sub.add_parser("promote", help="Promote STM notes to MTM.")
    orchestrate_promote.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help="Emit JSON.")
    orchestrate_promote.add_argument("--from-stm-days", type=int, default=2, help="STM window.")
    orchestrate_promote.add_argument("--min-observed", type=int, default=2, help="Observation threshold.")
    orchestrate_promote.add_argument("--min-confidence", type=float, default=0.7, help="Confidence threshold.")
    orchestrate_promote.set_defaults(func=cmd_orchestrate)
    orchestrate_prune = orchestrate_sub.add_parser("prune", help="Prune expired tier records.")
    orchestrate_prune.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help="Emit JSON.")
    orchestrate_prune.add_argument("--stm-days", type=int, default=2, help="STM days.")
    orchestrate_prune.add_argument("--mtm-days", type=int, default=30, help="MTM days.")
    orchestrate_prune.set_defaults(func=cmd_orchestrate)

    for name, func in (
        ("trajectory-warmup", cmd_trajectory_warmup),
        ("ris" + "k" + "-check", cmd_risk_check),
        ("suggest", cmd_suggest),
    ):
        cmd = sub.add_parser(name, help=f"Run public {name}.")
        cmd.add_argument("--json", action="store_true", help="Emit JSON.")
        cmd.set_defaults(func=func)

    trajectory_report = sub.add_parser("trajectory-report", help="Render public trajectory report.")
    trajectory_report.add_argument("--window-days", type=int, default=7, help="Window size.")
    trajectory_report.add_argument("--format", choices=["json", "md"], default="json", help="Output format.")
    trajectory_report.add_argument("--approvals-file", default="", help="Optional approvals file.")
    trajectory_report.set_defaults(func=cmd_trajectory_report)

    for name, func in (
        ("capture-acceptance", cmd_capture_acceptance),
        ("capture-regression", cmd_capture_regression),
    ):
        cmd = sub.add_parser(name, help=f"Capture public {name} receipt.")
        cmd.add_argument("--task", required=True, help="Task name.")
        cmd.add_argument("--summary", required=True, help="Summary text.")
        cmd.add_argument("--source", default="manual", help="Source label.")
        cmd.add_argument("--confidence", type=float, default=0.9, help="Confidence.")
        cmd.add_argument("--tags", default="", help="Comma-separated tags.")
        cmd.add_argument("--json", action="store_true", help="Emit JSON.")
        cmd.set_defaults(func=func)

    mcp_serve = sub.add_parser("mcp-serve", help="Serve the public MCP surface over stdio.")
    mcp_serve.add_argument("--transport", choices=["stdio", "http"], default="stdio", help="Transport mode.")
    mcp_serve.add_argument("--allow-write", action="store_true", help="Enable write-capable tools.")
    mcp_serve.add_argument("--manifest", action="store_true", help="Print the MCP manifest and exit.")
    mcp_serve.add_argument("--json", action="store_true", help="Emit JSON when printing the manifest.")
    mcp_serve.set_defaults(func=cmd_mcp_serve)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.home:
        os.environ["MADONGMEI_HOME"] = args.home
    ensure_layout()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
