from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_memoryctl(*args: str, home: Path, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
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


def run_script(script: str, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    merged["PYTHONPATH"] = f"{ROOT / 'src'}{os.pathsep}{merged.get('PYTHONPATH', '')}".rstrip(os.pathsep)
    if env:
        merged.update(env)
    return subprocess.run(
        [str(ROOT / script), *args],
        capture_output=True,
        text=True,
        env=merged,
        check=False,
    )


class MigrationContract(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory(prefix="madongmei-migration-")
        self.tmp = Path(self.tempdir.name)
        self.home = self.tmp / "home"

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_memoryctl_public_migration_commands_exist_and_emit_json(self) -> None:
        help_result = subprocess.run([str(ROOT / "memoryctl"), "--help"], capture_output=True, text=True, check=False)
        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        for command in [
            "pre-hook",
            "cycle",
            "compact",
            "health",
            "verify-step",
            "eval",
            "regression-gate",
            "personal-capture",
            "personal-search",
            "personal-slo",
            "codex-ref-audit",
            "codex-ref-doctor",
        ]:
            self.assertIn(command, help_result.stdout)

        run_memoryctl("capture", "public install memory", "--title", "install memory", "--tag", "public", home=self.home)
        prehook = run_memoryctl("pre-hook", "--query", "install memory", "--json", home=self.home)
        self.assertEqual(prehook.returncode, 0, prehook.stderr)
        prehook_payload = json.loads(prehook.stdout)
        self.assertEqual(prehook_payload["schema_version"], 1)
        self.assertTrue(prehook_payload["public"])
        self.assertIn("[MADONGMEI MEMORY]", prehook_payload["block"])
        self.assertNotIn(str(self.home), prehook.stdout)

        for args in [
            ("cycle", "install memory", "--json"),
            ("compact", "--json"),
            ("health", "--readonly", "--json"),
            ("verify-step", "all", "--json"),
            ("eval", "--format", "json"),
            ("regression-gate", "--format", "json"),
            ("codex-ref-doctor", "--json"),
        ]:
            result = run_memoryctl(*args, home=self.home)
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertTrue(payload.get("passed", payload.get("ok", True)), result.stdout)

        audit = run_memoryctl("codex-ref-audit", "--repo", "public/example", "--ref", "main", "--json", home=self.home)
        self.assertEqual(audit.returncode, 0, audit.stderr)
        self.assertEqual(json.loads(audit.stdout)["repo"], "public/example")

    def test_personal_public_graph_aliases_are_available(self) -> None:
        capture = run_memoryctl(
            "personal-capture",
            "--title",
            "public graph note",
            "--content",
            "public graph content",
            "--tags",
            "public,graph",
            "--json",
            home=self.home,
        )
        self.assertEqual(capture.returncode, 0, capture.stderr)
        page_id = json.loads(capture.stdout)["page_id"]

        search = run_memoryctl("personal-search", "graph", "--json", home=self.home)
        self.assertEqual(search.returncode, 0, search.stderr)
        self.assertTrue(json.loads(search.stdout))

        doctor = run_memoryctl("personal-doctor", "--json", home=self.home)
        self.assertEqual(doctor.returncode, 0, doctor.stderr)
        self.assertTrue(json.loads(doctor.stdout)["ok"])

        slo = run_memoryctl("personal-slo", "--json", home=self.home)
        self.assertEqual(slo.returncode, 0, slo.stderr)
        self.assertGreaterEqual(json.loads(slo.stdout)["page_count"], 1)

        snapshot = run_memoryctl("personal-snapshot", "--json", home=self.home)
        self.assertEqual(snapshot.returncode, 0, snapshot.stderr)
        self.assertTrue(Path(json.loads(snapshot.stdout)["snapshot"]).exists())
        self.assertTrue(page_id)

    def test_context_install_injects_codex_model_instructions(self) -> None:
        env = {
            "CODEX_HOME": str(self.tmp / "codex-home"),
            "MADONGMEI_HOME": str(self.home),
            "PYTHONPATH": f"{ROOT / 'src'}",
        }
        install = run_script("scripts/install_context_bridge.sh", "--home", str(self.home), "--json", env=env)
        self.assertEqual(install.returncode, 0, install.stderr)
        payload = json.loads(install.stdout)
        config_toml = Path(payload["codex_config_toml"])
        model_file = Path(payload["model_instructions_file"])
        self.assertTrue(config_toml.exists())
        self.assertTrue(model_file.exists())
        self.assertIn(str(model_file), config_toml.read_text(encoding="utf-8"))
        model_text = model_file.read_text(encoding="utf-8")
        self.assertIn("memoryctl pre-hook", model_text)
        self.assertIn("MADONGMEI_HOME", model_text)
        self.assertNotIn("ai-" + "madongmei-memory", model_text.lower())
        self.assertNotIn("<private", model_text.lower())

        prehook = run_memoryctl("pre-hook", "--query", "public install memory", "--json", home=self.home)
        self.assertEqual(prehook.returncode, 0, prehook.stderr)
        self.assertIn("[MADONGMEI MEMORY]", json.loads(prehook.stdout)["block"])

    def test_eval_and_regression_gate_use_real_longmemeval_snapshot(self) -> None:
        eval_result = run_memoryctl("eval", "--format", "json", home=self.home)
        self.assertEqual(eval_result.returncode, 0, eval_result.stderr)
        eval_payload = json.loads(eval_result.stdout)
        self.assertIn("longmemeval", eval_payload["metrics"])
        self.assertAlmostEqual(float(eval_payload["metrics"]["longmemeval"]["recall_any@5"]), 1.0, places=6)
        self.assertAlmostEqual(float(eval_payload["metrics"]["longmemeval"]["ndcg_any@10"]), 1.0, places=6)

        regression_result = run_memoryctl("regression-gate", "--format", "json", home=self.home)
        self.assertEqual(regression_result.returncode, 0, regression_result.stderr)
        regression_payload = json.loads(regression_result.stdout)
        self.assertIn("longmemeval", regression_payload["metrics"])
        self.assertTrue(regression_payload["passed"], regression_payload)
        self.assertAlmostEqual(float(regression_payload["metrics"]["longmemeval"]["madongmei_overall"]["ndcg_any@10"]), 1.0, places=6)

    def test_privacy_projection_governance_and_llmwiki_gates(self) -> None:
        good = self.tmp / "good"
        good.mkdir()
        (good / "ok.md").write_text("public template only\n", encoding="utf-8")
        privacy_good = run_script("scripts/privacy_audit.sh", "--target", str(good), "--json")
        self.assertEqual(privacy_good.returncode, 0, privacy_good.stderr)
        self.assertTrue(json.loads(privacy_good.stdout)["passed"])

        bad = self.tmp / "bad"
        bad.mkdir()
        private_path = "/" + "Users" + "/example/private-note"
        fake_token = "sk" + "-" + "A" * 24
        (bad / "bad.txt").write_text(f"{private_path}\n{fake_token}\n", encoding="utf-8")
        privacy_bad = run_script("scripts/privacy_audit.sh", "--target", str(bad), "--json")
        self.assertNotEqual(privacy_bad.returncode, 0)
        self.assertFalse(json.loads(privacy_bad.stdout)["passed"])

        for script, args in [
            ("scripts/export_public_projection.py", ("--check", "--json")),
            ("scripts/config_schema_gate.py", ("--json",)),
            ("scripts/llmwiki_route_map.py", ("--check", "--json")),
            ("scripts/llmwiki_source_ref_gate.py", ("--json",)),
            ("scripts/llmwiki_citation_gate.py", ("--json",)),
            ("scripts/llmwiki_conflict_report.py", ("--json",)),
            ("scripts/madongmei_doctor.py", ("--json",)),
        ]:
            result = run_script(script, *args)
            self.assertEqual(result.returncode, 0, f"{script}: {result.stderr}\n{result.stdout}")
            payload = json.loads(result.stdout)
            self.assertTrue(payload.get("passed", payload.get("ok", True)), payload)

        doctor_payload = json.loads(run_script("scripts/madongmei_doctor.py", "--json").stdout)
        self.assertEqual(doctor_payload["schema_version"], 1)
        self.assertIn("checks", doctor_payload)
        self.assertIn("privacy", doctor_payload["checks"])
        self.assertIn("llmwiki_route_map", doctor_payload["checks"])


if __name__ == "__main__":
    unittest.main()
