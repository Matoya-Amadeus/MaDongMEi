#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from longmemeval_madongmei_runner import backend_profile_key, canonical_backend_profile, run_benchmark

REPO_ROOT = Path(__file__).resolve().parent.parent
METRICS_DIR = REPO_ROOT / "manifests" / "metrics"
AUDIT_DIR = REPO_ROOT / "manifests" / "audit"
BENCHMARK_DIR = REPO_ROOT / "benchmarks" / "longmemeval"
DEFAULT_POLICY = REPO_ROOT / "config" / "governance" / "longmemeval_policy.json"
_FULL_RESULT_RE = re.compile(r"^longmemeval_(?P<family>.+?)_(?P<granularity>session|turn)_(?P<ts>\d{8}_\d{6})\.jsonl$")

def load_policy(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))

def backend_thresholds(policy: dict, backend: str) -> dict:
    return policy.get("absolute", {}).get(backend, {})

def thresholds_for_profile(policy: dict, backend: str, profile: str) -> dict:
    key = backend_profile_key(backend, profile)
    prof = (policy.get("internal_profiles", {}) or {}).get(key, {})
    if isinstance(prof, dict) and prof:
        return prof
    return backend_thresholds(policy, backend)

def parse_backend_entry(raw: str) -> dict:
    token = str(raw or "").strip()
    if not token:
        raise ValueError("empty backend token")
    if ":" in token:
        b, p = token.split(":", 1)
        backend, profile = canonical_backend_profile(b.strip(), p.strip() or "default")
    else:
        backend, profile = canonical_backend_profile(token, "default")
    return {
        "input": token,
        "backend": backend,
        "profile": profile,
        "backend_key": backend_profile_key(backend, profile),
    }

def read_metric(summary: dict, key: str) -> float:
    return float(summary.get("session_metrics", {}).get(key, 0.0) or 0.0)


def public_rel(path: Path, *, fallback: str = "") -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except Exception:
        return fallback or path.name


def sanitize_summary(summary: dict, *, data_file_label: str) -> dict:
    payload = json.loads(json.dumps(summary, ensure_ascii=False))
    payload["data_file"] = data_file_label
    if payload.get("results_jsonl"):
        payload["results_jsonl"] = public_rel(Path(str(payload["results_jsonl"])), fallback=str(payload["results_jsonl"]))
    return payload


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

def build_rows(summaries: Dict[str, dict], policy: dict) -> List[dict]:
    rows: List[dict] = []
    main = summaries.get("madongmei_semantic_hybrid:default")
    if not isinstance(main, dict):
        return rows
    th = backend_thresholds(policy, "madongmei_overall")
    row = {
        "backend": "madongmei_overall",
        "recall_any@5": read_metric(main, "recall_any@5"),
        "recall_any@10": read_metric(main, "recall_any@10"),
        "ndcg_any@10": read_metric(main, "ndcg_any@10"),
        "thresholds": {
            "recall_any@5": float(th.get("min_recall_any@5", 0.0)),
            "recall_any@10": float(th.get("min_recall_any@10", 0.0)),
            "ndcg_any@10": float(th.get("min_ndcg_any@10", 0.0)),
        },
    }
    row["passed"] = (
        row["recall_any@5"] >= row["thresholds"]["recall_any@5"]
        and row["recall_any@10"] >= row["thresholds"]["recall_any@10"]
        and row["ndcg_any@10"] >= row["thresholds"]["ndcg_any@10"]
    )
    rows.append(row)
    return rows

