#!/usr/bin/env python3
"""Enforce the Agent Skills six-field frontmatter constraint on core skills.

Host-specific frontmatter keys cause hard validation errors wherever the Agent
Skills specification is enforced. They belong in adapters/, never in skills/.

Usage:  python3 tools/lint_skills.py [--strict]
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"

ALLOWED = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}

# Known host extensions, reported with a pointed message rather than a generic one.
HOST_EXTENSIONS = {
    "argument-hint",
    "paths",
    "hooks",
    "context",
    "agent",
    "disable-model-invocation",
    "user-invocable",
    "disallowed-tools",
    "model",
    "effort",
    "background",
}

NAME_RE = re.compile(r"^[a-z0-9-]{1,64}$")
ACTIVATION_TOKEN_BUDGET = 5000
DESCRIPTION_MAX = 1024
COMPATIBILITY_MAX = 500
NAME_MAX = 64


def parse_frontmatter(text):
    """Minimal YAML frontmatter key extraction - top-level keys only."""
    if not text.startswith("---"):
        return None, None
    end = text.find("\n---", 3)
    if end == -1:
        return None, None
    block = text[3:end]
    body = text[end + 4 :]
    keys = {}
    for line in block.splitlines():
        if not line or line.startswith("#") or line[0] in " \t-":
            continue
        if ":" in line:
            k, _, v = line.partition(":")
            keys[k.strip()] = v.strip()
    return keys, body


def main():
    strict = "--strict" in sys.argv
    errors, warnings, checked = [], [], 0

    for skill_md in sorted(SKILLS.glob("*/SKILL.md")):
        checked += 1
        rel = skill_md.relative_to(ROOT)
        dir_name = skill_md.parent.name
        text = skill_md.read_text(encoding="utf-8")
        keys, body = parse_frontmatter(text)

        if keys is None:
            errors.append(f"{rel}: no YAML frontmatter block found")
            continue

        unexpected = sorted(set(keys) - ALLOWED)
        if unexpected:
            host_keys = [k for k in unexpected if k in HOST_EXTENSIONS]
            errors.append(
                f"{rel}: Unexpected key(s) in SKILL.md frontmatter: {', '.join(unexpected)}. "
                f"Allowed properties are: {', '.join(sorted(ALLOWED))}."
            )
            if host_keys:
                errors.append(
                    f"{rel}: {', '.join(host_keys)} are host extensions. "
                    "Move them to adapters/<host>/overlay.* - see contracts/host-adapter-contract/."
                )

        for req in ("name", "description"):
            if req not in keys:
                errors.append(f"{rel}: missing required frontmatter field '{req}'")

        name = keys.get("name", "")
        if name and not NAME_RE.match(name):
            errors.append(
                f"{rel}: name '{name}' must be lowercase letters, numbers and hyphens, max {NAME_MAX} chars"
            )
        if name and name != dir_name:
            errors.append(f"{rel}: name '{name}' must equal the parent directory name '{dir_name}'")

        desc = keys.get("description", "")
        if len(desc) > DESCRIPTION_MAX:
            errors.append(f"{rel}: description is {len(desc)} chars, max {DESCRIPTION_MAX}")
        if desc and len(desc) < 120:
            warnings.append(
                f"{rel}: description is {len(desc)} chars. It is the ONLY thing an agent sees "
                "at discovery. State the triggering situations in the user's vocabulary."
            )

        compat = keys.get("compatibility", "")
        if len(compat) > COMPATIBILITY_MAX:
            errors.append(f"{rel}: compatibility is {len(compat)} chars, max {COMPATIBILITY_MAX}")

        approx_tokens = len(body.split()) * 1.35 if body else 0
        if approx_tokens > ACTIVATION_TOKEN_BUDGET:
            warnings.append(
                f"{rel}: activation body approx {int(approx_tokens)} tokens, budget {ACTIVATION_TOKEN_BUDGET}. "
                "Move detail into references/ - progressive disclosure loads those on demand."
            )

    for wmsg in warnings:
        print(f"WARN  {wmsg}")
    if errors:
        print(f"FAIL  {len(errors)} problem(s):")
        for e in errors:
            print(f"  - {e}")
        return 1
    if warnings and strict:
        print("FAIL  warnings are errors under --strict")
        return 1

    print(f"OK    {checked} skill(s) conform to the six-field Agent Skills constraint.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
