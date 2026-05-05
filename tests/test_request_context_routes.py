from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from madongmei.request_context import prepare_public_request_context  # noqa: E402


def env_for(home: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["CODEX_HOME"] = str(home.parent / ".codex")
    env["MADONGMEI_HOME"] = str(home)
    env["MADONGMEI_WIKI_DIR"] = str(home / "knowledge" / "wiki")
    env["MADONGMEI_SKILL_DIR"] = str(home / "skills" / "public-autopilot")
    env["PYTHONPATH"] = f"{ROOT / 'src'}{os.pathsep}{env.get('PYTHONPATH', '')}".rstrip(os.pathsep)
    return env


class RequestContextRoutesTest(unittest.TestCase):
    def test_pre_hook_payload_explains_public_route_without_execution(self) -> None:
        with tempfile.TemporaryDirectory(prefix="madongmei-context-") as tmp:
            home = Path(tmp) / "home"
            payload = prepare_public_request_context("Please validate the public install workflow", env=env_for(home))
        self.assertEqual(payload["schema_version"], 1)
        self.assertIn("codex_context", payload)
        self.assertIn("route_trace", payload)
        self.assertIn("tool_route", payload)
        self.assertFalse(payload["tool_route"]["auto_execute"])
        self.assertEqual(payload["route_trace"]["injection_order"][0], "codex_context")
        self.assertIn("memory", payload["route_trace"]["routes"])
        self.assertIn("tool", payload["route_trace"]["routes"])
        self.assertEqual(payload["codex_context"]["repo"], "MaDongMei")

    def test_real_prompt_suite_script_checks_routes(self) -> None:
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
        self.assertGreaterEqual(payload["case_count"], 4)
        self.assertTrue(all(row["passed"] for row in payload["cases"]))


if __name__ == "__main__":
    unittest.main()
