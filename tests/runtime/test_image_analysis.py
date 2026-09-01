"""Provider-neutral bounded image-analysis contract tests."""

from __future__ import annotations

import hashlib
import sys
import types
import unittest
from unittest.mock import patch

from swos_runtime.image_analysis import (
    DeterministicFakeImageProvider,
    ImageAnalysisRequest,
    OpenAIImageAnalysisProvider,
)
from swos_runtime.image_analysis_openai import (
    OpenAIImageAnalysisProvider as RegisteredOpenAIImageAnalysisProvider,
)
from swos_runtime.media import MediaAssetRecord


class ImageAnalysisTests(unittest.TestCase):
    def _request(self, **changes):
        asset = MediaAssetRecord(
            asset_id="a",
            object_id="o",
            role="surrogate",
            mime_type="image/jpeg",
            byte_size=10,
            width=100,
            height=100,
            byte_digest="a" * 64,
            acquisition_uri="https://example.org/a",
            rights={"view": {"status": "allowed"}, "analyse": {"status": "allowed"}},
        )
        values = {
            "work_id": "w",
            "run_id": "r",
            "object_id": "o",
            "assets": (asset,),
            "target_questions": ("What is visible?",),
            "allowed_actions": ("analyse",),
        }
        values.update(changes)
        return ImageAnalysisRequest(**values)

    def test_explicit_statuses_and_deterministic_fake(self) -> None:
        request = self._request()
        for status in ("complete", "partial", "insufficient", "denied", "error"):
            provider = DeterministicFakeImageProvider(status=status)
            result = provider.analyze(request)
            self.assertEqual(status, result.status)
            self.assertEqual(result.to_dict(), provider.analyze(request).to_dict())
            self.assertRegex(result.response_digest, r"^[0-9a-f]{64}$")
            self.assertEqual(request.request_digest, result.request_digest)
            if status == "complete":
                self.assertTrue(result.observations[0].selector)

    def test_rights_denied_and_real_adapter_not_run_are_not_success(self) -> None:
        denied = self._request(allowed_actions=())
        self.assertEqual("denied", DeterministicFakeImageProvider().analyze(denied).status)
        result = OpenAIImageAnalysisProvider(api_key=None).analyze(self._request())
        self.assertNotEqual("complete", result.status)
        self.assertEqual("not_run", result.contract_status)
        registered = RegisteredOpenAIImageAnalysisProvider(api_key=None).analyze(self._request())
        self.assertEqual(result.status, registered.status)
        self.assertEqual(result.contract_status, registered.contract_status)
        self.assertEqual(result.request_digest, registered.request_digest)
        self.assertEqual(result.config_digest, registered.config_digest)

    def test_view_right_and_resource_bounds_are_enforced_by_the_fake(self) -> None:
        asset = self._request().assets[0]
        denied_asset = type(asset)(
            **{**asset.to_dict(), "rights": {"analyse": {"status": "allowed"}}}
        )
        denied = DeterministicFakeImageProvider().analyze(self._request(assets=(denied_asset,)))
        self.assertEqual("denied", denied.status)
        second = type(asset)(**{**asset.to_dict(), "asset_id": "b", "byte_digest": "b" * 64})
        bounded = self._request(
            assets=(asset, second),
            resource_limits={"max_assets": 8, "max_observations": 1, "max_seconds": 60},
        )
        result = DeterministicFakeImageProvider().analyze(bounded)
        self.assertEqual("partial", result.status)
        self.assertLessEqual(len(result.observations), 1)

    def test_live_provider_rejects_unverified_acquisition_uri(self) -> None:
        result = OpenAIImageAnalysisProvider(api_key="secret", enabled=True).analyze(
            self._request()
        )
        self.assertEqual("error", result.status)
        self.assertIn("asset_content_digest_unverified", " ".join(result.limitations))

    def test_live_provider_sends_only_digest_verified_captured_content(self) -> None:
        payload = b"verified-image-bytes"
        asset = self._request().assets[0]
        asset = type(asset)(
            **{
                **asset.to_dict(),
                "byte_size": len(payload),
                "byte_digest": hashlib.sha256(payload).hexdigest(),
            }
        )
        request = self._request(assets=(asset,), captured_bytes={"a": payload})
        calls = []
        client = types.SimpleNamespace(
            responses=types.SimpleNamespace(
                create=lambda **kwargs: (
                    calls.append(kwargs) or types.SimpleNamespace(output_text="Visible")
                )
            )
        )
        fake_module = types.ModuleType("openai")
        fake_module.OpenAI = lambda api_key: client
        with patch.dict(sys.modules, {"openai": fake_module}):
            result = OpenAIImageAnalysisProvider(api_key="secret", enabled=True).analyze(request)
        self.assertEqual("complete", result.status)
        image_url = calls[0]["input"][0]["content"][1]["image_url"]
        self.assertTrue(image_url.startswith("data:image/jpeg;base64,"))
        self.assertNotIn(asset.acquisition_uri, image_url)


if __name__ == "__main__":
    unittest.main()
