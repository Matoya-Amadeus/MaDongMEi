from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_memoryctl(home: Path, *args: str, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["CODEX_HOME"] = str(home.parent / "codex-home")
    env["MADONGMEI_HOME"] = str(home)
    env["MADONGMEI_WIKI_DIR"] = str(home / "knowledge" / "wiki")
    env["MADONGMEI_SKILL_DIR"] = str(home / "skills" / "public-autopilot")
    env["PYTHONPATH"] = f"{ROOT / 'src'}{os.pathsep}{env.get('PYTHONPATH', '')}".rstrip(os.pathsep)
    return subprocess.run(
        [str(ROOT / "memoryctl"), *args],
        input=input_text,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


class DeepFunctionalEquivalence(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory(prefix="madongmei-deep-")
        self.home = Path(self.tempdir.name) / "home"

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def json_cmd(self, *args: str, input_text: str | None = None) -> dict:
        result = run_memoryctl(self.home, *args, input_text=input_text)
        self.assertEqual(result.returncode, 0, f"cmd={args} stderr={result.stderr} stdout={result.stdout}")
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as exc:  # pragma: no cover - assertion detail
            raise AssertionError(f"cmd={args} did not emit JSON: {result.stdout}") from exc

    def test_reindex_ingest_graph_extract_build_query_are_real_runtime_artifacts(self) -> None:
        ingest = self.json_cmd(
            "ingest",
            "--bucket",
            "facts",
            "--topic",
            "public-install",
            "--claim",
            "MaDongMei installation uses bootstrap and context bridge.",
            "--source-family",
            "open_source",
            "--authority-level",
            "primary",
            "--source-ref",
            "knowledge/installation.md",
            "--collected-at",
            "2026-05-05T00:00:00Z",
            "--freshness-days",
            "30",
            "--lineage",
            "docs:installation",
            "--idempotency-key",
            "install-fact-1",
            "--json",
        )
        self.assertTrue(ingest["passed"])
        self.assertFalse(ingest["duplicate"])
        ingest_path = Path(ingest["file"])
        self.assertTrue(ingest_path.exists())
        self.assertTrue(str(ingest_path).startswith(str(self.home)))
        row = json.loads(ingest_path.read_text(encoding="utf-8").splitlines()[0])
        self.assertEqual(row["id"], ingest["id"])
        self.assertEqual(row["topic"], "public-install")
        self.assertEqual(row["source_ref"], "knowledge/installation.md")

        duplicate = self.json_cmd(
            "ingest",
            "--bucket",
            "facts",
            "--topic",
            "public-install",
            "--claim",
            "MaDongMei installation uses bootstrap and context bridge.",
            "--source-family",
            "open_source",
            "--authority-level",
            "primary",
            "--source-ref",
            "knowledge/installation.md",
            "--collected-at",
            "2026-05-05T00:00:00Z",
            "--freshness-days",
            "30",
            "--lineage",
            "docs:installation",
            "--idempotency-key",
            "install-fact-1",
            "--json",
        )
        self.assertTrue(duplicate["duplicate"])
        self.assertEqual(duplicate["id"], ingest["id"])

        reindex = self.json_cmd("reindex", "--json")
        self.assertGreaterEqual(reindex["n_docs"], 1)
        self.assertTrue(Path(reindex["index_path"]).exists())
        self.assertTrue(Path(reindex["meta_path"]).exists())
        self.assertIn("corpus_hash", reindex)

        extract = self.json_cmd("graph-extract", "--json")
        self.assertGreaterEqual(extract["entities"], 1)
        self.assertGreaterEqual(extract["relations"], 1)
        self.assertTrue(Path(extract["graph_source_dir"]).exists())

        build = self.json_cmd("graph-build", "--json")
        self.assertGreaterEqual(build["entity_count"], 1)
        self.assertGreaterEqual(build["relation_count"], 1)
        self.assertTrue(Path(build["node_index_path"]).exists())
        self.assertTrue(Path(build["edge_index_path"]).exists())

        query = self.json_cmd("graph-query", "public-install", "--hops", "1", "--topk", "5", "--json")
        self.assertGreaterEqual(query["row_count"], 1)
        top = query["rows"][0]
        self.assertIn(top["type"], {"document", "topic", "source", "keyword"})
        self.assertGreaterEqual(top["score"], 1)

    def test_stm_mtm_orchestration_trajectory_and_receipts_persist_state(self) -> None:
        first = self.json_cmd(
            "capture-stm",
            "--text",
            "Deep public STM note",
            "--source",
            "test",
            "--confidence",
            "0.82",
            "--tags",
            "public,stm",
            "--idempotency-key",
            "stm-1",
            "--json",
        )
        self.assertEqual(first["tier"], "stm")
        self.assertTrue(first["added"])
        second = self.json_cmd(
            "capture-stm",
            "--text",
            "Deep public STM note",
            "--source",
            "test",
            "--confidence",
            "0.88",
            "--tags",
            "public,stm",
            "--json",
        )
        self.assertFalse(second["added"])
        self.assertEqual(second["observed_count"], 2)

        promoted = self.json_cmd("promote-mtm", "--min-observed", "2", "--min-confidence", "0.8", "--json")
        self.assertEqual(promoted["promoted"], 1)
        mtm_path = Path(promoted["mtm_file"])
        self.assertTrue(mtm_path.exists())
        self.assertIn("Deep public STM note", mtm_path.read_text(encoding="utf-8"))

        orch = self.json_cmd("orchestrate", "--json", "promote", "--min-observed", "2", "--min-confidence", "0.8")
        self.assertEqual(orch["action"], "promote")
        self.assertIn("result", orch)

        trajectory = self.json_cmd("trajectory-warmup", "--json")
        self.assertGreaterEqual(trajectory["seeded"], 4)
        trace_file = Path(trajectory["trace_file"])
        self.assertTrue(trace_file.exists())
        self.assertGreaterEqual(len(trace_file.read_text(encoding="utf-8").splitlines()), 4)

        risk = self.json_cmd("risk-check", "--json")
        self.assertIn(risk["risk_level"], {"low", "medium", "high", "unknown"})
        self.assertGreaterEqual(risk["total_events"], 1)

        suggest = self.json_cmd("suggest", "--json")
        self.assertIn("items", suggest)
        self.assertTrue(suggest["items"])

        report = self.json_cmd("trajectory-report", "--format", "json")
        self.assertTrue(Path(report["md_report"]).exists())
        self.assertGreaterEqual(report["trajectory_events_in_window"], 1)

        acceptance = self.json_cmd("capture-acceptance", "--task", "deep", "--summary", "acceptance passed", "--json")
        regression = self.json_cmd("capture-regression", "--task", "deep", "--summary", "regression passed", "--json")
        self.assertEqual(acceptance["tier"], "stm")
        self.assertIn("acceptance", acceptance["tags"])
        self.assertIn("regression", regression["tags"])

    def test_eval_phase_switch_and_mcp_session_exercise_real_paths(self) -> None:
        eval_ab = self.json_cmd("eval-ab", "--format", "json")
        self.assertIn("baseline", eval_ab)
        self.assertIn("candidate", eval_ab)
        self.assertIn("delta", eval_ab)

        dashboard = self.json_cmd("eval-dashboard", "--format", "json")
        self.assertIn("metrics", dashboard)
        self.assertIn("eval_ab", dashboard)

        baseline = self.json_cmd("baseline-snapshot", "--json")
        self.assertTrue(Path(baseline["snapshot_file"]).exists())

        phase4 = self.json_cmd("phase4-acceptance", "--json")
        self.assertTrue(phase4["passed"])
        self.assertIn("mcp_readonly_blocks_write", phase4["checks"])

        phase = self.json_cmd("phase-gate", "--skip-switch-gate", "--json")
        self.assertTrue(phase["passed"])
        self.assertIn("phase4_acceptance", phase["steps"])

        switch = self.json_cmd("switch-gate", "--json")
        self.assertIn(switch["decision"], {"pass", "fail"})
        self.assertIn("checks", switch)

        mcp_input = "\n".join([
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}),
            json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}),
            json.dumps({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "memory_capture", "arguments": {"title": "deny", "text": "blocked"}}}),
            json.dumps({"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "memory_search", "arguments": {"query": "deny"}}}),
        ]) + "\n"
        readonly = run_memoryctl(self.home, "mcp-serve", input_text=mcp_input)
        self.assertEqual(readonly.returncode, 0, readonly.stderr)
        responses = [json.loads(line) for line in readonly.stdout.splitlines() if line.strip()]
        by_id = {row.get("id"): row for row in responses}
        self.assertEqual(by_id[1]["result"]["serverInfo"]["name"], "madongmei-mcp")
        self.assertTrue(any(tool["name"] == "memory_capture" for tool in by_id[2]["result"]["tools"]))
        self.assertEqual(by_id[3]["error"]["code"], 403)
        self.assertEqual(by_id[4]["result"]["rows"], [])

        write_input = "\n".join([
            json.dumps({"jsonrpc": "2.0", "id": 10, "method": "initialize", "params": {}}),
            json.dumps({"jsonrpc": "2.0", "id": 11, "method": "tools/call", "params": {"name": "memory_capture", "arguments": {"title": "mcp deep", "text": "mcp write works", "tags": ["mcp"]}}}),
            json.dumps({"jsonrpc": "2.0", "id": 12, "method": "tools/call", "params": {"name": "memory_search", "arguments": {"query": "mcp write"}}}),
        ]) + "\n"
        writable = run_memoryctl(self.home, "mcp-serve", "--allow-write", input_text=write_input)
        self.assertEqual(writable.returncode, 0, writable.stderr)
        write_responses = [json.loads(line) for line in writable.stdout.splitlines() if line.strip()]
        writable_by_id = {row.get("id"): row for row in write_responses}
        self.assertEqual(writable_by_id[11]["result"]["record"]["title"], "mcp deep")
        self.assertTrue(writable_by_id[12]["result"]["rows"])


if __name__ == "__main__":
    unittest.main()
