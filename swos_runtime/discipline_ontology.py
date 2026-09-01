"""Offline, versioned discipline ontology registry.

The reviewed Turtle files are the source of semantic identity.  Production
code consumes the compiled JSON profile and never requires an RDF engine; this
module deliberately keeps the small validation surface deterministic.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from .models import canonical_digest

ONTOLOGY_VERSION = "2.0.0"
ONTOLOGY_IRI = "https://swos.example.org/ontology/discipline/2.0.0"
DISCIPLINE_IRI_BASE = "https://swos.example.org/discipline/"
SUPPORTED_DISCIPLINES = (
    "art_history",
    "art_criticism",
    "engineering",
    "humanities",
    "interdisciplinary",
    "materials_science",
    "philosophy",
    "psychology",
    "technical_writing",
)
V1_ONLY_DISCIPLINES = frozenset({"enterprise_reporting"})


class OntologyError(ValueError):
    """Base error for malformed or unavailable ontology releases."""


class OntologyVersionError(OntologyError):
    """Raised when a release is unknown or unsupported."""


class PackValidationError(OntologyError):
    """Raised when a pack cannot satisfy closed-world validation."""


class NoDisciplineFallbackError(PackValidationError):
    """Raised instead of silently substituting another discipline."""


@dataclass(frozen=True)
class OntologyRelease:
    ontology_id: str
    version: str
    version_iri: str
    source_digest: str
    shape_digest: str
    context_digest: str
    compiled_digest: str
    supported_packs: tuple[str, ...]
    deprecated: bool = False
    deprecation_date: str | None = None
    replacement: str | None = None
    compatibility: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ontology_id": self.ontology_id,
            "version": self.version,
            "version_iri": self.version_iri,
            "source_digest": self.source_digest,
            "shape_digest": self.shape_digest,
            "context_digest": self.context_digest,
            "compiled_digest": self.compiled_digest,
            "supported_packs": list(self.supported_packs),
            "deprecated": self.deprecated,
            "deprecation_date": self.deprecation_date,
            "replacement": self.replacement,
            "compatibility": dict(self.compatibility),
        }


@dataclass(frozen=True)
class DisciplineProfile:
    discipline: str
    discipline_iri: str
    pack_id: str
    pack_version: str
    pack_digest: str
    ontology_digest: str
    ontology_path: str
    human_pack_path: str
    methods: tuple[dict[str, Any], ...]
    evidence_types: tuple[dict[str, Any], ...]
    proof_standards: tuple[dict[str, Any], ...]
    required_criteria: tuple[dict[str, Any], ...]
    failure_modes: tuple[dict[str, Any], ...]
    source_roles: tuple[dict[str, Any], ...]
    diversity_dimensions: tuple[dict[str, Any], ...]
    mappings: tuple[dict[str, Any], ...]
    deprecation: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "discipline": self.discipline,
            "discipline_iri": self.discipline_iri,
            "pack_id": self.pack_id,
            "pack_version": self.pack_version,
            "pack_digest": self.pack_digest,
            "ontology_digest": self.ontology_digest,
            "ontology_path": self.ontology_path,
            "human_pack_path": self.human_pack_path,
            "methods": list(self.methods),
            "evidence_types": list(self.evidence_types),
            "proof_standards": list(self.proof_standards),
            "required_criteria": list(self.required_criteria),
            "failure_modes": list(self.failure_modes),
            "source_roles": list(self.source_roles),
            "diversity_dimensions": list(self.diversity_dimensions),
            "mappings": list(self.mappings),
            "deprecation": dict(self.deprecation),
        }


@dataclass(frozen=True)
class PackValidationReport:
    valid: bool
    path: str
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    graph_digest: str = ""
    concepts: int = 0
    criteria: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "path": self.path,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "graph_digest": self.graph_digest,
            "concepts": self.concepts,
            "criteria": self.criteria,
        }


_PREFIX = re.compile(r"^\s*@prefix\s+([\w-]+):\s*<([^>]+)>\s*\.\s*$", re.I)
_TRIPLE = re.compile(
    r"^\s*(?P<s><[^>]+>|[\w-]+:[\w.-]+)\s+"
    r"(?P<p><[^>]+>|[\w-]+:[\w.-]+|a)\s+"
    r"(?P<o>\"(?:[^\"\\]|\\.)*\"(?:@[A-Za-z-]+|\^\^<[^>]+>)?|<[^>]+>|[\w-]+:[\w.-]+|[\w.-]+)\s*$"
)
_PREDICATE_OBJECT = re.compile(
    r"^\s*(?P<p><[^>]+>|[\w-]+:[\w.-]+|a)\s+"
    r"(?P<o>\"(?:[^\"\\]|\\.)*\"(?:@[A-Za-z-]+|\^\^<[^>]+>)?|<[^>]+>|[\w-]+:[\w.-]+|[\w.-]+)\s*$"
)


def parse_turtle(text: str) -> tuple[tuple[str, str, str], ...]:
    """Parse the conservative Turtle subset used by reviewed pack sources."""

    prefixes: dict[str, str] = {}
    triples: list[tuple[str, str, str]] = []
    for raw in text.splitlines():
        # A hash inside an IRI (notably the standard SKOS namespace) is data,
        # while a hash outside an IRI starts a Turtle comment.
        line = raw.strip() if raw.strip().startswith("@prefix") else raw.split("#", 1)[0].strip()
        if not line:
            continue
        prefix = _PREFIX.match(line)
        if prefix:
            prefixes[prefix.group(1)] = prefix.group(2)
            continue
        if not line.endswith("."):
            raise PackValidationError(f"unsupported Turtle statement: {raw.strip()}")
        segments = [segment.strip() for segment in line[:-1].strip().split(";") if segment.strip()]
        match = _TRIPLE.match(segments[0]) if segments else None
        if not match:
            raise PackValidationError(f"unsupported Turtle statement: {raw.strip()}")

        def expand(value: str) -> str:
            if value == "a":
                return "rdf:type"
            if value.startswith("<"):
                return value[1:-1]
            if value.startswith('"'):
                return value
            if ":" in value:
                prefix_name, local = value.split(":", 1)
                if prefix_name in prefixes:
                    return prefixes[prefix_name] + local
            return value

        subject = expand(match.group("s"))
        triples.append((subject, expand(match.group("p")), expand(match.group("o"))))
        for segment in segments[1:]:
            continuation = _PREDICATE_OBJECT.match(segment)
            if not continuation:
                raise PackValidationError(f"unsupported Turtle statement: {raw.strip()}")
            triples.append((subject, expand(continuation.group("p")), expand(continuation.group("o"))))
    return tuple(sorted(triples))


def _validate_structured_pack(data: Mapping[str, Any], path: Path) -> PackValidationReport:
    errors: list[str] = []
    concepts = list(data.get("concepts") or [])
    criteria = list(data.get("criteria") or [])
    notations: dict[str, str] = {}
    iris: set[str] = set()
    for concept in concepts:
        if not isinstance(concept, Mapping):
            errors.append("concept must be an object")
            continue
        iri = str(concept.get("iri") or "")
        notation = str(concept.get("notation") or "")
        if iri in iris and iri:
            errors.append(f"duplicate IRI: {iri}")
        if notation in notations and notation:
            errors.append(f"duplicate notation: {notation}")
        if iri:
            iris.add(iri)
        if notation:
            notations[notation] = iri
        for broader in concept.get("broader") or []:
            if broader not in {item.get("iri") for item in concepts if isinstance(item, Mapping)}:
                errors.append(f"dangling broader IRI: {broader}")
    graph = {str(item.get("iri")): set(item.get("broader") or []) for item in concepts if isinstance(item, Mapping)}
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            errors.append(f"hierarchy cycle at {node}")
            return
        if node in visited:
            return
        visiting.add(node)
        for parent in graph.get(node, set()):
            visit(parent)
        visiting.remove(node)
        visited.add(node)

    for node in graph:
        visit(node)
    for criterion in criteria:
        if not isinstance(criterion, Mapping):
            errors.append("criterion must be an object")
            continue
        weight = criterion.get("weight")
        if not isinstance(weight, (int, float)) or not 0 < float(weight) <= 1:
            errors.append(f"invalid weight for {criterion.get('iri', '<unknown>')}")
    graph_digest = canonical_digest(data)
    return PackValidationReport(
        valid=not errors,
        path=str(path),
        errors=tuple(dict.fromkeys(errors)),
        graph_digest=graph_digest,
        concepts=len(concepts),
        criteria=len(criteria),
    )


class DisciplineOntologyRegistry:
    """Load one immutable offline ontology release and its pack profiles."""

    def __init__(self) -> None:
        self.root: Path | None = None
        self.manifest: dict[str, Any] = {}
        self.release: OntologyRelease | None = None
        self.compatibility: dict[str, Any] = {}
        self._profiles: dict[str, DisciplineProfile] = {}

    def load(self, release_manifest: Path | str | Mapping[str, Any]) -> "DisciplineOntologyRegistry":
        if isinstance(release_manifest, Mapping):
            manifest = dict(release_manifest)
            root = Path.cwd()
        else:
            manifest_path = Path(release_manifest)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            # Manifest paths are repository-relative so the same release can
            # be loaded from the checkout or from an audit-pack extraction.
            root = manifest_path.parent.parent
        version = str(manifest.get("version") or manifest.get("ontology_version") or "")
        if version != ONTOLOGY_VERSION:
            raise OntologyVersionError(f"unsupported ontology version {version or '<missing>'}; no fallback is permitted")
        entries = list(manifest.get("packs") or [])
        if len(entries) != len(SUPPORTED_DISCIPLINES):
            raise PackValidationError("manifest must contain exactly nine discipline packs")
        seen: set[str] = set()
        profiles: dict[str, DisciplineProfile] = {}
        for entry in entries:
            if not isinstance(entry, Mapping):
                raise PackValidationError("pack entry must be an object")
            discipline = str(entry.get("discipline") or "")
            if discipline not in SUPPORTED_DISCIPLINES:
                raise PackValidationError(f"unsupported v2 discipline {discipline or '<missing>'}")
            if discipline in seen:
                raise PackValidationError(f"duplicate discipline mapping: {discipline}")
            seen.add(discipline)
            expected_iri = f"{DISCIPLINE_IRI_BASE}{discipline}"
            if str(entry.get("discipline_iri")) != expected_iri:
                raise PackValidationError(f"stable IRI mismatch for {discipline}")
            ontology_path = str(entry.get("ontology_path") or "")
            path = root / ontology_path
            if not path.is_file():
                raise PackValidationError(f"missing ontology pack: {path}")
            report = self.validate_pack(path)
            if not report.valid:
                raise PackValidationError("; ".join(report.errors))
            profiles[discipline] = DisciplineProfile(
                discipline=discipline,
                discipline_iri=expected_iri,
                pack_id=str(entry.get("pack_id") or f"swos-discipline-{discipline}"),
                pack_version=str(entry.get("pack_version") or "1.0.0"),
                pack_digest=canonical_digest(entry),
                ontology_digest=report.graph_digest,
                ontology_path=ontology_path,
                human_pack_path=str(entry.get("human_pack_path") or ""),
                methods=tuple(dict(item) for item in entry.get("methods") or []),
                evidence_types=tuple(dict(item) for item in entry.get("evidence_types") or []),
                proof_standards=tuple(dict(item) for item in entry.get("proof_standards") or []),
                required_criteria=tuple(dict(item) for item in entry.get("criteria") or []),
                failure_modes=tuple(dict(item) for item in entry.get("failure_modes") or []),
                source_roles=tuple(dict(item) for item in entry.get("source_roles") or []),
                diversity_dimensions=tuple(dict(item) for item in entry.get("diversity_dimensions") or []),
                mappings=tuple(dict(item) for item in entry.get("mappings") or []),
                deprecation=dict(entry.get("deprecation") or {}),
            )
        if seen != set(SUPPORTED_DISCIPLINES):
            raise PackValidationError("manifest does not map all nine supported disciplines exactly once")
        release_data = dict(manifest.get("release") or {})
        self.root = root
        self.manifest = manifest
        self.compatibility = dict(manifest.get("compatibility") or {})
        self.release = OntologyRelease(
            ontology_id=str(release_data.get("ontology_id") or "swos-discipline-ontology"),
            version=version,
            version_iri=str(release_data.get("version_iri") or ONTOLOGY_IRI),
            source_digest=str(release_data.get("source_digest") or canonical_digest(manifest)),
            shape_digest=str(release_data.get("shape_digest") or "unrecorded"),
            context_digest=str(release_data.get("context_digest") or "unrecorded"),
            compiled_digest=str(release_data.get("compiled_digest") or "uncompiled"),
            supported_packs=tuple(sorted(seen)),
            deprecated=bool(release_data.get("deprecated", False)),
            deprecation_date=release_data.get("deprecation_date"),
            replacement=release_data.get("replacement"),
            compatibility=self.compatibility,
        )
        self._profiles = profiles
        return self

    def disciplines(self) -> tuple[str, ...]:
        return tuple(sorted(self._profiles))

    def profile(self, discipline_iri: str) -> DisciplineProfile:
        key = str(discipline_iri)
        if key.startswith(DISCIPLINE_IRI_BASE):
            key = key.removeprefix(DISCIPLINE_IRI_BASE)
        if key in V1_ONLY_DISCIPLINES:
            raise NoDisciplineFallbackError(
                "enterprise_reporting is v1-only; migrate to an approved v2 discipline explicitly"
            )
        try:
            return self._profiles[key]
        except KeyError as exc:
            raise NoDisciplineFallbackError(f"no v2 discipline pack for {discipline_iri}; no fallback is permitted") from exc

    def compiled_profile(self, discipline_iri: str) -> dict[str, Any]:
        profile = self.profile(discipline_iri)
        if self.root is not None:
            entry = next(item for item in self.manifest["packs"] if item["discipline"] == profile.discipline)
            path = self.root / str(entry.get("compiled_path") or "")
            if path.is_file():
                return json.loads(path.read_text(encoding="utf-8"))
        return profile.to_dict()

    def validate_pack(self, pack_path: Path | str) -> PackValidationReport:
        path = Path(pack_path)
        try:
            if path.suffix.lower() == ".json":
                data = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(data, Mapping):
                    raise PackValidationError("pack JSON must be an object")
                report = _validate_structured_pack(data, path)
            else:
                triples = parse_turtle(path.read_text(encoding="utf-8"))
                subjects = {subject for subject, _, _ in triples}
                errors: list[str] = []
                if len(triples) != len(set(triples)):
                    errors.append("duplicate RDF statement")
                for subject, predicate, obj in triples:
                    if predicate.endswith("broader") and obj not in subjects:
                        errors.append(f"dangling broader IRI: {obj}")
                report = PackValidationReport(
                    valid=not errors,
                    path=str(path),
                    errors=tuple(dict.fromkeys(errors)),
                    graph_digest=canonical_digest(triples),
                    concepts=sum(1 for _, predicate, _ in triples if predicate.endswith("prefLabel")),
                    criteria=sum(1 for _, predicate, _ in triples if predicate.endswith("requiresCriterion")),
                )
        except (OSError, json.JSONDecodeError, PackValidationError) as exc:
            if isinstance(exc, PackValidationError):
                raise
            raise PackValidationError(f"cannot validate {path}: {exc}") from exc
        if not report.valid:
            raise PackValidationError("; ".join(report.errors))
        return report

    def migrate_v1_discipline(self, discipline: str) -> str:
        value = str(discipline)
        if value in V1_ONLY_DISCIPLINES:
            # The migration is intentionally reversible metadata-wise: callers
            # retain the original v1 value and must choose a v2 target.
            return value
        self.profile(value)
        return value


def _iri_for_method(value: Any, profile: DisciplineProfile) -> str:
    text = str(value)
    for method in profile.methods:
        if text in {str(method.get("iri")), str(method.get("label"))}:
            return str(method.get("iri"))
    return text if text.startswith("http://") or text.startswith("https://") else ""


def bind_research_plan(plan: Mapping[str, Any], profile: DisciplineProfile) -> dict[str, Any]:
    """Attach immutable ontology identities to a plan without changing its meaning."""

    bound = dict(plan)
    methods = list(plan.get("methods") or [])
    bound["discipline"] = profile.discipline
    bound["discipline_iri"] = profile.discipline_iri
    bound["ontology_version"] = "2.0.0"
    bound["ontology_digest"] = profile.ontology_digest
    bound["method_iris"] = [iri for value in methods if (iri := _iri_for_method(value, profile))]
    bound["criterion_iris"] = [str(item.get("iri")) for item in profile.required_criteria]
    return bound


def bind_evidence_matrix(matrix: Mapping[str, Any], profile: DisciplineProfile) -> dict[str, Any]:
    """Bind every Evidence Matrix row to the profile used to assess it."""

    bound = dict(matrix)
    bound["discipline"] = profile.discipline
    bound["discipline_iri"] = profile.discipline_iri
    bound["ontology_version"] = "2.0.0"
    bound["ontology_digest"] = profile.ontology_digest
    rows: list[dict[str, Any]] = []
    known = {str(item.get("iri")) for item in profile.required_criteria}
    for raw in matrix.get("rows", []):
        row = dict(raw)
        criterion = row.get("criterion_iri")
        if criterion is not None and str(criterion) not in known:
            row["ontology_binding_error"] = "criterion is not declared by the selected pack"
        row["discipline_iri"] = profile.discipline_iri
        row["ontology_digest"] = profile.ontology_digest
        rows.append(row)
    bound["rows"] = rows
    return bound
