from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from madongmei.governance import code_scorecard, doctor_report, push_readiness_report, release_strict_report  # noqa: E402


class MaDongMeiCodeScorecardTest(unittest.TestCase):
    def test_scorecard_is_public_readonly_and_weighted_to_100(self) -> None:
        payload = code_scorecard()
        self.assertEqual(payload["schema_version"], 1)
        self.assertTrue(payload["passed"], payload)
        self.assertEqual(payload["max_score"], 100)
        self.assertGreaterEqual(payload["score"], 90)
        self.assertEqual(sum(item["weight"] for item in payload["checks"].values()), 100)
        for key in ("installability", "privacy", "projection", "cli_contract", "governance", "docs", "storage", "benchmark"):
            self.assertIn(key, payload["checks"])
            self.assertIn("code", payload["checks"][key])
            self.assertIn("category", payload["checks"][key])

    def test_scorecard_script_emits_json(self) -> None:
        env = os.environ.copy()
        env["PYTHONPATH"] = f"{ROOT / 'src'}{os.pathsep}{env.get('PYTHONPATH', '')}".rstrip(os.pathsep)
        result = subprocess.run(
            [str(ROOT / "scripts" / "madongmei_code_scorecard.py"), "--json", "--no-record"],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["passed"], payload)
        self.assertEqual(payload["score"], code_scorecard()["score"])

    def test_reference_style_scorecard_matches_internal_parity_shape(self) -> None:
        payload = code_scorecard(style="reference_style")
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["style"], "reference_style")
        self.assertGreaterEqual(payload["score"], 98)
        self.assertEqual(payload["grade"], "A")
        self.assertTrue(payload["passed"], payload)
        self.assertFalse(payload["p0_blocked"], payload)
        self.assertEqual(payload["p0_violations"], [])
        self.assertEqual(len(payload["dimensions"]), 10)
        self.assertEqual([item["weight"] for item in payload["dimensions"]], [20, 15, 15, 10, 10, 10, 8, 5, 5, 2])

    def test_reference_style_scorecard_script_emits_reference_json(self) -> None:
        env = os.environ.copy()
        env["PYTHONPATH"] = f"{ROOT / 'src'}{os.pathsep}{env.get('PYTHONPATH', '')}".rstrip(os.pathsep)
        result = subprocess.run(
            [str(ROOT / "scripts" / "madongmei_code_scorecard.py"), "--json", "--no-record", "--reference-style"],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["style"], "reference_style")
        self.assertEqual(payload["grade"], "A")
        self.assertFalse(payload["p0_blocked"], payload)

    def test_doctor_push_and_release_include_scorecard_and_storage(self) -> None:
        doctor = doctor_report()
        self.assertTrue(doctor["passed"], doctor)
        self.assertIn("scorecard", doctor["checks"])
        self.assertIn("storage_facts", doctor)
        for name, check in doctor["checks"].items():
            if isinstance(check, dict):
                self.assertIn("code", check, name)
                self.assertIn("category", check, name)

        push = push_readiness_report(task_type="code", strict=True)
        self.assertIn("scorecard", push["checks"])
        self.assertIn("storage", push["checks"])
        self.assertTrue(push["passed"], push)

        release = release_strict_report()
        self.assertIn("scorecard", release["checks"])
        self.assertTrue(release["passed"], release)


if __name__ == "__main__":
    unittest.main()
