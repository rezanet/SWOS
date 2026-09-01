"""Research Grade multimodal finalization bindings."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from swos_runtime.finalizer import finalize_work_order_run
from swos_runtime.image_analysis import DeterministicFakeImageProvider, ImageAnalysisRequest
from swos_runtime.media import MediaAssetRecord
from tests.runtime.test_finalizer import HostNativeFinalizerTests


class ResearchGradeMultimodalFinalizerTests(unittest.TestCase):
    def test_complete_image_analysis_is_bound_to_epg_v2_and_host_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run = HostNativeFinalizerTests()._ready_run(tmp)
            asset = MediaAssetRecord(
                asset_id="asset-1",
                object_id="object-1",
                role="surrogate",
                mime_type="image/jpeg",
                byte_size=1,
                width=20,
                height=20,
                byte_digest="a" * 64,
                acquisition_uri="https://example.org/a.jpg",
                rights={"view": {"status": "allowed"}, "analyse": {"status": "allowed"}},
            )
            result = DeterministicFakeImageProvider().analyze(
                ImageAnalysisRequest(
                    work_id="object-1",
                    run_id=run.state["run_id"],
                    object_id="object-1",
                    assets=(asset,),
                    target_questions=("What is visible?",),
                )
            )
            run.record_image_analysis(result)
            output = Path(tmp) / "output"
            outcome = finalize_work_order_run(run, output)
            self.assertEqual("APPROVED", outcome.status, outcome.blocking_reasons)
            image = json.loads((output / "image-analysis-result.json").read_text(encoding="utf-8"))
            self.assertEqual("complete", image["status"])
            self.assertTrue(image["response_digest"])
            epg = json.loads((output / "provenance-v2.json").read_text(encoding="utf-8"))
            self.assertTrue(any("/observation/" in identifier for identifier in epg["entities"]))
            bundle = json.loads((output / "host-bundle.json").read_text(encoding="utf-8"))
            self.assertIsNotNone(bundle["work_order_run"]["epg_v2_export"])


if __name__ == "__main__":
    unittest.main()
