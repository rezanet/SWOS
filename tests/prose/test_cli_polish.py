from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import Mock, patch

from swos_prose import cli


class PolishCliTests(unittest.TestCase):
    def test_polish_requires_explicit_api_key_when_generation_is_needed(self):
        stdout = StringIO()
        stderr = StringIO()
        argv = ["swos-prose", "polish", "--source", "A source sentence."]

        with (
            patch.dict(os.environ, {}, clear=True),
            patch.object(sys, "argv", argv),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            code = cli.main()

        self.assertEqual(code, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("OPENAI_API_KEY", stderr.getvalue())

    def test_reviewed_abstention_exemplar_needs_no_api_key_or_provider(self):
        source = "The revised workflow reduced implementation errors and simplified later review."
        stdout = StringIO()
        stderr = StringIO()
        argv = ["swos-prose", "polish", "--source", source]

        with (
            patch.dict(os.environ, {}, clear=True),
            patch.object(sys, "argv", argv),
            patch("swos_prose.cli._ProviderMustNotRun.rewrite") as sentinel_rewrite,
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            code = cli.main()

        self.assertEqual(code, 0)
        self.assertEqual(stdout.getvalue(), f"{source}\n")
        self.assertIn("NO_CHANGE_RECOMMENDED", stderr.getvalue())
        self.assertNotIn("OPENAI_API_KEY", stderr.getvalue())
        sentinel_rewrite.assert_not_called()

    def test_empty_source_is_successful_zero_provider_noop(self):
        stdout = StringIO()
        stderr = StringIO()
        argv = ["swos-prose", "polish", "--source", "   ", "--json"]

        with (
            patch.dict(os.environ, {}, clear=True),
            patch.object(sys, "argv", argv),
            patch("swos_prose.cli._ProviderMustNotRun.rewrite") as sentinel_rewrite,
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            code = cli.main()

        payload = json.loads(stdout.getvalue())
        self.assertEqual(code, 0)
        self.assertTrue(payload["safe_for_automatic_use"])
        self.assertEqual(payload["final_text"], "   ")
        self.assertIsNone(payload["verification_status"])
        self.assertEqual(stderr.getvalue(), "")
        sentinel_rewrite.assert_not_called()

    def test_long_literal_source_falls_back_from_filesystem_error(self):
        source = "A" * 1000
        content, was_file = cli.resolve_input(source)
        self.assertEqual(content, source)
        self.assertFalse(was_file)

    def test_valid_long_file_path_is_still_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            for index in range(6):
                path = path / (f"segment-{index}-" + "x" * 28)
            path.mkdir(parents=True)
            source_file = path / "source.txt"
            source_file.write_text("Read from a deeply nested file.", encoding="utf-8")
            self.assertGreater(len(str(source_file)), 200)

            content, was_file = cli.resolve_input(str(source_file))

        self.assertTrue(was_file)
        self.assertEqual(content, "Read from a deeply nested file.")

    def test_multiline_literal_source_is_not_statted_as_a_path(self):
        source = "First sentence.\nSecond sentence."
        content, was_file = cli.resolve_input(source)
        self.assertEqual(content, source)
        self.assertFalse(was_file)

    def test_polish_plain_output_is_final_text_and_status_is_stderr(self):
        result = Mock()
        result.final_text = "Polished sentence."
        result.safe_for_automatic_use = True
        result.generation_skipped_by_diagnostics = False
        result.verification_status = "PASS"
        result.used_source_fallback = False

        stdout = StringIO()
        stderr = StringIO()
        argv = ["swos-prose", "polish", "--source", "Source sentence."]

        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True),
            patch.object(sys, "argv", argv),
            patch(
                "swos_prose.providers.openai_rewrite.OpenAIResponsesRewriteProvider"
            ) as rewrite_cls,
            patch(
                "swos_prose.providers.openai_responses.OpenAIResponsesSemanticVerifierProvider"
            ) as verifier_cls,
            patch("swos_prose.cli.polish_text", return_value=result) as polish,
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            code = cli.main()

        self.assertEqual(code, 0)
        self.assertEqual(stdout.getvalue(), "Polished sentence.\n")
        self.assertIn("SWOS Prose polish: PASS", stderr.getvalue())
        kwargs = polish.call_args.kwargs
        self.assertTrue(kwargs["run_diagnostics"])
        self.assertEqual(kwargs["assurance"], "strict")
        self.assertIs(kwargs["rewrite_provider"], rewrite_cls.return_value)
        self.assertIs(kwargs["verifier_provider"], verifier_cls.return_value)

    def test_skip_diagnostics_is_forwarded_and_review_exits_nonzero(self):
        result = Mock()
        result.final_text = "Source sentence."
        result.safe_for_automatic_use = False
        result.generation_skipped_by_diagnostics = False
        result.verification_status = "REVIEW"
        result.used_source_fallback = True
        result.to_dict.return_value = {
            "mode": "polish",
            "final_text": "Source sentence.",
            "verification_status": "REVIEW",
        }

        stdout = StringIO()
        stderr = StringIO()
        argv = [
            "swos-prose",
            "polish",
            "--source",
            "Source sentence.",
            "--skip-diagnostics",
            "--json",
        ]

        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True),
            patch.object(sys, "argv", argv),
            patch("swos_prose.providers.openai_rewrite.OpenAIResponsesRewriteProvider"),
            patch("swos_prose.providers.openai_responses.OpenAIResponsesSemanticVerifierProvider"),
            patch("swos_prose.cli.polish_text", return_value=result) as polish,
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            code = cli.main()

        self.assertEqual(code, 1)
        self.assertIn('"verification_status": "REVIEW"', stdout.getvalue())
        self.assertEqual(stderr.getvalue(), "")
        self.assertFalse(polish.call_args.kwargs["run_diagnostics"])


if __name__ == "__main__":
    unittest.main()
