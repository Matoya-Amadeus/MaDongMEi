from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PublicDocsContractTest(unittest.TestCase):
    def test_public_storage_docs_and_projection_are_linked(self) -> None:
        for rel in ("knowledge/repo-storage-audit.md", "knowledge/repo-retention-policy.md"):
            path = ROOT / rel
            self.assertTrue(path.exists(), rel)
            text = path.read_text(encoding="utf-8")
            self.assertIn("tracked worktree", text)
            self.assertIn("ignored", text)
            self.assertNotIn("ai-" + "madongmei-memory", text.lower())

        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        projection = (ROOT / "config" / "public-projection.yaml").read_text(encoding="utf-8")
        for token in (
            "knowledge/repo-storage-audit.md",
            "knowledge/repo-retention-policy.md",
            "madongmei_code_scorecard.py",
            "request-route-registry.json",
            "llmwiki-v2-policy.json",
            "wiki-coverage-thresholds.json",
            "phase-thresholds.json",
        ):
            self.assertIn(token, readme)
            self.assertIn(token, agents)
            self.assertIn(token, projection)

    def test_readme_recent_note_is_current_for_public_release(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("更新时间：2026-05-06", readme)
        self.assertIn("scorecard", readme.lower())
        self.assertIn("compact", readme.lower())
        self.assertIn("## 解决什么问题", readme)
        self.assertIn("## 三分钟上手", readme)
        self.assertIn("LongMemEval 评估、命中与结果解读", readme)
        self.assertIn("Codex 专属安装链", readme)
        self.assertIn("Maintained jointly by **AI·MaDongMei** and **Human·Matoya**", readme)


if __name__ == "__main__":
    unittest.main()
