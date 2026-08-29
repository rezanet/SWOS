"""Inspect SWOS workflow triggers and provider-call boundaries deterministically."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

WORKFLOW_DIR = Path(".github/workflows")
MANUAL_TRIGGER = "workflow_dispatch"
PROVIDER_MARKERS = (
    "OPENAI_API_KEY",
    "SWOS_PROSE_RUN_LIVE_OPENAI",
    "pip install openai",
    "openai_api",
)
ORDINARY_WORKFLOW_MARKERS = ("pull_request", "push")


def _top_level_block(text: str, heading: str) -> str:
    lines = text.splitlines()
    start = next((index for index, line in enumerate(lines) if line == f"{heading}:"), None)
    if start is None:
        return ""
    selected = [lines[start]]
    for line in lines[start + 1 :]:
        if line and not line.startswith((" ", "\t")):
            break
        selected.append(line)
    return "\n".join(selected)


def trigger_names(text: str) -> set[str]:
    """Return trigger keys from the top-level GitHub Actions ``on`` block."""

    block = _top_level_block(text, "on")
    return {
        match.group(1)
        for match in re.finditer(
            r"^\s{2}(pull_request|push|workflow_dispatch|schedule):", block, re.MULTILINE
        )
    }


def job_block(text: str, job_id: str) -> str:
    """Return one top-level job block, preserving its conditions and steps."""

    lines = text.splitlines()
    start = next((index for index, line in enumerate(lines) if line == f"  {job_id}:"), None)
    if start is None:
        return ""
    selected = [lines[start]]
    for line in lines[start + 1 :]:
        if re.match(r"^  [A-Za-z0-9_-]+:\s*$", line):
            break
        selected.append(line)
    return "\n".join(selected)


def _provider_jobs_are_dispatch_only(text: str, path: Path, errors: list[str]) -> None:
    if not any(marker.lower() in text.lower() for marker in PROVIDER_MARKERS):
        return
    triggers = trigger_names(text)
    if not triggers.intersection(ORDINARY_WORKFLOW_MARKERS):
        return

    for job_id in re.findall(
        r"^  ([A-Za-z0-9_-]+):\s*$", _top_level_block(text, "jobs"), re.MULTILINE
    ):
        block = job_block(text, job_id)
        if any(marker.lower() in block.lower() for marker in PROVIDER_MARKERS):
            if (
                "github.event_name == 'workflow_dispatch'" not in block
                and 'github.event_name == "workflow_dispatch"' not in block
            ):
                errors.append(f"provider job is not manual-dispatch-only: {path}:{job_id}")


def inspect_workflow_files(repo_root: Path) -> list[str]:
    """Return all trigger/provider profile violations under ``repo_root``."""

    workflow_root = repo_root / WORKFLOW_DIR
    errors: list[str] = []
    if not workflow_root.is_dir():
        return [f"workflow directory does not exist: {WORKFLOW_DIR.as_posix()}"]

    workflows = sorted(workflow_root.glob("*.yml")) + sorted(workflow_root.glob("*.yaml"))
    if not workflows:
        return [f"no workflow files found under {WORKFLOW_DIR.as_posix()}"]

    for path in workflows:
        text = path.read_text(encoding="utf-8")
        triggers = trigger_names(text)
        _provider_jobs_are_dispatch_only(text, path.relative_to(repo_root), errors)

        if path.name == "swos-ci.yml":
            if any(marker.lower() in text.lower() for marker in PROVIDER_MARKERS):
                errors.append(
                    f"ordinary SWOS CI contains a provider marker: {path.relative_to(repo_root)}"
                )

        if path.name == "swos-portability-gate.yml":
            if "pull_request" not in triggers or MANUAL_TRIGGER not in triggers:
                errors.append("portability gate must support pull_request and workflow_dispatch")
            architecture = job_block(text, "architecture")
            release = job_block(text, "release-gates")
            if "--definitions-only" not in architecture:
                errors.append("portability architecture job must use --definitions-only")
            if "--release" not in release:
                errors.append("portability release job must use --release")
            if (
                "github.event_name == 'workflow_dispatch'" not in release
                and 'github.event_name == "workflow_dispatch"' not in release
            ):
                errors.append("portability release job must be dispatch-only")
            if "github.event.pull_request.draft" in release:
                errors.append("portability release job must not run from pull_request conditions")
            if "name: SWOS v2 Portability Gate" in text:
                errors.append("portability workflow name must be version-neutral")

        if path.name == "swos-prose-benchmark.yml":
            live_benchmark = job_block(text, "benchmark-live")
            if "Record exact dispatch SHA" not in live_benchmark:
                errors.append("live benchmark must record its exact dispatch SHA")
            if "Require configured live provider credential" not in live_benchmark:
                errors.append("live benchmark must fail closed when credentials are absent")
            if "Require complete live benchmark evidence" not in live_benchmark:
                errors.append("live benchmark must fail closed when evidence is missing")
            if "continue-on-error: true" in live_benchmark:
                errors.append("live benchmark must fail closed on provider or benchmark failure")

        if path.name in {
            "autonomous-swos-acceptance.yml",
            "pigment-article-acceptance.yml",
            "swos-live-evidence.yml",
        }:
            if triggers != {MANUAL_TRIGGER}:
                errors.append(f"live workflow is not manual-only: {path.relative_to(repo_root)}")

        if path.name == "swos-live-evidence.yml":
            if "commit_sha:" not in text:
                errors.append("live evidence workflow must require a commit_sha input")
            if "ref: ${{ inputs.commit_sha }}" not in text:
                errors.append("live evidence workflow must checkout the selected commit_sha")
            if "git rev-parse HEAD" not in text or "selected-sha" not in text:
                errors.append("live evidence workflow must record the resolved exact SHA")
            if "Require configured live provider credential" not in text:
                errors.append("live evidence workflow must fail closed when credentials are absent")
            if "Require complete live evidence" not in text:
                errors.append("live evidence workflow must fail closed when evidence is missing")
            if "actions/upload-artifact@v4" not in text:
                errors.append("live evidence workflow must upload evidence")

    return sorted(set(errors))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    args = parser.parse_args(argv)
    errors = inspect_workflow_files(args.repo_root.resolve())
    if errors:
        print("Workflow profile inspection failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(
        "Workflow profile inspection passed: ordinary PR/push profiles are deterministic and live profiles are dispatch-only"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
