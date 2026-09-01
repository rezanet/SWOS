"""Additional deterministic branch coverage for Research Grade boundaries."""

from __future__ import annotations

import math
import sys
import types
import unittest
from unittest.mock import patch

from swos_runtime.citation_classifier import (
    LABELS,
    CitationPair,
    CitationSupportClassifier,
    DeterministicCitationChecks,
    VerifiedCalibration,
    VerifiedModelArtifact,
    admission_eligibility,
    deterministic_precheck,
)
from swos_runtime.image_analysis import (
    DeterministicFakeImageProvider,
    ImageAnalysisRequest,
    ImageAnalysisResult,
    OpenAIImageAnalysisProvider,
    VisualInterpretation,
    VisualObservation,
    assess_promotion,
    commit_promotion,
    evaluate_cross_modal_support,
    rollback_promotion,
)
from swos_runtime.media import (
    AccessibilityRecord,
    AssetValidation,
    MediaAssetRecord,
    MediaRightsPolicy,
    ObjectInspectionActivity,
    ObjectRecord,
    RegionSelector,
    derive_asset,
    ingest_iiif3,
    inherit_rights,
    normalize_selector,
    redact_asset_for_export,
    validate_media_asset,
)
from swos_runtime.prov_interop import (
    epg_v1_to_v2,
    epg_v2_to_v1,
    parse_prov,
    prov_to_epg,
    serialize_prov,
)
from swos_runtime.prov_model import ProvDocument, ResourceLimits
from swos_runtime.prov_validation import canonical_fingerprint, validate_prov


