from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from swos_prose.dogfood import collect_dogfood, load_simple_env_file
from swos_prose.providers.mock import StaticSemanticVerifierProvider
from swos_prose.providers.rewrite_mock import StaticRewriteProvider


def _proposition(prop_id: str, text: str) -> dict:
    return {
        "id": prop_id,
        "text": text,
        "subject": None,
        "relation": None,
        "object": None,
        "modality": None,
        "modality_scope": None,
        "attribution": None,
        "causal_force": "none",
        "temporal_relation": None,
        "normative_stance": "neutral",
        "relation_sign": "neutral",
        "claim_type": "methodological",
        "epistemic_type": "method",
    }


def _equivalent_payload(source: str, candidate: str) -> dict:
    return {
        "equivalent": True,
        "independent_of_rewriter": True,
        "source_propositions": [_proposition("p1", source)],
        "candidate_propositions": [_proposition("c1", candidate)],
        "source_to_candidate": [{
            "source_id": "p1",
            "candidate_ids": ["c1"],
            "preserved": True,
            "modality_preserved": True,
            "scope_preserved": True,
            "attribution_preserved": True,
            "causal_force_preserved": True,
            "relational_direction_preserved": True,
            "confidence": 0.99,
            "reason": "Equivalent polish paraphrase.",
        }],
        "candidate_to_source": [{
            "candidate_id": "c1",
            "source_ids": ["p1"],
            "licensed": True,
            "new_claim": False,
            "confidence": 0.99,
            "reason": "Licensed by source.",
        }],
        "unresolved": [],
        "notes": [],
    }


class SimpleEnvLoaderTests(unittest.TestCase):
    def test_env_file_loads_without_overriding_process_environment(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / ".env"
            env_file.write_text(
                "# local only\nOPENAI_API_KEY=file-key\nexport SWOS_TEST_VALUE='quoted value'\n",
                encoding="utf-8",
            )
            with patch.dict(os.environ, {"OPENAI_API_KEY": "shell-key"}, clear=False):
                os.environ.pop("SWOS_TEST_VALUE", None)
                loaded = load_simple_env_file(env_file)
                self.assertEqual(os.environ["OPENAI_API_KEY"], "shell-key")
                self.assertEqual(os.environ["SWOS_TEST_VALUE"], "quoted value")
                self.assertEqual(loaded, ["SWOS_TEST_VALUE"])
                os.environ.pop("SWOS_TEST_VALUE", None)

    def test_env_file_rejects_malformed_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / ".env"
            env_file.write_text("NOT_A_PAIR\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_simple_env_file(env_file)


class DogfoodCollectorTests(unittest.TestCase):
    def test_collect_dogfood_writes_record_and_summary(self):
        source = "The analysis was performed using a t-test."
        candidate = "The analysis used a t-test."
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            corpus = root / "corpus"
            results = root / "results"
            corpus.mkdir()
            (corpus / "paragraph_001.txt").write_text(source, encoding="utf-8-sig")

            records = collect_dogfood(
                input_dir=corpus,
                output_dir=results,
                rewrite_provider=StaticRewriteProvider(candidate),
                verifier_provider=StaticSemanticVerifierProvider(_equivalent_payload(source, candidate)),
                assurance="strict",
            )

            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["status"], "PASS")
            self.assertEqual(records[0]["source_text"], source)
            self.assertEqual(records[0]["final_text"], candidate)
            self.assertTrue(records[0]["verifier_used"])
            self.assertIsNone(records[0]["verification_skip_reason"])
            self.assertIsNone(records[0]["preset"])
            self.assertIsNone(records[0]["diagnostics_before"])
            self.assertEqual(records[0]["human_review"]["category"], None)

            result_path = results / "paragraph_001.txt.json"
            self.assertTrue(result_path.exists())
            persisted = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(persisted["candidate_text"], candidate)

            summary = json.loads((results / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["sample_count"], 1)
            self.assertEqual(summary["status_counts"], {"PASS": 1})

    def test_terminal_newline_only_records_no_change_and_preserves_source(self):
        source = "The claim is unchanged.\n"
        candidate = "The claim is unchanged."
        verifier = StaticSemanticVerifierProvider(_equivalent_payload(source, candidate))

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            corpus = root / "corpus"
            results = root / "results"
            corpus.mkdir()
            (corpus / "paragraph_001.txt").write_text(source, encoding="utf-8")

            records = collect_dogfood(
                input_dir=corpus,
                output_dir=results,
                rewrite_provider=StaticRewriteProvider(candidate),
                verifier_provider=verifier,
                assurance="strict",
            )

            self.assertEqual(records[0]["status"], "NO_CHANGE_RECOMMENDED")
            self.assertEqual(records[0]["final_text"], source)
            self.assertFalse(records[0]["used_fallback"])
            self.assertFalse(records[0]["verifier_used"])
            self.assertEqual(records[0]["verification_skip_reason"], "terminal_newline_only")
            self.assertEqual(verifier.calls, 0)

            summary = json.loads((results / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["status_counts"], {"NO_CHANGE_RECOMMENDED": 1})

    def test_deterministic_reject_records_verifier_skip_reason(self):
        source = "The response rate was 18.7%."
        candidate = "The response rate was 19%."

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            corpus = root / "corpus"
            results = root / "results"
            corpus.mkdir()
            (corpus / "paragraph_001.txt").write_text(source, encoding="utf-8")

            records = collect_dogfood(
                input_dir=corpus,
                output_dir=results,
                rewrite_provider=StaticRewriteProvider(candidate),
                verifier_provider=StaticSemanticVerifierProvider(
                    _equivalent_payload(source, candidate)
                ),
                assurance="strict",
            )

            self.assertEqual(records[0]["status"], "REJECT")
            self.assertFalse(records[0]["verifier_used"])
            self.assertEqual(
                records[0]["verification_skip_reason"],
                "deterministic_blocker:number_changed",
            )
            self.assertEqual(records[0]["verifier_notes"], [])

    def test_collect_dogfood_rejects_empty_supported_corpus(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            corpus = root / "corpus"
            results = root / "results"
            corpus.mkdir()
            (corpus / "ignore.csv").write_text("not a prose sample", encoding="utf-8")
            with self.assertRaises(ValueError):
                collect_dogfood(
                    input_dir=corpus,
                    output_dir=results,
                    rewrite_provider=StaticRewriteProvider("x"),
                    verifier_provider=None,
                )


if __name__ == "__main__":
    unittest.main()
