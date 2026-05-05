from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_PARTS = {".git", "__pycache__", ".pytest_cache", ".venv"}
SKIP_SUFFIXES = {".pyc", ".pyo"}


class PublicNamingContractTest(unittest.TestCase):
    HISTORY_FORBIDDEN_REMOTE_PATTERN = (
        "/"
        + "Volumes"
        + "/Python 1|"
        + "Bit"
        + "bucket|"
        + "bit"
        + "bucket|ai-"
        + "madongmei"
        + "-memory|ai-"
        + ("ma" + "ho")
        + "-memory"
    )

    def _non_self_files(self):
        for path in ROOT.rglob("*"):
            rel = path.relative_to(ROOT)
            if any(part in SKIP_PARTS for part in rel.parts):
                continue
            if path.suffix in SKIP_SUFFIXES:
                continue
            if rel == Path(__file__).relative_to(ROOT):
                continue
            yield path, rel

    def test_public_surface_uses_madongmei_not_legacy_name(self) -> None:
        offenders: list[str] = []
        for path, rel in self._non_self_files():
            rel_text = str(rel)
            forbidden = "ma" + "ho"
            if forbidden in rel_text.lower():
                offenders.append(f"path:{rel_text}")
                continue
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if forbidden in text.lower():
                offenders.append(f"content:{rel_text}")
        self.assertEqual(offenders, [])

    def test_public_surface_has_no_private_machine_paths_or_person_handles(self) -> None:
        forbidden_tokens = [
            "/" + "Users" + "/",
            "/" + "Volumes" + "/Python 1/",
            "/" + "Volumes" + "/Python 1/" + ("Bit" + "bucket"),
            "Bit" + "bucket",
            "ai-" + "madongmei-memory",
            "zhang" + "qian",
            "AI·" + ("Ma" + "ho"),
        ]
        offenders: list[str] = []
        for path, rel in self._non_self_files():
            rel_text = str(rel)
            for token in forbidden_tokens:
                if token.lower() in rel_text.lower():
                    offenders.append(f"path:{rel_text}:{token}")
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            lowered = text.lower()
            for token in forbidden_tokens:
                if token.lower() in lowered:
                    offenders.append(f"content:{rel_text}:{token}")
        self.assertEqual(offenders, [])

    def test_git_history_has_no_private_email_or_private_remote_markers(self) -> None:
        import subprocess

        email_probe = subprocess.run(
            [
                "git",
                "-C",
                str(ROOT),
                "log",
                "--format=%an%x00%ae%x00%cn%x00%ce",
                "--all",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(email_probe.returncode, 0, email_probe.stderr)
        private_email = "1067184851" + "@" + "qq.com"
        self.assertNotIn(private_email, email_probe.stdout)

        revisions = subprocess.run(
            ["git", "-C", str(ROOT), "rev-list", "--all"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(revisions.returncode, 0, revisions.stderr)
        revs = [line.strip() for line in revisions.stdout.splitlines() if line.strip()]
        if not revs:
            return
        grep = subprocess.run(
            [
                "git",
                "-C",
                str(ROOT),
                "grep",
                "-n",
                "-I",
                "-E",
                self.HISTORY_FORBIDDEN_REMOTE_PATTERN,
                *revs,
                "--",
                ".",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(grep.returncode, 1, grep.stdout[:2000])


if __name__ == "__main__":
    unittest.main()
