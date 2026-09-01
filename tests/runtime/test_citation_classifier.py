"""US3 classifier contract tests; all inference is injected and offline."""

from __future__ import annotations

import math
import unittest

from swos_runtime.citation_classifier import (
    LABELS,
    CitationPair,
    CitationSupportClassifier,
    DeterministicCitationChecks,
    VerifiedCalibration,
    VerifiedModelArtifact,
    admission_eligibility,
)


class CitationClassifierTests(unittest.TestCase):
    def _artifacts(self) -> tuple[VerifiedModelArtifact, VerifiedCalibration]:
        model = VerifiedModelArtifact(
            model_id="model-test",
            model_digest="m" * 64,
            label_order=LABELS,
            version="1.0.0",
            verified=True,
        )
        calibration = VerifiedCalibration(
            calibration_id="cal-test",
            model_digest="m" * 64,
            dataset_manifest_digest="d" * 64,
            ontology_digest="o" * 64,
            label_order=LABELS,
            temperature=1.0,
            thresholds={"directly_supports": 0.7},
            verified=True,
        )
        return model, calibration

    def test_five_labels_order_probability_and_batch_invariance(self) -> None:
        model, calibration = self._artifacts()
        pairs = [CitationPair(pair_id=f"p-{i}", claim="claim", passage="passage") for i in range(3)]
        classifier = CitationSupportClassifier(model=model, calibration=calibration, ontology_version="2.0.0")
        results = classifier.classify(pairs, logits=[[4, 0, 0, 0, 0]] * 3)
        self.assertEqual(LABELS, tuple(results[0].probabilities))
        self.assertEqual("directly_supports", results[0].support_level)
        self.assertAlmostEqual(1.0, sum(results[0].probabilities.values()), places=8)
        self.assertEqual("2.0.0", results[0].to_dict()["schema_version"])
        self.assertEqual(pairs[0].claim, results[0].to_dict()["input"]["claim"])
        self.assertEqual(pairs[0].canonical_input_digest, results[0].to_dict()["input"]["input_digest"])
        self.assertEqual([item.pair_id for item in results], ["p-0", "p-1", "p-2"])
        repeat = classifier.classify(pairs[:1], logits=[[4, 0, 0, 0, 0]])[0].to_dict()
        first = results[0].to_dict()
        first.pop("created_at")
        repeat.pop("created_at")
        self.assertEqual(first, repeat)

    def test_ood_corrupt_nonfinite_and_unknown_version_abstain(self) -> None:
        model, calibration = self._artifacts()
        pair = CitationPair(pair_id="p", claim="claim", passage="passage")
        classifier = CitationSupportClassifier(model=model, calibration=calibration, ontology_version="2.0.0")
        self.assertEqual("abstained", classifier.classify([pair], ood=[True])[0].status)
        self.assertEqual("abstained", classifier.classify([pair], logits=[[math.nan] * 5])[0].status)
        unknown = CitationSupportClassifier(model=model, calibration=calibration, ontology_version="9.0.0")
        self.assertEqual("abstained", unknown.classify([pair], logits=[[4, 0, 0, 0, 0]])[0].status)

    def test_deterministic_rule_rejection_has_no_support_label_and_is_not_admission(self) -> None:
        model, calibration = self._artifacts()
        pair = CitationPair(pair_id="p", claim="claim", passage="passage")
        classifier = CitationSupportClassifier(model=model, calibration=calibration, ontology_version="2.0.0")
        decision = classifier.classify([pair], logits=[[8, 0, 0, 0, 0]])[0]
        checks = DeterministicCitationChecks(
            source_exists=False,
            metadata_verified=False,
            rights_allowed=False,
            quote_contained=False,
            provenance_valid=False,
            rule_rejection="citation_laundering",
        )
        eligibility = admission_eligibility(pair, checks, decision)
        self.assertIsNone(eligibility.support_level)
        self.assertEqual("rule_rejected", eligibility.state)
        self.assertFalse(eligibility.eligible)


if __name__ == "__main__":
    unittest.main()
