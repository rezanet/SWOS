"""Thin adapter from the harness to production runtime evaluation controls."""

from __future__ import annotations

from typing import Any

from swos_runtime.evaluation import EvaluationSubject, evaluate_plane


def evaluate_fixture(
    plane: str,
    fixture: dict[str, Any],
    *,
    run_dir: str,
) -> dict[str, Any]:
    """Evaluate one probe against a verified finalized run."""
    subject = EvaluationSubject.load(run_dir)
    result = evaluate_plane(subject, plane, [fixture])
    failure = result.get("failures", [])
    return {
        "fixture_id": str(fixture.get("fixture_id") or "?"),
        "passed": result["gate_result"] == "pass",
        "observation": failure[0]["reason"] if failure else "runtime-bound control passed",
        "subject_run_id": subject.run_id,
        "manifest_sha256": subject.manifest_sha256,
    }
