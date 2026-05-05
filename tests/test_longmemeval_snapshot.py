from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "benchmarks" / "longmemeval" / "official-suite-summary.json"


class LongMemEvalSnapshotTest(unittest.TestCase):
    def test_official_snapshot_metrics(self) -> None:
        payload = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        self.assertTrue(payload["passed"])
        self.assertEqual(int(payload["questions"]), 500)
        row = payload["rows"][0]
        self.assertEqual(row["backend"], "madongmei_overall")
        self.assertAlmostEqual(float(row["recall_any@5"]), 1.0, places=6)
        self.assertAlmostEqual(float(row["recall_any@10"]), 1.0, places=6)
        self.assertAlmostEqual(float(row["ndcg_any@10"]), 1.0, places=6)
        profiles = payload.get("internal_profiles", {})
        self.assertAlmostEqual(float(profiles["madongmei_semantic_hybrid:default"]["ndcg_any@10"]), 1.0, places=6)
        self.assertAlmostEqual(float(profiles["madongmei_semantic_hybrid:tfidf_fallback"]["ndcg_any@10"]), 1.0, places=6)


if __name__ == "__main__":
    unittest.main()
