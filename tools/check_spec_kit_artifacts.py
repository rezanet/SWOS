"""Run deterministic consistency checks for the active Spec Kit feature."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REQUIRED_FILES = (
    "spec.md",
    "plan.md",
    "tasks.md",
    "checklists/requirements.md",
)
PLACEHOLDER_MARKERS = (
    "[FEATURE NAME]",
    "[DATE]",
    "[NEEDS CLARIFICATION",
    "$ARGUMENTS",
    "[PROJECT_NAME]",
    "[PRINCIPLE_",
    "[SECTION_",
)


def _feature_directory(repo_root: Path) -> Path:
    feature_file = repo_root / ".specify" / "feature.json"
    if feature_file.is_file():
        payload = json.loads(feature_file.read_text(encoding="utf-8"))
        configured = payload.get("feature_directory")
        if isinstance(configured, str) and configured.strip():
            return (repo_root / configured).resolve()
    candidates = sorted((repo_root / "specs").glob("*/spec.md"))
    if len(candidates) == 1:
        return candidates[0].parent.resolve()
    raise ValueError("unable to resolve one active Spec Kit feature directory")


def validate_feature_directory(feature_dir: Path) -> list[str]:
    """Return deterministic consistency failures for one feature directory."""

    errors: list[str] = []
    files = {relative: feature_dir / relative for relative in REQUIRED_FILES}
    for relative, path in files.items():
        if not path.is_file():
            errors.append(f"missing required Spec Kit artifact: {relative}")
    if errors:
        return errors

    content = {relative: path.read_text(encoding="utf-8") for relative, path in files.items()}
    for relative, text in content.items():
        for marker in PLACEHOLDER_MARKERS:
            if marker in text:
                errors.append(f"unresolved template placeholder {marker!r}: {relative}")

    spec = content["spec.md"]
    plan = content["plan.md"]
    tasks = content["tasks.md"]
    checklist = content["checklists/requirements.md"]
    required_headings = (
        "## objective",
        "## commands",
        "## project structure",
        "## code and document style",
        "## testing strategy",
        "## boundaries",
        "## success criteria",
    )
    spec_lower = spec.lower()
    for heading in required_headings:
        if heading not in spec_lower:
            errors.append(f"spec.md is missing required section: {heading[3:]}")

    requirement_ids = set(re.findall(r"\b(?:FR|NFR)-\d{3}\b", spec))
    checklist_ids = set(re.findall(r"\b(?:FR|NFR)-\d{3}\b", checklist))
    missing_checklist = sorted(requirement_ids - checklist_ids)
    if missing_checklist:
        errors.append(f"requirements missing from checklist: {', '.join(missing_checklist)}")
    if "## requirement traceability" not in plan.lower():
        errors.append("plan.md is missing a requirement traceability section")
    for requirement_id in sorted(requirement_ids):
        if requirement_id not in plan:
            errors.append(f"requirement missing from plan traceability: {requirement_id}")

    stories = set(re.findall(r"User Story (\d+)", spec))
    task_story_labels = set(re.findall(r"\[US(\d+)\]", tasks))
    for story in sorted(stories):
        if story not in task_story_labels:
            errors.append(f"user story {story} has no task label")

    task_ids = re.findall(r"^- \[[ x]\] (T\d{3})\b", tasks, flags=re.MULTILINE)
    if not task_ids:
        errors.append("tasks.md contains no Spec Kit task IDs")
    if len(task_ids) != len(set(task_ids)):
        errors.append("tasks.md contains duplicate task IDs")
    for line in tasks.splitlines():
        has_explicit_root_path = bool(re.search(r"`[^`]+\.(?:md|json|py|yml|yaml)`", line))
        if (
            re.match(r"^- \[[ x]\] T\d{3}\b", line)
            and "/" not in line
            and "\\" not in line
            and not has_explicit_root_path
        ):
            errors.append(f"task has no explicit file path: {line}")

    for version in ("1.0.0", "v1.1", "v2.0"):
        if version not in spec or version not in plan:
            errors.append(f"version track is not consistent across spec and plan: {version}")
    return sorted(set(errors))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--feature-dir", type=Path, default=None)
    args = parser.parse_args(argv)
    repo_root = args.repo_root.resolve()
    try:
        feature_dir = (args.feature_dir or _feature_directory(repo_root)).resolve()
        errors = validate_feature_directory(feature_dir)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors = [f"unable to inspect Spec Kit feature: {exc}"]
    if errors:
        print("Spec Kit artifact consistency check failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"Spec Kit artifact consistency check passed: {feature_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
