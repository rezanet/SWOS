"""Locked citation evaluation reporting and provenance contracts."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from swos_runtime.citation_classifier import LABELS
from swos_runtime.models import canonical_digest
from tools.evaluate_citation_classifier import (
    EvaluationBlocked,
    _gate_report,
    _load_calibration,
    _load_model,
    evaluate,
)


class CitationEvaluationTests(unittest.TestCase):
    def test_direct_precision_gate_requires_confidence_bound(self) -> None:
        def metric(value: float, lower: float = 0.99, upper: float = 1.0) -> dict[str, float]:
            return {
                "value": value,
                "lower_95": lower,
                "upper_95": upper,
                "successes": 1,
                "total": 1,
            }
        metrics = {
            "direct_support_precision": metric(0.99, lower=0.97),
            "contradiction_recall": metric(1.0),
            "not_supported_recall": metric(1.0),
            "macro_f1": 1.0,
            "expected_calibration_error": 0.0,
            "selective_coverage": metric(1.0),
            "selective_error": metric(0.0),
            "unsupported_auto_admission": metric(0.0, upper=0.001),
            "ood_or_unsupported_version_abstention": metric(
                0.0, lower=0.0, upper=0.0
            ),
        }
        report = _gate_report(
            metrics,
            {
                "discipline": {
                    "engineering": {
                        "macro_f1": 1.0,
                        "direct_support_precision": metric(1.0),
                    }
                }
            },
            {"p95_ms": 1.0, "gate_pass": True},
        )

        self.assertFalse(report["gates"]["direct_support_precision"]["pass"])
        self.assertFalse(report["gates"]["direct_support_precision"]["lower_95_pass"])
        self.assertFalse(report["pass"])

    def test_calibration_digest_tampering_fails_closed(self) -> None:
        model_bytes = b"verified citation model artifact"
        model_digest = hashlib.sha256(model_bytes).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "model.bin").write_bytes(model_bytes)
            (root / "model.json").write_text(
                json.dumps(
                    {
                        "status": "frozen",
                        "verified": True,
                        "model_id": "citation-model-test",
                        "model_digest": model_digest,
                        "label_order": list(LABELS),
                        "dataset_manifest_digest": "d" * 64,
                        "ontology_version": "2.0.0",
                        "ontology_digest": "e" * 64,
                        "artifact_path": "model.bin",
                    }
                ),
                encoding="utf-8",
            )
            (root / "calibration.json").write_text(
                json.dumps(
                    {
                        "status": "frozen",
                        "verified": True,
                        "calibration_id": "calibration-test",
                        "model_digest": model_digest,
                        "dataset_manifest_digest": "d" * 64,
                        "ontology_digest": "e" * 64,
                        "label_order": list(LABELS),
                        "temperature": 1.0,
                        "thresholds": {label: 0.0 for label in LABELS},
                        "ece": 0.0,
                        "calibration_split_digest": "b" * 64,
                        "locked_test_used": False,
                        "calibration_digest": "a" * 64,
                    }
                ),
                encoding="utf-8",
            )

            model, _ = _load_model(root / "model.json")
            with self.assertRaises(EvaluationBlocked):
                _load_calibration(
                    root / "calibration.json", model=model, ontology_version="2.0.0"
                )

    def test_malformed_verified_model_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "model.json").write_text(
                json.dumps(
                    {
                        "status": "frozen",
                        "verified": True,
                        "model_id": "malformed-model",
                        "model_digest": "a" * 64,
                        "dataset_manifest_digest": "d" * 64,
                        "label_order": 5,
                    }
                ),
                encoding="utf-8",
            )

            report = evaluate(
                root / "model.json",
                root / "missing-calibration.json",
                root / "missing-locked-test.jsonl",
                root / "predictions.jsonl",
                root / "report.json",
            )

            self.assertEqual("not_run", report["status"])
            self.assertEqual("", (root / "predictions.jsonl").read_text(encoding="utf-8"))

    def test_evaluation_rejects_aliased_immutable_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "output.json"

            with self.assertRaises(RuntimeError):
                evaluate(
                    root / "missing-model.json",
                    root / "missing-calibration.json",
                    root / "missing-locked-test.jsonl",
                    output,
                    output,
                )

            self.assertFalse(output.exists())

    def test_evaluation_emits_raw_decisions_metrics_and_packaged_latency(self) -> None:
        dataset_digest = "d" * 64
        ontology_digest = "e" * 64
        model_bytes = b"verified citation model artifact"
        model_digest = hashlib.sha256(model_bytes).hexdigest()
        rows = []
        disciplines = (
            "art_history",
            "art_criticism",
            "engineering",
            "humanities",
            "interdisciplinary",
            "materials_science",
            "philosophy",
            "psychology",
            "technical_writing",
        )
        for index in range(2000):
            label_index = index % len(LABELS)
            rows.append(
                {
                    "pair_id": f"pair-{index:04d}",
                    "claim": f"claim-{index}",
                    "exact_quote": f"exact quote {index}",
                    "context": f"bounded context {index}",
                    "source_id": "source-1",
                    "source_digest": "s" * 64,
                    "discipline": disciplines[index % len(disciplines)],
                    "label": LABELS[label_index],
                    "ood": index < 20,
                    "logits": [10.0 if position == label_index else 0.0 for position in range(5)],
                }
            )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "model.bin").write_bytes(model_bytes)
            (root / "model.json").write_text(
                json.dumps(
                    {
                        "schema_version": "2.0.0",
                        "status": "frozen",
                        "model_id": "citation-model-test",
                        "model_digest": model_digest,
                        "label_order": list(LABELS),
                        "dataset_manifest_digest": dataset_digest,
                        "ontology_version": "2.0.0",
                        "ontology_digest": ontology_digest,
                        "config_digest": "c" * 64,
                        "artifact_path": "model.bin",
                        "verified": True,
                    }
                ),
                encoding="utf-8",
            )
            calibration_payload = {
                "schema_version": "2.0.0",
                "status": "frozen",
                "calibration_id": "calibration-test",
                "model_digest": model_digest,
                "dataset_manifest_digest": dataset_digest,
                "ontology_digest": ontology_digest,
                "label_order": list(LABELS),
                "temperature": 1.0,
                "thresholds": {label: 0.0 for label in LABELS},
                "ece": 0.0,
                "calibration_split_digest": "b" * 64,
                "locked_test_used": False,
                "verified": True,
            }
            calibration_payload["calibration_digest"] = canonical_digest(
                {
                    "calibration_id": calibration_payload["calibration_id"],
                    "model_digest": calibration_payload["model_digest"],
                    "dataset_manifest_digest": calibration_payload["dataset_manifest_digest"],
                    "ontology_digest": calibration_payload["ontology_digest"],
                    "label_order": calibration_payload["label_order"],
                    "temperature": calibration_payload["temperature"],
                    "thresholds": calibration_payload["thresholds"],
                    "ece": calibration_payload["ece"],
                    "calibration_split_digest": calibration_payload["calibration_split_digest"],
                    "locked_test_used": calibration_payload["locked_test_used"],
                }
            )
            (root / "calibration.json").write_text(
                json.dumps(calibration_payload), encoding="utf-8"
            )
            locked_path = root / "locked.jsonl"
            locked_path.write_text(
                "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
                encoding="utf-8",
            )

            report = evaluate(
                root / "model.json",
                root / "calibration.json",
                locked_path,
                root / "predictions.jsonl",
                root / "report.json",
            )

            prediction = json.loads((root / "predictions.jsonl").read_text().splitlines()[0])

        self.assertEqual("frozen", report["status"])
        self.assertEqual(2000, report["locked_test_count"])
        self.assertGreater(report["metrics"]["macro_f1"], 0.98)
        self.assertEqual(1.0, report["metrics"]["direct_support_precision"]["value"])
        self.assertEqual(0.99, report["metrics"]["contradiction_recall"]["value"])
        self.assertEqual(9, len(report["slices"]["discipline"]))
        self.assertEqual(100, report["latency"]["sample_count"])
        self.assertLessEqual(report["latency"]["p95_ms"], 5000.0)
        self.assertLessEqual(report["latency"]["p95_seconds"], 5.0)
        self.assertEqual(100, len(report["latency"]["samples_ms"]))
        self.assertRegex(report["latency"]["sample_input_digest"], r"^[0-9a-f]{64}$")
        self.assertTrue(report["latency"]["gate_pass"])
        self.assertEqual(
            1.0,
            report["metrics"]["ood_or_unsupported_version_abstention"]["value"],
        )
        self.assertTrue(
            report["gates"]["gates"]["ood_or_unsupported_version_abstention"]["pass"]
        )
        self.assertEqual(rows[0]["pair_id"], prediction["pair_id"])
        self.assertEqual(rows[0]["claim"], prediction["input"]["claim"])
        self.assertEqual(rows[0]["exact_quote"], prediction["input"]["exact_quote"])
        self.assertEqual(prediction["input"]["input_digest"], prediction["input_digest"])
        self.assertRegex(prediction["provenance"]["code_sha"], r"^[0-9a-f]{40}$")
        self.assertRegex(prediction["provenance"]["config_digest"], r"^[0-9a-f]{64}$")
        self.assertEqual(
            hashlib.sha256(rows[0]["claim"].encode("utf-8")).hexdigest(),
            prediction["provenance"]["claim_digest"],
        )
        self.assertEqual(
            hashlib.sha256(rows[0]["exact_quote"].encode("utf-8")).hexdigest(),
            prediction["provenance"]["span_digest"],
        )
        self.assertEqual("CitationSupportClassifier/offline-injected", prediction["provenance"]["backend"])
        self.assertTrue(prediction["provenance"]["execution_id"])


if __name__ == "__main__":
    unittest.main()
