from __future__ import annotations

import tempfile
import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from madongmei.store import capture_record, load_records, summarize


class StoreBehaviorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory(prefix="madongmei-store-")
        self.db_path = Path(self.tempdir.name) / "memory.jsonl"

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_capture_dedupes_and_sanitizes_private_paths(self) -> None:
        first = capture_record(
            title="wiki note",
            text="See ~/Documents/Private for details.",
            tags=["public"],
            source="manual",
            kind="wiki",
            bucket="wiki",
            confidence=0.9,
            reason="rule",
            source_ref="~/Work/Private",
            idempotency="same-key",
            path=self.db_path,
        )
        second = capture_record(
            title="wiki note",
            text="See ~/Documents/Private for details.",
            tags=["public"],
            source="manual",
            kind="wiki",
            bucket="wiki",
            confidence=0.9,
            reason="rule",
            source_ref="~/Work/Private",
            idempotency="same-key",
            path=self.db_path,
        )

        self.assertEqual(first["id"], second["id"])
        loaded = load_records(self.db_path)
        self.assertEqual(len(loaded), 1)
        self.assertNotIn("~/", loaded[0]["text"])
        self.assertNotIn("~/", loaded[0]["source_ref"])
        self.assertEqual(loaded[0]["bucket"], "wiki")
        self.assertEqual(loaded[0]["route"], "wiki")

    def test_ttl_pruning_and_summary_counts(self) -> None:
        capture_record(
            title="expired note",
            text="Old memory that should be pruned.",
            tags=["memory"],
            source="manual",
            kind="memory",
            bucket="memory",
            ttl=1,
            extra={"created_at": "2020-01-01T00:00:00Z"},
            path=self.db_path,
        )
        capture_record(
            title="live wiki",
            text="Public rule stays around.",
            tags=["wiki"],
            source="manual",
            kind="wiki",
            bucket="wiki",
            ttl=None,
            reason="rule",
            path=self.db_path,
        )

        loaded = load_records(self.db_path)
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0]["bucket"], "wiki")
        summary = summarize(loaded)
        self.assertEqual(summary["count"], 1)
        self.assertEqual(summary["bucket_counts"][0][0], "wiki")
        self.assertEqual(summary["route_counts"][0][0], "wiki")


if __name__ == "__main__":
    unittest.main()