def write_markdown_report(path: Path, payload: dict) -> None:
    lines = [
        "# LongMemEval Evaluation Report",
        "",
        f"- generated_at: {payload['generated_at']}",
        f"- dataset: {payload['data_file']}",
        f"- granularity: {payload['granularity']}",
        f"- questions: {payload['questions']}",
        "",
        "## Summary",
        "",
        "| backend | Recall@5 | Recall@10 | NDCG@10 | threshold R@5 | threshold R@10 | threshold NDCG@10 | pass |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]

    for row in payload["rows"]:
        lines.append(
            "| {backend} | {r5:.4f} | {r10:.4f} | {n10:.4f} | {tr5:.4f} | {tr10:.4f} | {tn10:.4f} | {passed} |".format(
                backend=row["backend"],
                r5=row["recall_any@5"],
                r10=row["recall_any@10"],
                n10=row["ndcg_any@10"],
                tr5=row["thresholds"]["recall_any@5"],
                tr10=row["thresholds"]["recall_any@10"],
                tn10=row["thresholds"]["ndcg_any@10"],
                passed="PASS" if row["passed"] else "FAIL",
            )
        )

    ref = payload.get("reference", {})
    if ref:
        lines.extend(
            [
                "",
                "## Reference",
                "",
                f"- source: {ref.get('source', 'n/a')}",
                f"- mempalace_claim_recall_any@5: {ref.get('mempalace_claim_recall_any@5', 'n/a')}",
                f"- notes: {ref.get('notes', 'n/a')}",
            ]
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

def longmemeval_full_result_retention_plan(metrics_dir: Path, *, keep_per_family: int = 5) -> dict:
    families: dict[str, list[Path]] = {}
    for path in sorted(metrics_dir.glob("longmemeval_*_*.jsonl")):
        match = _FULL_RESULT_RE.match(path.name)
        if not match:
            continue
        family = f"{match.group('family')}_{match.group('granularity')}"
        families.setdefault(family, []).append(path)

    keep: list[dict] = []
    remove: list[dict] = []
    for family, paths in sorted(families.items()):
        ordered = sorted(paths, key=lambda p: p.name)
        keep_set = set(ordered[-keep_per_family:])
        for path in ordered:
            row = {
                "path": str(path.relative_to(metrics_dir.parent.parent) if metrics_dir.parent.parent in path.parents else path),
                "family": family,
                "size_bytes": path.stat().st_size if path.exists() else 0,
            }
            if path in keep_set:
                keep.append(row)
            else:
                remove.append(row)
    return {
        "keep_per_family": keep_per_family,
        "keep": keep,
        "remove": remove,
        "remove_count": len(remove),
        "remove_bytes": sum(int(row.get("size_bytes", 0)) for row in remove),
    }

def main() -> int:
    ap = argparse.ArgumentParser(description="Run LongMemEval suite for madongmei and produce release-ready report artifacts.")
    ap.add_argument("data_file", type=Path, help="Path to longmemeval_s_cleaned.json")
    ap.add_argument(
        "--backends",
        default="madongmei_semantic_hybrid,madongmei_semantic_hybrid:tfidf_fallback",
        help="comma-separated backend tokens; supports backend or backend:profile",
    )
    ap.add_argument("--granularity", choices=["session", "turn"], default="session")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--skip", type=int, default=0)
    ap.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    ap.add_argument("--record-history", action="store_true", help="append backend metrics to history jsonl")
    ap.add_argument("--record-full-results", action="store_true", help="write full per-question JSONL result artifacts")
    ap.add_argument("--retention-keep-full-results", type=int, default=5, help="number of full JSONL result artifacts to keep per backend/granularity family")
    ap.add_argument("--retention-plan-json", type=Path, default=None, help="write LongMemEval full-result retention plan JSON")
    ap.add_argument("--public-data-label", default="data/longmemeval/longmemeval_s_cleaned.json", help="public artifact label for the dataset path")
    ap.add_argument("--enforce", action="store_true", help="return non-zero when any backend fails policy")
    args = ap.parse_args()

    tokens = [b.strip() for b in args.backends.split(",") if b.strip()]
    if not tokens:
        raise SystemExit("no backends provided")
    entries = [parse_backend_entry(tok) for tok in tokens]

    policy = load_policy(args.policy)
    ts = datetime.now(timezone.utc).astimezone().strftime("%Y%m%d_%H%M%S")
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    BENCHMARK_DIR.mkdir(parents=True, exist_ok=True)

    summaries: Dict[str, dict] = {}
    for entry in entries:
        backend = entry["backend"]
        profile = entry["profile"]
        backend_key = entry["backend_key"]
        key_safe = backend_key.replace(":", "__")
        out_jsonl = METRICS_DIR / f"longmemeval_{key_safe}_{args.granularity}_{ts}.jsonl" if args.record_full_results else None
        summary = run_benchmark(
            data_file=args.data_file,
            backend=backend,
            profile=profile,
            granularity=args.granularity,
            limit=max(0, args.limit),
            skip=max(0, args.skip),
            out_file=out_jsonl,
        )
        if out_jsonl is not None:
            summary["results_jsonl"] = str(out_jsonl)
        summary = sanitize_summary(summary, data_file_label=args.public_data_label)
        summary_path = METRICS_DIR / f"longmemeval_{key_safe}_{args.granularity}_{ts}.summary.json"
        write_json(summary_path, summary)
        latest_path = METRICS_DIR / f"longmemeval_latest_{key_safe}.json"
        write_json(latest_path, summary)
        if backend == "madongmei_semantic_hybrid" and profile == "default":
            legacy_latest = METRICS_DIR / "longmemeval_latest_madongmei_semantic_hybrid.json"
            write_json(legacy_latest, summary)
        summaries[backend_key] = summary

        if args.record_history:
            hist_path = METRICS_DIR / f"longmemeval-history-{key_safe}.jsonl"
            row = {
                "generated_at": summary.get("generated_at", ""),
                "backend": backend,
                "profile": profile,
                "backend_key": backend_key,
                "data_file": args.public_data_label,
                "granularity": args.granularity,
                "questions_evaluated": int(summary.get("questions_evaluated", 0) or 0),
                "recall_any@5": read_metric(summary, "recall_any@5"),
                "recall_any@10": read_metric(summary, "recall_any@10"),
                "ndcg_any@10": read_metric(summary, "ndcg_any@10"),
            }
            with hist_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            if backend == "madongmei_semantic_hybrid" and profile == "default":
                legacy_hist = METRICS_DIR / "longmemeval-history-madongmei_semantic_hybrid.jsonl"
                with legacy_hist.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")

    rows = build_rows(summaries, policy)
    passed = all(row["passed"] for row in rows)

    suite_payload = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(),
        "data_file": args.public_data_label,
        "granularity": args.granularity,
        "questions": int(next(iter(summaries.values())).get("questions_evaluated", 0) if summaries else 0),
        "backends": ["madongmei_overall"],
        "rows": rows,
        "passed": passed,
        "policy_path": public_rel(args.policy, fallback="config/governance/longmemeval_policy.json"),
        "internal_profiles": {
            k: {
                "backend": str(v.get("backend", "")),
                "profile": str(v.get("profile", "default")),
                "recall_any@5": read_metric(v, "recall_any@5"),
                "recall_any@10": read_metric(v, "recall_any@10"),
                "ndcg_any@10": read_metric(v, "ndcg_any@10"),
            }
            for k, v in summaries.items()
        },
        "reference": policy.get("reference", {}),
    }

    suite_path = METRICS_DIR / f"longmemeval_suite_{ts}.json"
    write_json(suite_path, suite_payload)
    latest_suite_path = METRICS_DIR / "longmemeval_latest_suite.json"
    write_json(latest_suite_path, suite_payload)
    official_snapshot_path = BENCHMARK_DIR / "official-suite-summary.json"
    write_json(official_snapshot_path, suite_payload)

    report_path = AUDIT_DIR / f"longmemeval-report-{ts}.md"
    write_markdown_report(report_path, suite_payload)
    latest_report_path = AUDIT_DIR / "longmemeval-report-latest.md"
    write_markdown_report(latest_report_path, suite_payload)

    retention_plan = longmemeval_full_result_retention_plan(METRICS_DIR, keep_per_family=max(1, args.retention_keep_full_results))
    if args.retention_plan_json:
        args.retention_plan_json.parent.mkdir(parents=True, exist_ok=True)
        args.retention_plan_json.write_text(json.dumps(retention_plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("=== LongMemEval Suite (MaDongMei) ===")
    print(f"dataset={args.data_file}")
    print(f"suite_json={suite_path}")
    print(f"suite_latest={latest_suite_path}")
    print(f"report_md={report_path}")
    print(f"full_results_recorded={str(args.record_full_results).lower()}")
    print(f"retention_remove_count={retention_plan['remove_count']}")
    for row in rows:
        print(
            f"{row['backend']}: "
            f"R@5={row['recall_any@5']:.4f} R@10={row['recall_any@10']:.4f} "
            f"NDCG@10={row['ndcg_any@10']:.4f} status={'PASS' if row['passed'] else 'FAIL'}"
        )

    if args.enforce and not passed:
        return 6
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
