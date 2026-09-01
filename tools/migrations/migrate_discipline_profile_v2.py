"""Reversible v1/v2 discipline-profile migration with an explicit warning window."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from swos_runtime.models import canonical_digest  # noqa: E402

SUPPORTED_V2 = {
    "art_history",
    "art_criticism",
    "engineering",
    "humanities",
    "interdisciplinary",
    "materials_science",
    "philosophy",
    "psychology",
    "technical_writing",
}
V1_ONLY = {"enterprise_reporting"}


class DisciplineMigrationError(ValueError):
    pass


def migrate_profile(profile: Mapping[str, Any], *, direction: str = "v1-to-v2") -> dict[str, Any]:
    value = dict(profile)
    if direction == "v1-to-v2":
        discipline = str(value.get("discipline") or "")
        if discipline in V1_ONLY:
            raise DisciplineMigrationError(
                "enterprise_reporting is retained only by v1; choose an explicit approved v2 discipline"
            )
        discipline = discipline.replace("-", "_")
        if discipline not in SUPPORTED_V2:
            raise DisciplineMigrationError(f"unsupported v1 discipline {discipline or '<missing>'}")
        value["schema_version"] = "2.0.0"
        value["discipline"] = discipline
        value["discipline_iri"] = f"https://swos.example.org/discipline/{discipline}"
        value["migration"] = {
            "from_schema_version": str(profile.get("schema_version") or "1.0.0"),
            "original_discipline": str(profile.get("discipline") or discipline),
            "reversible": True,
            "warning_window_minor_releases": 1,
            "tool_digest": canonical_digest({"tool": "migrate_discipline_profile_v2", "version": "2.0.0"}),
        }
        return value
    if direction == "v2-to-v1":
        migration = value.get("migration")
        if not isinstance(migration, Mapping) or not migration.get("reversible"):
            raise DisciplineMigrationError("v2 profile has no reversible migration record")
        original = str(migration.get("original_discipline") or "")
        if not original:
            raise DisciplineMigrationError("migration record lacks original discipline")
        value["schema_version"] = "1.0.0"
        value["discipline"] = original
        value.pop("discipline_iri", None)
        value.pop("migration", None)
        return value
    raise DisciplineMigrationError(f"unknown migration direction {direction}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--direction", choices=("v1-to-v2", "v2-to-v1"), default="v1-to-v2")
    args = parser.parse_args()
    result = migrate_profile(json.loads(args.input.read_text(encoding="utf-8")), direction=args.direction)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
