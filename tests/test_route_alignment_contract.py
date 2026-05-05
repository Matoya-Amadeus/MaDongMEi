from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from madongmei.governance import code_scorecard  # noqa: E402


class RouteAlignmentReferenceStyleTest(unittest.TestCase):
    def test_public_route_suite_covers_reference_style_alignment_cases(self) -> None:
        env = os.environ.copy()
        env["PYTHONPATH"] = f"{ROOT / 'src'}{os.pathsep}{env.get('PYTHONPATH', '')}".rstrip(os.pathsep)
        result = subprocess.run(
            [str(ROOT / "scripts" / "request_route_real_prompt_suite.py"), "--json"],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["passed"], payload)
        self.assertEqual(payload["case_count"], 16)
        ids = {case["id"] for case in payload["cases"]}
        self.assertEqual(
            ids,
            {
                "docs_openai",
                "security_threat_model",
                "security_best_practices",
                "meeting_public",
                "skill_governance",
                "push_recovery_cn",
                "push_recovery_cn_variant",
                "readme_capture",
                "general_chat",
                "ts_refactor",
                "ts_plan",
                "docs_plus_wiki",
                "capability_route_registry_positive",
                "capability_route_registry_negative",
                "capability_route_registry_mixed",
                "capability_route_registry_zh_natural",
            },
        )
        by_id = {case["id"]: case for case in payload["cases"]}
        self.assertEqual(by_id["docs_openai"]["actual"]["intent"], "docs")
        self.assertEqual(by_id["docs_openai"]["actual"]["skill"], "public-openai-docs")
        self.assertEqual(by_id["security_threat_model"]["actual"]["skill"], "public-security-threat-model")
        self.assertEqual(by_id["security_best_practices"]["actual"]["skill"], "public-security-best-practices")
        self.assertEqual(by_id["meeting_public"]["actual"]["intent"], "meeting")
        self.assertEqual(by_id["meeting_public"]["actual"]["skill"], "public-meeting-intelligence")
        self.assertEqual(by_id["skill_governance"]["actual"]["intent"], "skill_governance")
        self.assertEqual(by_id["skill_governance"]["actual"]["skill"], "public-skill-governance")
        self.assertEqual(by_id["push_recovery_cn"]["actual"]["wiki"], "public-push-recovery-wiki")
        self.assertEqual(by_id["push_recovery_cn"]["actual"]["tool_route"], "push_readiness")
        self.assertEqual(by_id["readme_capture"]["actual"]["wiki"], "public-repo-knowledge-hub")
        self.assertEqual(by_id["readme_capture"]["actual"]["wiki_action"], "promote")
        self.assertEqual(by_id["ts_refactor"]["actual"]["skill"], "public-typescript-implementation")
        self.assertEqual(by_id["docs_plus_wiki"]["actual"]["skill"], "public-openai-docs")
        self.assertEqual(by_id["docs_plus_wiki"]["actual"]["wiki"], "public-repo-knowledge-hub")
        self.assertEqual(by_id["general_chat"]["actual"]["intent"], "casual")
        self.assertEqual(by_id["general_chat"]["actual"]["tool_mode"], "none")

    def test_scorecard_exposes_reference_style_summary_fields(self) -> None:
        payload = code_scorecard()
        self.assertEqual(payload["score"], 100)
        self.assertIn("grade", payload)
        self.assertIn("p0_blocked", payload)
        self.assertIn("p0_violations", payload)
        self.assertIn("facts", payload)
        self.assertIn("dimensions", payload)
        self.assertFalse(payload["p0_blocked"], payload)
        self.assertEqual(len(payload["dimensions"]), 10)
        self.assertIn("git", payload["facts"])
        self.assertIn("storage", payload["facts"])
        self.assertIn("longmemeval", payload["facts"])


if __name__ == "__main__":
    unittest.main()
