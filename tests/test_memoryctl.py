from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_cmd(*args: str, home: Path, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["CODEX_HOME"] = str(home.parent / ".codex")
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


class MemoryCtlE2E(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory(prefix="madongmei-tests-")
        self.home = Path(self.tempdir.name) / "home"

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_capture_search_recall_and_doctor(self) -> None:
        capture = run_cmd("capture", "--title", "install note", "bootstrap completed", "--tag", "install", "--json", home=self.home)
        self.assertEqual(capture.returncode, 0, capture.stderr)
        payload = json.loads(capture.stdout)
        self.assertEqual(payload["title"], "install note")
        self.assertIn("install", payload["tags"])

        search = run_cmd("search", "bootstrap", "--json", home=self.home)
        self.assertEqual(search.returncode, 0, search.stderr)
        rows = json.loads(search.stdout)
        self.assertTrue(rows)
        self.assertEqual(rows[0]["title"], "install note")

        recall = run_cmd("recall", "bootstrap", home=self.home)
        self.assertEqual(recall.returncode, 0, recall.stderr)
        self.assertIn("install note", recall.stdout)

        doctor = run_cmd("doctor", "--json", home=self.home)
        self.assertEqual(doctor.returncode, 0, doctor.stderr)
        report = json.loads(doctor.stdout)
        self.assertTrue(report["db_exists"])
        self.assertGreaterEqual(report["record_count"], 1)
        self.assertIn("wiki_dir", report)
        self.assertIn("skill_dir", report)

    def test_review_export_and_import(self) -> None:
        run_cmd("capture", "--title", "weekly item", "weekly review content", "--tag", "weekly", home=self.home)
        run_cmd("capture", "--title", "second item", "another note", "--tag", "public", home=self.home)

        review = run_cmd("review", "--json", home=self.home)
        self.assertEqual(review.returncode, 0, review.stderr)
        review_payload = json.loads(review.stdout)
        self.assertEqual(review_payload["count"], 2)

        weekly = run_cmd("weekly-review", "--json", home=self.home)
        self.assertEqual(weekly.returncode, 0, weekly.stderr)
        weekly_payload = json.loads(weekly.stdout)
        self.assertGreaterEqual(weekly_payload["count"], 2)

        export_file = Path(self.tempdir.name) / "export.jsonl"
        export = run_cmd("export-jsonl", "--output", str(export_file), home=self.home)
        self.assertEqual(export.returncode, 0, export.stderr)
        self.assertTrue(export_file.exists())

        import_home = Path(self.tempdir.name) / "import-home"
        import_result = run_cmd("import-jsonl", str(export_file), "--replace", home=import_home)
        self.assertEqual(import_result.returncode, 0, import_result.stderr)
        self.assertIn("Imported 2 record(s).", import_result.stdout)

        search = run_cmd("search", "weekly", "--json", home=import_home)
        self.assertEqual(search.returncode, 0, search.stderr)
        rows = json.loads(search.stdout)
        self.assertTrue(rows)

    def test_autopilot_routes_and_persists_public_artifacts(self) -> None:
        wiki_home = Path(self.tempdir.name) / "wiki-home"
        skill_home = Path(self.tempdir.name) / "skill-home"

        wiki_result = run_cmd(
            "autopilot",
            "--title",
            "wiki note",
            "The canonical public rule is to keep installation decisions in the wiki.",
            "--tag",
            "public",
            "--json",
            home=wiki_home,
        )
        self.assertEqual(wiki_result.returncode, 0, wiki_result.stderr)
        wiki_payload = json.loads(wiki_result.stdout)
        self.assertEqual(wiki_payload["plan"]["wiki_action"], "promote")
        self.assertIn(wiki_payload["record"]["bucket"], {"wiki", "decision", "faq"})
        self.assertTrue((wiki_home / "knowledge" / "wiki" / wiki_payload["record"]["bucket"]).exists())

        skill_result = run_cmd(
            "autopilot",
            "--title",
            "skill note",
            "Please run ./bootstrap.sh and validate the clean install workflow.",
            "--tag",
            "public",
            "--json",
            home=skill_home,
        )
        self.assertEqual(skill_result.returncode, 0, skill_result.stderr)
        skill_payload = json.loads(skill_result.stdout)
        self.assertEqual(skill_payload["record"]["bucket"], "skill")
        self.assertTrue((skill_home / "skills" / "public-autopilot" / "published").exists())
        self.assertFalse("<private-path>" in skill_payload["query"])
        self.assertNotIn(str(skill_home), skill_result.stdout)

    def test_autopilot_low_confidence_stays_in_memory(self) -> None:
        memory_result = run_cmd(
            "autopilot",
            "--dry-run",
            "Quick reminder about lunch.",
            "--json",
            home=Path(self.tempdir.name) / "memory-home",
        )
        self.assertEqual(memory_result.returncode, 0, memory_result.stderr)
        memory_payload = json.loads(memory_result.stdout)
        self.assertEqual(memory_payload["plan"]["memory_route"], "memory")
        self.assertEqual(memory_payload["plan"]["wiki_action"], "skip")
        self.assertLess(memory_payload["plan"]["confidence"], 0.55)

    def test_framework_context_workspace_graph_and_mcp_commands(self) -> None:
        bridge_home = Path(self.tempdir.name) / "bridge-home"
        extra_workspace = Path(self.tempdir.name) / "extra-workspace"

        context = run_cmd(
            "context",
            "template",
            "--query",
            "Keep the bridge install chain public.",
            "--workspace-id",
            "bridge-home",
            "--json",
            home=bridge_home,
        )
        self.assertEqual(context.returncode, 0, context.stderr)
        context_payload = json.loads(context.stdout)
        self.assertIn("Keep the bridge install chain public.", context_payload["template"])

        install = run_cmd("context", "install", "--json", home=bridge_home)
        self.assertEqual(install.returncode, 0, install.stderr)
        install_payload = json.loads(install.stdout)
        self.assertTrue(Path(install_payload["config_path"]).exists())
        self.assertIn("bridge_root", install_payload)
        self.assertIn("graph_snapshot_dir", install_payload)

        templates = run_cmd("context", "templates", "--json", home=bridge_home)
        self.assertEqual(templates.returncode, 0, templates.stderr)
        templates_payload = json.loads(templates.stdout)
        self.assertIn("request_context", templates_payload)
        self.assertIn("workspace_registry", templates_payload)

        workspace_status = run_cmd("workspace", "status", "--json", home=bridge_home)
        self.assertEqual(workspace_status.returncode, 0, workspace_status.stderr)
        workspace_status_payload = json.loads(workspace_status.stdout)
        self.assertIn("bridge_root", workspace_status_payload)
        self.assertIn("workspace_registry_path", workspace_status_payload)
        self.assertIn("graph_snapshot_dir", workspace_status_payload)

        register = run_cmd(
            "workspace",
            "register",
            "--root",
            str(extra_workspace),
            "--label",
            "extra",
            "--json",
            home=bridge_home,
        )
        self.assertEqual(register.returncode, 0, register.stderr)
        register_payload = json.loads(register.stdout)
        self.assertTrue(any(row["label"] == "extra" for row in register_payload))

        remove = run_cmd("workspace", "remove", "--root", str(extra_workspace), "--json", home=bridge_home)
        self.assertEqual(remove.returncode, 0, remove.stderr)
        remove_payload = json.loads(remove.stdout)
        self.assertFalse(any(row["label"] == "extra" for row in remove_payload))

        graph_capture = run_cmd(
            "graph",
            "capture",
            "--title",
            "graph note",
            "--content",
            "Framework only",
            "--tag",
            "public",
            "--json",
            home=bridge_home,
        )
        self.assertEqual(graph_capture.returncode, 0, graph_capture.stderr)
        graph_capture_payload = json.loads(graph_capture.stdout)
        self.assertTrue(graph_capture_payload["ok"])
        page_id = graph_capture_payload["page_id"]

        graph_search = run_cmd("graph", "search", "Framework", "--json", home=bridge_home)
        self.assertEqual(graph_search.returncode, 0, graph_search.stderr)
        graph_search_payload = json.loads(graph_search.stdout)
        self.assertTrue(graph_search_payload)
        self.assertEqual(graph_search_payload[0]["title"], "graph note")

        graph_snapshot = run_cmd("graph", "snapshot", "--json", home=bridge_home)
        self.assertEqual(graph_snapshot.returncode, 0, graph_snapshot.stderr)
        graph_snapshot_payload = json.loads(graph_snapshot.stdout)
        self.assertTrue(Path(graph_snapshot_payload["snapshot"]).exists())

        graph_restore = run_cmd("graph", "restore", "--snapshot", graph_snapshot_payload["snapshot"], "--json", home=bridge_home)
        self.assertEqual(graph_restore.returncode, 0, graph_restore.stderr)
        graph_restore_payload = json.loads(graph_restore.stdout)
        self.assertTrue(graph_restore_payload["ok"])

        graph_doctor = run_cmd("graph", "doctor", "--json", home=bridge_home)
        self.assertEqual(graph_doctor.returncode, 0, graph_doctor.stderr)
        graph_doctor_payload = json.loads(graph_doctor.stdout)
        self.assertTrue(graph_doctor_payload["ok"])
        self.assertIn("snapshot_root", graph_doctor_payload)

        mcp_manifest = run_cmd("mcp-serve", "--manifest", "--json", home=bridge_home)
        self.assertEqual(mcp_manifest.returncode, 0, mcp_manifest.stderr)
        mcp_manifest_payload = json.loads(mcp_manifest.stdout)
        tool_names = {tool["name"] for tool in mcp_manifest_payload["tools"]}
        self.assertIn("context_template", tool_names)
        self.assertIn("graph_snapshot", tool_names)
        self.assertIn("workspace_remove", tool_names)

        mcp_ping = run_cmd("mcp-serve", home=bridge_home, input_text='{"jsonrpc":"2.0","id":1,"method":"ping"}\n')
        self.assertEqual(mcp_ping.returncode, 0, mcp_ping.stderr)
        ping_payload = [json.loads(line) for line in mcp_ping.stdout.splitlines() if line.strip()]
        self.assertTrue(any(item.get("result", {}).get("ok") for item in ping_payload))


if __name__ == "__main__":
    unittest.main()
