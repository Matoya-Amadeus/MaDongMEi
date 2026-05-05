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


class RequestRouteStrengtheningTest(unittest.TestCase):
    def test_schema_authoring_docs_and_governance_are_publicly_linked(self) -> None:
        schema_path = ROOT / "config" / "capability" / "request-route-template-schema.json"
        guide_path = ROOT / "config" / "capability" / "request-route-authoring-guide.md"
        self.assertTrue(schema_path.exists(), str(schema_path))
        self.assertTrue(guide_path.exists(), str(guide_path))

        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        self.assertEqual(schema.get("schema_version"), 1)
        definitions = schema.get("definitions", {})
        for key in ("skillRoute", "toolHint", "memoryRoute", "wikiRoute", "realPromptCase"):
            self.assertIn(key, definitions)

        guide = guide_path.read_text(encoding="utf-8")
        for token in (
            "templates/capability/skill-route.template.json",
            "templates/capability/tool-hint.template.json",
            "config/capability/request-route-registry.json",
            "config/capability/request-route-real-prompt-suite.json",
            "config/capability/llmwiki-v2-policy.json",
            "config/capability/wiki-coverage-thresholds.json",
            "config/capability/phase-thresholds.json",
            "positive",
            "negative",
            "mixed",
            "zh_natural",
        ):
            self.assertIn(token, guide)
        self.assertNotIn("ma" + "ho", guide.lower())

        governance = (ROOT / "src" / "madongmei" / "governance.py").read_text(encoding="utf-8")
        self.assertIn("config/capability/request-route-template-schema.json", governance)
        self.assertIn("config/capability/request-route-authoring-guide.md", governance)

        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        for token in (
            "request-route-template-schema.json",
            "request-route-authoring-guide.md",
            "llmwiki-v2-policy.json",
            "wiki-coverage-thresholds.json",
            "phase-thresholds.json",
        ):
            self.assertIn(token, readme)
            self.assertIn(token, agents)

    def test_registry_templates_have_full_public_strengthening_fields(self) -> None:
        registry = json.loads((ROOT / "config" / "capability" / "request-route-registry.json").read_text(encoding="utf-8"))
        self.assertIn("skill_routes", registry)
        self.assertIn("memory_routes", registry)
        self.assertIn("wiki_routes", registry)
        self.assertIn("tool_hints", registry)
        for route in registry["skill_routes"]:
            for key in (
                "id",
                "name",
                "intent",
                "aliases",
                "positive_examples",
                "negative_examples",
                "threshold_policy",
                "suppression_rules",
                "tool_hints",
                "wiki_affinity",
                "llmwiki_affinity",
                "capture_policy",
            ):
                self.assertIn(key, route)
            self.assertIn("auto_load_threshold", route["threshold_policy"])

        for rel in (
            "templates/capability/skill-route.template.json",
            "templates/capability/memory-route.template.json",
            "templates/capability/wiki-route.template.json",
            "templates/capability/tool-hint.template.json",
            "templates/capability/real-prompt-case.template.json",
        ):
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertIn("threshold", text.lower() if "tool-hint" not in rel else text.lower())
            self.assertNotIn("ma" + "ho", text.lower())

    def test_llmwiki_and_coverage_sidecar_policies_exist_and_are_public_safe(self) -> None:
        for rel in (
            "config/capability/llmwiki-v2-policy.json",
            "config/capability/wiki-coverage-thresholds.json",
            "config/capability/phase-thresholds.json",
        ):
            path = ROOT / rel
            self.assertTrue(path.exists(), rel)
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("ma" + "ho", text.lower())
            self.assertNotIn("/" + "Users" + "/", text)
            self.assertNotIn("/" + "Volumes" + "/Python 1/", text)
            self.assertNotIn("bit" + "bucket", text.lower())
            payload = json.loads(text)
            self.assertIsInstance(payload, dict)

        llmwiki_policy = json.loads((ROOT / "config" / "capability" / "llmwiki-v2-policy.json").read_text(encoding="utf-8"))
        self.assertIn("weights", llmwiki_policy)
        self.assertIn("gate_thresholds", llmwiki_policy)

        wiki_coverage = json.loads((ROOT / "config" / "capability" / "wiki-coverage-thresholds.json").read_text(encoding="utf-8"))
        self.assertIn("stage1", wiki_coverage)
        self.assertIn("stage2", wiki_coverage)

        phase_thresholds = json.loads((ROOT / "config" / "capability" / "phase-thresholds.json").read_text(encoding="utf-8"))
        for stage in ("stage_a", "stage_b", "stage_c", "stage_d", "stage_e"):
            self.assertIn(stage, phase_thresholds)

    def test_pre_hook_uses_registry_metadata_for_skill_wiki_and_tool_routes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="madongmei-route-strength-") as tmp:
            env = env_for(Path(tmp) / "home")
            skill_payload = prepare_public_request_context(
                "Please bootstrap and validate the clean install workflow before release.",
                env=env,
            )
            self.assertEqual(skill_payload["route_trace"]["routes"]["skill"]["mode"], "selected")
            self.assertEqual(skill_payload["route_trace"]["routes"]["skill"]["selected"], "public-install-workflow")
            self.assertEqual(skill_payload["tool_route"]["selected"], "quality_gate")
            self.assertIn("metadata", skill_payload["route_trace"]["routes"]["skill"]["reason"])

            wiki_payload = prepare_public_request_context(
                "The canonical public policy should be captured in the wiki as a decision.",
                env=env,
            )
            self.assertEqual(wiki_payload["route_trace"]["routes"]["wiki"]["mode"], "selected")
            self.assertEqual(wiki_payload["route_trace"]["routes"]["wiki"]["selected"], "public-governance-wiki")
            self.assertEqual(wiki_payload["route_trace"]["routes"]["capture"]["selected"], "promote")
            self.assertEqual(wiki_payload["tool_route"]["selected"], "wiki_capture")

            casual_payload = prepare_public_request_context("hello, nice weather today", env=env)
            self.assertEqual(casual_payload["route_trace"]["routes"]["skill"]["mode"], "none")
            self.assertEqual(casual_payload["tool_route"]["mode"], "none")

    def test_real_prompt_suite_enforces_positive_negative_mixed_and_zh_cases(self) -> None:
        result = subprocess.run(
            [str(ROOT / "scripts" / "request_route_real_prompt_suite.py"), "--json"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["passed"], payload)
        tags = {tag for case in payload["cases"] for tag in case.get("case_tags", [])}
        self.assertTrue({"positive", "negative", "mixed", "zh_natural"}.issubset(tags), tags)
        self.assertGreaterEqual(payload["case_count"], 8)


if __name__ == "__main__":
    unittest.main()
