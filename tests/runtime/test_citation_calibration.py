"""Calibration fit isolation and threshold binding tests."""

from __future__ import annotations

import unittest

from swos_runtime.citation_calibration import (
    CalibrationBindingError,
    expected_calibration_error,
    fit_temperature,
    metric_confidence_interval,
    selective_threshold,
)
from swos_runtime.citation_classifier import LABELS


class CitationCalibrationTests(unittest.TestCase):
    def test_temperature_and_ece_are_deterministic_and_locked_test_is_not_consumed(self) -> None:
        logits = [[4.0, 0, 0, 0, 0], [0, 4.0, 0, 0, 0]]
        labels = [0, 1]
        artifact = fit_temperature(
            logits,
            labels,
            label_order=LABELS,
            model_digest="m" * 64,
            dataset_manifest_digest="d" * 64,
            ontology_digest="o" * 64,
        )
        self.assertGreater(artifact.temperature, 0)
        self.assertEqual(LABELS, artifact.label_order)
        repeat = fit_temperature(
            logits,
            labels,
            label_order=LABELS,
            model_digest="m" * 64,
            dataset_manifest_digest="d" * 64,
            ontology_digest="o" * 64,
        ).to_dict()
        first = artifact.to_dict()
        first.pop("created_at")
        repeat.pop("created_at")
        self.assertEqual(first, repeat)
        self.assertLessEqual(expected_calibration_error([[0.9, 0.1, 0, 0, 0]], [0], bins=10), 0.2)
        lower, upper = metric_confidence_interval(95, 100)
        self.assertLessEqual(lower, upper)

    def test_selective_threshold_has_immutable_model_data_and_ontology_binding(self) -> None:
        threshold = selective_threshold(
            probabilities=[[0.9, 0.05, 0.02, 0.02, 0.01]],
            labels=[0],
            target_error=0.02,
            model_digest="m" * 64,
            dataset_manifest_digest="d" * 64,
            ontology_digest="o" * 64,
            label_order=LABELS,
        )
        self.assertEqual("m" * 64, threshold.model_digest)
        with self.assertRaises(CalibrationBindingError):
            threshold.assert_bound(
                model_digest="x" * 64,
                dataset_manifest_digest="d" * 64,
                ontology_digest="o" * 64,
                label_order=LABELS,
            )


if __name__ == "__main__":
    unittest.main()
