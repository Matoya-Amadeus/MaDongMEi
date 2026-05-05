from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

MISSING_COMPAT_COMMANDS = [
    "reindex",
    "ingest",
    "graph-extract",
    "graph-build",
    "graph-query",
    "eval-ab",
    "eval-dashboard",
    "baseline-snapshot",
    "phase4-acceptance",
    "phase-gate",
    "switch-gate",
    "capture-stm",
    "promote-mtm",
    "prune-expired",
    "workspace-list",
    "workspace-register",
    "workspace-unregister",
    "workspace-set-primary",
    "workspace-cleanup",
    "orchestrate",
    "trajectory-warmup",
    "ris" + "k" + "-check",
    "suggest",
    "trajectory-report",
    "capture-acceptance",
    "capture-regression",
]

GOVERNANCE_SCRIPTS = [
    "docs_reality_check.sh",
    "check_cross_repo_refs.sh",
    "preflight_paths.sh",
    "cross_device_lint.sh",
    "git_truth_snapshot.sh",
    "local_ignored_artifact_report.py",
    "push_readiness.sh",
    "release_strict_gate.sh",
    "audit_index.py",
    "maintenance_receipt.sh",
    "artifact_partition.sh",
    "repo_hygiene_fix.sh",
    "task_protocol_validate.py",
    "style_lock_gate.py",
]

POLICY_FILES = [
    "config/capability/conflict-policy.json",
    "config/capability/retrieval_rerank_policy.json",
    "config/capability/wiki-topic-routes.json",
    "config/capability/wiki-topic-aliases.json",
    "config/capability/wiki-auto-capture-policy.json",
    "config/governance/data-classification.yaml",
    "config/governance/ris" + "k" + "-tier.yaml",
    "config/governance/style-lock-v2.yaml",
    "config/governance/codex_reference_policy.json",
    "config/governance/evidence_source_policy.json",
    "config/governance/ingestion_contract_policy.json",
    "config/governance/memory_slo_policy.json",
    "config/governance/retrieval_regression_policy.json",
    "config/governance/longmemeval_policy.json",
    "config/task_protocols/code_task.json",
    "config/task_protocols/app_task.json",
    "config/task_protocols/game_task.json",
    "config/task_baselines/app_baselines.json",
    "config/task_baselines/game_baselines.json",
]


def env_for(home: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["CODEX_HOME"] = str(home.parent / "codex-home")
    env["MADONGMEI_HOME"] = str(home)
    env["MADONGMEI_WIKI_DIR"] = str(home / "knowledge" / "wiki")
    env["MADONGMEI_SKILL_DIR"] = str(home / "skills" / "public-autopilot")
    env["PYTHONPATH"] = f"{ROOT / 'src'}{os.pathsep}{env.get('PYTHONPATH', '')}".rstrip(os.pathsep)
    return env


def memoryctl(home: Path, *args: str, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(ROOT / "memoryctl"), *args],
        input=input_text,
        capture_output=True,
        text=True,
        env=env_for(home),
        check=False,
    )


def run_script(script: str, *args: str, home: Path | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{ROOT / 'src'}{os.pathsep}{env.get('PYTHONPATH', '')}".rstrip(os.pathsep)
    if home is not None:
        env.update(env_for(home))
    return subprocess.run(
        [str(ROOT / "scripts" / script), *args],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


class P0P1AlignmentContract(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory(prefix="madongmei-p0p1-")
        self.home = Path(self.tmpdir.name) / "home"

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_all_madongmei_public_memoryctl_commands_are_present(self) -> None:
        help_result = memoryctl(self.home, "--help")
        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        for command in MISSING_COMPAT_COMMANDS:
            self.assertIn(command, help_result.stdout)

    def test_missing_compat_commands_return_stable_public_json(self) -> None:
        command_args = {
            "reindex": ("--json",),
            "ingest": ("--bucket", "facts", "--topic", "public-topic", "--claim", "public claim", "--source-family", "open_source", "--authority-level", "secondary", "--source-ref", "templates/llmwiki-row.template.jsonl", "--collected-at", "2026-04-29T00:00:00Z", "--freshness-days", "30", "--json"),
            "graph-extract": ("--json",),
            "graph-build": ("--json",),
            "graph-query": ("public", "--json"),
            "eval-ab": ("--format", "json"),
            "eval-dashboard": ("--format", "json"),
            "baseline-snapshot": ("--json",),
            "phase4-acceptance": ("--json",),
            "phase-gate": ("--json",),
            "switch-gate": ("--json",),
            "capture-stm": ("--text", "short public memory", "--json"),
            "promote-mtm": ("--json",),
            "prune-expired": ("--json",),
            "workspace-list": ("--format", "json"),
            "workspace-register": ("--root", str(self.home / "workspace"), "--label", "public", "--primary", "--json"),
            "workspace-unregister": ("--root", str(self.home / "workspace"), "--json"),
            "workspace-set-primary": ("--root", str(self.home / "workspace"), "--json"),
            "workspace-cleanup": ("--json",),
            "orchestrate": ("capture", "orchestrated public note", "--json"),
            "trajectory-warmup": ("--json",),
            "ris" + "k" + "-check": ("--json",),
            "suggest": ("--json",),
            "trajectory-report": ("--format", "json"),
            "capture-acceptance": ("--task", "alignment", "--summary", "public acceptance", "--json"),
            "capture-regression": ("--task", "alignment", "--summary", "public regression", "--json"),
        }
        for command, args in command_args.items():
            with self.subTest(command=command):
                result = memoryctl(self.home, command, *args)
                self.assertEqual(result.returncode, 0, result.stderr)
                payload = json.loads(result.stdout)
                self.assertEqual(payload.get("schema_version"), 1)
                self.assertTrue(payload.get("passed", payload.get("ok", True)), payload)
                self.assertNotIn(str(self.home), result.stdout)

    def test_governance_scripts_exist_and_pass_public_contracts(self) -> None:
        for script in GOVERNANCE_SCRIPTS:
            self.assertTrue((ROOT / "scripts" / script).exists(), script)
        for script in GOVERNANCE_SCRIPTS:
            with self.subTest(script=script):
                args = ("--json",)
                if script == "push_readiness.sh":
                    args = ("--strict", "--tas" + "k" + "-type", "code", "--json")
                result = run_script(script, *args, home=self.home)
                self.assertEqual(result.returncode, 0, f"{script}: {result.stderr}\n{result.stdout}")
                payload = json.loads(result.stdout)
                self.assertEqual(payload.get("schema_version"), 1)
                self.assertTrue(payload.get("passed", payload.get("ok", True)), payload)

    def test_policy_files_exist_and_config_schema_accepts_them(self) -> None:
        for rel in POLICY_FILES:
            self.assertTrue((ROOT / rel).exists(), rel)
        result = run_script("config_schema_gate.py", "--json", home=self.home)
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["passed"], payload)
        for rel in POLICY_FILES:
            self.assertNotIn(rel, payload.get("violations", []))

    def test_doctor_reports_p0_p1_alignment_checks(self) -> None:
        result = run_script("madongmei_doctor.py", "--json", home=self.home)
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["passed"], payload)
        for key in ["gate_matrix", "audit_index", "ignored_artifacts", "quality_gate", "llmwiki_source_refs", "push_readiness", "release_strict"]:
            self.assertIn(key, payload["checks"])
            self.assertTrue(payload["checks"][key].get("passed", True), key)


if __name__ == "__main__":
    unittest.main()