class ResearchGradeCoverageTests(unittest.TestCase):
    def _asset(self, **changes: object) -> MediaAssetRecord:
        values: dict[str, object] = {
            "asset_id": "asset-1",
            "object_id": "object-1",
            "role": "surrogate",
            "mime_type": "image/jpeg",
            "byte_size": 10,
            "width": 100,
            "height": 80,
            "byte_digest": "a" * 64,
            "acquisition_uri": "https://example.org/asset.jpg",
            "rights": {
                "view": {"status": "allowed"},
                "analyse": {"status": "allowed"},
                "export": {"status": "allowed"},
            },
        }
        values.update(changes)
        return MediaAssetRecord(**values)

    def _request(self, **changes: object) -> ImageAnalysisRequest:
        values: dict[str, object] = {
            "work_id": "work-1",
            "run_id": "run-1",
            "object_id": "object-1",
            "assets": (self._asset(),),
            "target_questions": ("What is visible?",),
        }
        values.update(changes)
        return ImageAnalysisRequest(**values)

    def _classifier(self, **changes: object) -> CitationSupportClassifier:
        model = VerifiedModelArtifact(model_id="m", model_digest="m" * 64, verified=True)
        calibration = VerifiedCalibration(
            calibration_id="c",
            model_digest="m" * 64,
            dataset_manifest_digest="d" * 64,
            ontology_digest="o" * 64,
            verified=True,
            thresholds={"directly_supports": 0.7},
        )
        values: dict[str, object] = {"model": model, "calibration": calibration}
        values.update(changes)
        return CitationSupportClassifier(**values)

    def test_media_rights_objects_accessibility_and_validation_boundaries(self) -> None:
        self.assertEqual("swos.media-rights", MediaRightsPolicy.from_mapping({}).policy_id)
        with self.assertRaises(ValueError):
            MediaRightsPolicy(actions=("view",))
        with self.assertRaises(ValueError):
            MediaRightsPolicy(unknown_effect="allow")
        self.assertIn("object_id", ObjectRecord("o", "painting", "A").to_dict())
        self.assertIn("inspection_id", ObjectInspectionActivity("i", "o", "a", "surface").to_dict())
        invalid_accessibility = AccessibilityRecord("bad", "evidentiary", "")
        valid_accessibility = AccessibilityRecord(
            "a" * 64,
            "evidentiary",
            "A work",
            long_description="A detailed work",
            review_status="reviewed",
        )
        self.assertFalse(invalid_accessibility.valid)
        self.assertTrue(valid_accessibility.valid)
        self.assertIn("valid", valid_accessibility.to_dict())
        invalid = self._asset(
            asset_id="",
            object_id="",
            role="invalid",
            mime_type="",
            byte_size=-1,
            width=0,
            height=0,
            byte_digest="BAD",
            acquisition_uri="relative/path",
            accessibility=AccessibilityRecord(
                "b" * 64, "decorative", "Alt", review_status="reviewed"
            ),
            generated=True,
        )
        report = validate_media_asset(invalid, required_actions=("not-an-action", "view"))
        self.assertFalse(report.valid)
        self.assertTrue(report.errors)
        self.assertTrue(report.warnings)
        self.assertIsInstance(report.to_dict(), dict)
        self.assertFalse(AssetValidation(False, action_states={"view": "allowed"}).allowed("view"))

    def test_media_inheritance_selectors_derivatives_and_iiif_edges(self) -> None:
        parent = self._asset(
            rights={
                "view": {"status": "allowed"},
                "analyse": {"status": "allowed"},
                "transform": {"status": "denied"},
                "create_derivative": {"status": "unknown"},
                "export": {"status": "denied"},
            }
        )
        inherited = inherit_rights(
            parent,
            {
                "transform": {"status": "allowed"},
                "create_derivative": {"status": "allowed", "grant_id": "g", "evidence": "e"},
            },
        )
        self.assertEqual("denied", inherited["transform"]["status"])
        self.assertEqual("allowed", inherited["create_derivative"]["status"])
        self.assertEqual("unknown", inherited["quote"]["status"])
        child = derive_asset(
            parent,
            asset_id="child",
            byte_digest="b" * 64,
            transform="crop",
            rights_grant={"transform": {"status": "allowed", "grant_id": "g", "evidence": "e"}},
        )
        self.assertEqual("generated", child.role)
        exportable = self._asset(
            rights={
                "view": {"status": "allowed"},
                "analyse": {"status": "allowed"},
                "export": {"status": "allowed"},
            }
        )
        self.assertTrue(redact_asset_for_export(exportable)["redacted"] is False)
        self.assertIn("bytes", exportable.to_dict(include_bytes=True))
        asset = self._asset()
        pixel = normalize_selector(
            RegionSelector("pixel", {"x": 1, "y": 2, "w": 20, "h": 30}, "a" * 64), asset
        )
        percent = normalize_selector(RegionSelector("percent", "pct:0,0,50,50", "a" * 64), asset)
        svg = normalize_selector(
            RegionSelector(
                "web_annotation_svg",
                '<svg><rect x="1" y="2" width="20" height="30" /></svg>',
                "a" * 64,
            ),
            asset,
        )
        self.assertEqual((1, 2, 20, 30), pixel.normalized)
        self.assertEqual((0, 0, 50, 40), percent.normalized)
        self.assertEqual((1, 2, 20, 30), svg.normalized)
        bad_selectors = (
            RegionSelector("pixel", "1,2,3", "a" * 64),
            RegionSelector("percent", "1,2,3,4", "a" * 64),
            RegionSelector("svg", "<svg><script>x</script></svg>", "a" * 64),
            RegionSelector("svg", "<svg></svg>", "a" * 64),
            RegionSelector("unknown", "x", "a" * 64),
        )
        for selector in bad_selectors:
            with self.subTest(selector=selector.selector_type), self.assertRaises(ValueError):
                normalize_selector(selector, asset)
        with self.assertRaises(ValueError):
            normalize_selector(RegionSelector("pixel", "0,0,1,1", "b" * 64), asset)
        manifest = {
            "type": "Manifest",
            "id": "https://example.org/manifest",
            "items": [
                {
                    "id": "https://example.org/canvas/1",
                    "width": 100,
                    "height": 80,
                    "byte_digest": "a" * 64,
                },
                "ignored",
            ],
        }
        assets = ingest_iiif3(
            manifest,
            object_id="object-1",
            rights={"view": {"status": "allowed"}},
            source_uri="https://example.org/manifest",
        )
        self.assertEqual(1, len(assets))
        with self.assertRaises(ValueError):
            ingest_iiif3(
                {"type": "Image"}, object_id="o", rights={}, source_uri="https://example.org/m"
            )
        with self.assertRaises(ValueError):
            ingest_iiif3(
                {"type": "Manifest", "items": [{"width": 0, "height": 1}]},
                object_id="o",
                rights={},
                source_uri="https://example.org/m",
            )

    def test_image_provider_cross_modal_and_promotion_boundaries(self) -> None:
        request = self._request()
        self.assertEqual(
            "insufficient",
            DeterministicFakeImageProvider().analyze(self._request(assets=())).status,
        )
        self.assertEqual(
            "insufficient",
            DeterministicFakeImageProvider()
            .analyze(self._request(resource_limits={"max_assets": 0}))
            .status,
        )
        self.assertEqual(
            "denied",
            DeterministicFakeImageProvider().analyze(self._request(allowed_actions=())).status,
        )
        with self.assertRaises(ValueError):
            DeterministicFakeImageProvider(status="bad")
        interpretation = VisualInterpretation("i", "o", (), "A proposed reading")
        result = ImageAnalysisResult(
            "partial", request.request_digest, "fake", "m", "c", interpretations=(interpretation,)
        )
        self.assertTrue(any("without_observation" in value for value in result.limitations))
        observation = VisualObservation(
            "obs",
            "o",
            "a",
            "a" * 64,
            "Visible",
            "machine",
            supports_claim_ids=("claim",),
            review_status="human_reviewed",
        )
        supported = evaluate_cross_modal_support(
            {"claim_id": "claim", "object_id": "o", "asset_id": "a"},
            (observation,),
            ({"claim_id": "claim", "support_level": "directly_supports"},),
        )
        self.assertEqual("supported", supported.status)
        attribution = evaluate_cross_modal_support(
            {"claim_id": "claim", "object_id": "o", "claim_type": "attribution"}, (observation,), ()
        )
        self.assertEqual("blocked", attribution.status)
        many = tuple(
            VisualObservation(str(i), "o", str(i), "a" * 64, "Visible", "machine") for i in range(9)
        )
        self.assertEqual(
            "limited",
            evaluate_cross_modal_support({"claim_id": "claim", "object_id": "o"}, many, ()).status,
        )

        baseline = {
            "metric": 0.5,
            "source_sha": "s",
            "case_ids": ["c"],
            "provider": "p",
            "model": "m",
            "config_digest": "c",
            "prompt_digest": "p",
            "seed": 1,
            "draw_digest": "d",
            "artifact_digest": "a",
        }
        candidate = {
            **baseline,
            "metric": 0.7,
            "lower_95_ci": 0.2,
            "live_exact_head": True,
            "human_quorum": True,
            "role_separation": True,
            "rollback_tested": True,
            "pack_only_fallback": True,
            "status": "evaluated",
        }
        assessment = assess_promotion(
            capability="image", pack="pack", stage="stage", baseline=baseline, candidate=candidate
        )
        self.assertTrue(assessment.eligible)
        enabled = commit_promotion(
            assessment,
            {
                "disposition": "approved",
                "approver_id": "owner",
                "expires_at": "2099-01-01T00:00:00+00:00",
            },
        )
        self.assertTrue(enabled.enabled)
        self.assertEqual("rolled_back", rollback_promotion(enabled, reason="test").status)
        disabled = commit_promotion(assessment, {})
        self.assertFalse(disabled.enabled)
        blocked = assess_promotion(
            capability="image",
            pack="pack",
            stage="stage",
            baseline=baseline,
            candidate={
                **candidate,
                "source_sha": "other",
                "safety_regressions": True,
                "expires_at": "2000-01-01T00:00:00+00:00",
            },
        )
        self.assertFalse(blocked.eligible)

    def test_openai_adapter_is_bounded_and_fail_closed_with_injected_client(self) -> None:
        request = self._request()
        client = types.SimpleNamespace(
            responses=types.SimpleNamespace(
                create=lambda **kwargs: types.SimpleNamespace(output_text="A visible line")
            )
        )
        fake_module = types.ModuleType("openai")
        fake_module.OpenAI = lambda api_key: client
        with patch.dict(sys.modules, {"openai": fake_module}):
            result = OpenAIImageAnalysisProvider(api_key="secret", enabled=True).analyze(request)
            self.assertEqual("complete", result.status)
            self.assertEqual("executed", result.contract_status)
            self.assertEqual(1, len(result.observations))
        empty_client = types.SimpleNamespace(
            responses=types.SimpleNamespace(
                create=lambda **kwargs: types.SimpleNamespace(output_text="")
            )
        )
        empty_module = types.ModuleType("openai")
        empty_module.OpenAI = lambda api_key: empty_client
        with patch.dict(sys.modules, {"openai": empty_module}):
            self.assertEqual(
                "insufficient",
                OpenAIImageAnalysisProvider(api_key="secret", enabled=True).analyze(request).status,
            )
        error_module = types.ModuleType("openai")
        error_module.OpenAI = lambda api_key: (_ for _ in ()).throw(RuntimeError("provider down"))
        with patch.dict(sys.modules, {"openai": error_module}):
            self.assertEqual(
                "error",
                OpenAIImageAnalysisProvider(api_key="secret", enabled=True).analyze(request).status,
            )
        self.assertEqual(
            "insufficient",
            OpenAIImageAnalysisProvider(api_key="secret", enabled=True)
            .analyze(self._request(assets=()))
            .status,
        )
        self.assertEqual(
            "denied",
            OpenAIImageAnalysisProvider(api_key="secret", enabled=True)
            .analyze(self._request(allowed_actions=()))
            .status,
        )

    def test_prov_migration_parser_and_classifier_edge_paths(self) -> None:
        with self.assertRaises(ValueError):
            epg_v1_to_v2({"schema_version": "2.0.0"}, base_iri="https://example.org/")
        with self.assertRaises(ValueError):
            epg_v1_to_v2({"schema_version": "1.0.0"}, base_iri="relative")
        v1 = {
            "schema_version": "1.0.0",
            "work_id": "w",
            "entities": [{"entity_id": "e", "label": "E"}, "ignored"],
            "activities": [],
            "agents": [],
            "relations": [{"subject": "e", "relation_type": "used"}, "ignored"],
        }
        migrated = epg_v1_to_v2(v1, base_iri="https://example.org/")
        self.assertEqual("1.0.0", epg_v2_to_v1(migrated)["schema_version"])
        document = ProvDocument(**migrated)
        self.assertEqual("2.0.0", prov_to_epg(document)["schema_version"])
        with self.assertRaises(ValueError):
            serialize_prov(document, "unsupported")
        with self.assertRaises(ValueError):
            serialize_prov({}, "prov-json")
        with self.assertRaises(ValueError):
            parse_prov(b"not prov", "prov-n")
        with self.assertRaises(ValueError):
            parse_prov("not bytes", "prov-json")
        payload = {
            "prefix": {},
            "entity": {},
            "activity": {},
            "agent": {},
            "used": {"r": {"entity": "e"}},
            "bundle": {},
        }
        parsed = parse_prov(
            (
                __import__("json").dumps({**payload, "swos": {"base_iri": "https://example.org/"}})
            ).encode(),
            "prov-json",
        )
        self.assertEqual(1, len(parsed.relations))
        with self.assertRaises(ValueError):
            parse_prov(b"{}", "prov-json")
        limits = ResourceLimits(max_bytes=1)
        with self.assertRaises(ValueError):
            limits.check_bytes(2)
        self.assertIsNotNone(canonical_fingerprint(document))
        self.assertTrue(validate_prov(document).syntax)

        pair = CitationPair(
            "pair",
            "claim",
            passage="passage",
            source_id="source",
            source_digest="s" * 64,
            span_start=0,
            span_end=7,
        )
        empty = self._classifier().classify([])
        self.assertEqual([], empty)

        def backend(rows: object) -> list[list[int]]:
            return [[8, 0, 0, 0, 0] for _ in rows]  # type: ignore[union-attr]

        classified = self._classifier(backend=backend).classify([pair])
        self.assertEqual("directly_supports", classified[0].support_level)
        mapped = self._classifier().classify(
            [pair],
            probabilities=[{label: (1 if label == "context_only" else 0) for label in LABELS}],
        )
        self.assertEqual("context_only", mapped[0].support_level)
        self.assertEqual("error", self._classifier().classify([pair], logits=[])[0].status)
        self.assertEqual(
            "abstained",
            self._classifier().classify([pair], probabilities=[[math.nan] * 5])[0].status,
        )
        low = self._classifier().classify([pair], probabilities=[[0.3, 0.2, 0.2, 0.2, 0.1]])[0]
        self.assertEqual("abstained", low.status)
        checks = deterministic_precheck(
            pair,
            {
                "source_id": "source",
                "metadata_verified": True,
                "text": "different",
                "redistribution_allowed": False,
                "retraction_status": "retracted",
            },
        )
        self.assertFalse(checks.passed)
        eligibility = admission_eligibility(pair, checks.to_dict(), classified[0])
        self.assertFalse(eligibility.eligible)
        self.assertFalse(
            admission_eligibility(
                pair,
                DeterministicCitationChecks(
                    source_exists=True,
                    metadata_verified=True,
                    rights_allowed=True,
                    quote_contained=True,
                    provenance_valid=True,
                ),
                mapped[0],
            ).eligible
        )


if __name__ == "__main__":
    unittest.main()
