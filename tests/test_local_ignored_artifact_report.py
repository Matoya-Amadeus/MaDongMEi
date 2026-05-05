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

from madongmei.governance import ignored_artifacts_report  # noqa: E402


class LocalIgnoredArtifactReportTest(unittest.TestCase):
    def test_report_has_target_scoped_public_rows(self) -> None:
        payload = ignored_artifacts_report()
        self.assertEqual(payload["schema_version"], 1)
        self.assertTrue(payload["passed"])
        self.assertEqual(payload["mode"], "report")
        self.assertIn("artifacts", payload)
        self.assertIn("storage_facts", payload)
        for row in payload["artifacts"]:
            for key in ("target_id", "path", "size_bytes", "risk", "rebuild_cost", "cleanable"):
                self.assertIn(key, row)
            self.assertNotIn(str(ROOT.parent), row["path"])
            self.assertIn(row["risk"], {"low", "medium", "high"})
            self.assertIsInstance(row["cleanable"], bool)

    def test_script_emits_same_shape_without_private_paths(self) -> None:
        env = os.environ.copy()
        env["PYTHONPATH"] = f"{ROOT / 'src'}{os.pathsep}{env.get('PYTHONPATH', '')}".rstrip(os.pathsep)
        result = subprocess.run(
            [str(ROOT / "scripts" / "local_ignored_artifact_report.py"), "--json"],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["schema_version"], 1)
        self.assertIn("artifacts", payload)
        self.assertNotIn(str(ROOT.parent), result.stdout)

    def test_report_can_describe_runtime_cache_target(self) -> None:
        with tempfile.TemporaryDirectory(prefix="madongmei-ignored-") as tmp:
            root = Path(tmp)
            cache = root / ".madongmei-runtime" / "cache"
            cache.mkdir(parents=True)
            (cache / "artifact.bin").write_bytes(b"x" * 12)
            payload = ignored_artifacts_report(root=root, ignored_paths=[".madongmei-runtime/cache/"])
        rows = {row["target_id"]: row for row in payload["artifacts"]}
        self.assertIn("runtime-cache:.madongmei-runtime/cache", rows)
        self.assertEqual(rows["runtime-cache:.madongmei-runtime/cache"]["size_bytes"], 12)
        self.assertEqual(rows["runtime-cache:.madongmei-runtime/cache"]["risk"], "low")
        self.assertTrue(rows["runtime-cache:.madongmei-runtime/cache"]["cleanable"])


if __name__ == "__main__":
    unittest.main()
