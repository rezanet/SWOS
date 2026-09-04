"""Test-first contracts for the pre-annotation citation corpus workflow."""

from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from swos_runtime.citation_acquisition import (
    AcquisitionValidationError,
    _entry_licence_error,
    _read_text_content,
    _source_record,
    _source_semantic_assignment,
    acquire_candidates,
    canonical_source_family,
    semantic_grouped_split,
    validate_candidate_source_binding,
    validate_source_candidate_manifest,
    validate_unlabelled_candidate_pair,
)
from swos_runtime.citation_dataset import DatasetValidationError, validate_pair_record
from tools.prepare_t070_catalog import (
    MAX_ARTICLE_BYTES,
    _elsevier_entry,
    _olh_entry,
    _semantic_assignment,
    classify_elsevier,
    classify_olh,
    prepare_catalog,
)


class CitationAcquisitionTests(unittest.TestCase):
    def _source(self, *, state: str = "ADMISSIBLE_PENDING_REVIEW") -> dict:
        return {
            "source_id": "source-1",
            "doi": "10.1234/example.1",
            "stable_uri": "https://doi.org/10.1234/example.1",
            "exact_acquired_copy_uri": "file:///cache/source-1.json",
            "canonical_source_family": "doi:10.1234/example.1",
            "title": "A licensed example",
            "authors": ["Example Author"],
            "publisher": "Example Press",
            "publication_date": "2019-01-02",
            "disciplines": ["engineering"],
            "semantic_split_default": {
                "partition": "in_domain",
                "criteria_id": "T070-IN-DOMAIN-V1",
                "publication_year": 2019,
                "catalog_declared_held_out_domain": False,
            },
            "licence": {
                "spdx": "CC-BY-4.0",
                "uri": "https://creativecommons.org/licenses/by/4.0/",
                "version": "4.0",
                "article_rights_uri": "https://example.org/article-rights",
                "verification": "article_level_verified",
            },
            "attribution": "Example Author, A licensed example, Example Press",
            "acquired_at": "2026-09-03T00:00:00Z",
            "sha256": "a" * 64,
            "allowed_uses": ["candidate_generation", "human_annotation"],
            "third_party": {
                "status": "warning",
                "warning": "The source licence warns that third-party content may require permission.",
            },
            "state": state,
            "approval": {"status": "pending", "reviewer_id": None},
            "rejection_reason": None,
        }

    def _manifest(self) -> dict:
        return {
            "schema_version": "2.0.0",
            "manifest_type": "citation_support_source_candidates",
            "status": "READY_FOR_HUMAN_ANNOTATION",
            "generated_at": "2026-09-03T00:00:00Z",
            "sources": [self._source()],
            "semantic_split_policy": {
                "version": "2.0.0",
                "temporal": {
                    "criteria_id": "T070-TEMPORAL-LATER-YEAR-V1",
                    "definition": "publication_year >= 2020 and catalog_declared_held_out_domain is not true",
                    "start_year": 2020,
                },
                "ood": {
                    "criteria_id": "T070-OOD-DOMAIN-V1",
                    "definition": "catalog_declared_held_out_domain is true",
                },
            },
        }

    def _pair(
        self,
        pair_id: str,
        group_id: str,
        partition: str = "in_domain",
        *,
        source_id: str = "source-1",
        publication_year: int | None = None,
        claim_family_id: str | None = None,
    ) -> dict:
        if publication_year is None:
            publication_year = 2020 if partition == "temporal" else 2019
        claim_family_id = claim_family_id or f"family-{group_id}"
        return {
            "schema_version": "2.0.0",
            "packet_type": "citation_support_unlabelled_annotation",
            "packet_id": f"packet-{pair_id}",
            "pair_id": pair_id,
            "claim_family_id": claim_family_id,
            "group_id": group_id,
            "discipline": "engineering",
            "claim_origin": "source-authored-sentence",
            "candidate_claim": "A source-authored atomic claim.",
            "exact_quote": "A bounded source passage.",
            "context": "The surrounding source context.",
            "source_id": source_id,
            "source_uri": "https://doi.org/10.1234/example.1",
            "acquired_copy_uri": "file:///cache/source-1.json",
            "source_digest": "a" * 64,
            "licence": "CC-BY-4.0",
            "attribution": "Example Author, A licensed example, Example Press",
            "acquisition_stratum": "S1",
            "candidate_pattern_id": "A01",
            "pattern_basis": "stratum_defined",
            "semantic_split": {
                "partition": partition,
                "criteria_id": (
                    "T070-TEMPORAL-LATER-YEAR-V1"
                    if partition == "temporal"
                    else "T070-OOD-DOMAIN-V1"
                    if partition == "ood"
                    else "T070-IN-DOMAIN-V1"
                ),
                "publication_year": publication_year,
                **({"start_year": 2020} if partition == "temporal" else {}),
                "catalog_declared_held_out_domain": partition == "ood",
                **({"domain_id": "held-out-domain"} if partition == "ood" else {}),
            },
            "annotations": [
                {"annotator_id": None, "label": None, "rationale": None},
                {"annotator_id": None, "label": None, "rationale": None},
            ],
            "adjudication": {
                "status": "pending",
                "adjudicator_id": None,
                "label": None,
                "rationale": None,
            },
        }

    def test_source_candidates_are_pending_until_independent_review(self) -> None:
        indexed = validate_source_candidate_manifest(self._manifest())
        self.assertEqual(indexed["source-1"]["state"], "ADMISSIBLE_PENDING_REVIEW")

        approved = self._manifest()
        approved["sources"][0]["state"] = "APPROVED"
        approved["sources"][0]["approval"] = {
            "status": "approved",
            "reviewer_id": "reviewer-1",
        }
        with self.assertRaises(AcquisitionValidationError):
            validate_source_candidate_manifest(approved)

        unknown = self._manifest()
        unknown["sources"][0]["licence"]["spdx"] = "UNKNOWN"
        with self.assertRaises(AcquisitionValidationError):
            validate_source_candidate_manifest(unknown)

        missing_use = self._manifest()
        missing_use["sources"][0]["allowed_uses"] = ["provenance_audit"]
        with self.assertRaises(AcquisitionValidationError):
            validate_source_candidate_manifest(missing_use)

        unknown_manifest_field = self._manifest()
        unknown_manifest_field["release_approval"] = {"status": "approved"}
        with self.assertRaises(AcquisitionValidationError):
            validate_source_candidate_manifest(unknown_manifest_field)

        unknown_source_field = self._manifest()
        unknown_source_field["sources"][0]["approved"] = True
        with self.assertRaises(AcquisitionValidationError):
            validate_source_candidate_manifest(unknown_source_field)

    def test_doi_bearing_source_families_cannot_override_doi_identity(self) -> None:
        source = self._source()
        source["canonical_source_family"] = "uri:https://example.org/another-work"

        self.assertEqual(canonical_source_family(source), "doi:10.1234/example.1")
        with self.assertRaises(AcquisitionValidationError):
            validate_source_candidate_manifest({**self._manifest(), "sources": [source]})

    def test_unlabelled_validation_requires_all_reserved_human_keys(self) -> None:
        missing_annotation_key = self._pair("pair-1", "group-1")
        del missing_annotation_key["annotations"][0]["rationale"]
        with self.assertRaises(AcquisitionValidationError):
            validate_unlabelled_candidate_pair(missing_annotation_key)

        missing_adjudication_key = self._pair("pair-2", "group-2")
        del missing_adjudication_key["adjudication"]["label"]
        with self.assertRaises(AcquisitionValidationError):
            validate_unlabelled_candidate_pair(missing_adjudication_key)

    def test_unlabelled_packet_rejects_undeclared_top_level_fields(self) -> None:
        packet = self._pair("pair-extra", "group-extra")
        packet["approved"] = True
        with self.assertRaises(AcquisitionValidationError):
            validate_unlabelled_candidate_pair(packet)

        nested_extra = self._pair("pair-nested-extra", "group-nested-extra")
        nested_extra["semantic_split"]["gold_label"] = "supported"
        with self.assertRaises(AcquisitionValidationError):
            validate_unlabelled_candidate_pair(nested_extra)

    def test_packet_schema_keeps_all_human_placeholders_null(self) -> None:
        schema = json.loads(
            Path(
                "schemas/research-grade/citation-unlabelled-candidate-packet.schema.json"
            ).read_text(encoding="utf-8")
        )
        import jsonschema

        validator = jsonschema.Draft202012Validator(schema)
        mutations = (
            (
                "annotation identity",
                lambda packet: packet["annotations"][0].__setitem__("annotator_id", "ann-1"),
            ),
            (
                "annotation rationale",
                lambda packet: packet["annotations"][0].__setitem__(
                    "rationale", "directly supports"
                ),
            ),
            (
                "adjudicator identity",
                lambda packet: packet["adjudication"].__setitem__("adjudicator_id", "adj-1"),
            ),
            (
                "adjudication rationale",
                lambda packet: packet["adjudication"].__setitem__("rationale", "accepted"),
            ),
        )
        for name, mutate in mutations:
            packet = self._pair("schema-" + name.replace(" ", "-"), "schema-group")
            mutate(packet)
            self.assertTrue(list(validator.iter_errors(packet)), name)

    def test_elsevier_catalog_requires_article_level_open_access_marker(self) -> None:
        data = {
            "docId": "S0000000000000000",
            "metadata": {
                "openaccess": "No",
                "title": "An engineering article",
                "subjareas": ["ENGI"],
            },
        }
        self.assertIsNone(_elsevier_entry(data, Path("article.json"), 0))

    def test_elsevier_dataset_open_access_marker_does_not_verify_article_rights(self) -> None:
        data = {
            "docId": "S0000000000000003",
            "metadata": {
                "openaccess": "Full",
                "title": "An engineering article",
                "subjareas": ["ENGI"],
                "authors": [{"first": "Example", "last": "Author"}],
            },
        }
        entry = _elsevier_entry(data, Path("article.json"), 0)
        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertEqual(entry["licence"]["verification"], "unverified")
        error = _entry_licence_error(entry)
        self.assertIsNotNone(error)
        assert error is not None
        self.assertEqual(error[0], "REJECTED_UNRESOLVED_LICENCE")
        self.assertIn("article-level", error[1])

    def test_elsevier_arts_assignment_requires_article_level_topic_evidence(self) -> None:
        unrelated = {
            "title": "Collective strategies to cope with neonatal nursing stress in Kenya",
            "subjareas": ["ARTS", "SOCI"],
            "keywords": ["nursing", "stress", "Kenya"],
        }
        self.assertIsNone(classify_elsevier(unrelated))

        art_history = {
            "title": "Museum collections and conservation of ancient paintings",
            "subjareas": ["ARTS", "SOCI"],
            "keywords": ["heritage", "painting"],
        }
        self.assertEqual(classify_elsevier(art_history), "art_history")

    def test_generic_documentation_does_not_define_technical_writing(self) -> None:
        vaccine = {
            "title": "Documentation of vaccine handling and service delivery",
            "subjareas": ["MULT"],
            "keywords": ["Public health", "Vaccines"],
        }
        self.assertEqual(classify_elsevier(vaccine), "interdisciplinary")

        red_list = {
            "title": "Using documentation in national Red Lists",
            "subjareas": ["AGRI", "ENVI"],
            "keywords": ["forest species", "conservation"],
        }
        self.assertIsNone(classify_elsevier(red_list))

        olh_documentation = {
            "title": "The documentation of historical archives",
            "section": "Research article",
            "abstract": "This humanities study examines archival practice.",
        }
        self.assertEqual(classify_olh(olh_documentation), "humanities")

        olh_technical = {
            "title": "Technical Communication and public outreach",
            "section": "Research article",
            "abstract": "A study of technical communication practices.",
        }
        self.assertEqual(classify_olh(olh_technical), "technical_writing")

    def test_generic_ethics_does_not_define_philosophy(self) -> None:
        hydrogel = {
            "title": "Antibacterial hydrogel for wound healing",
            "subjareas": ["ENGI", "MATE", "PHYS"],
            "keywords": ["ethics", "biocompatibility"],
        }
        self.assertNotEqual(classify_elsevier(hydrogel), "philosophy")

        microneedle = {
            "title": "Microneedle drug delivery systems",
            "subjareas": ["MATE", "PHYS"],
            "keywords": ["ethics", "drug delivery"],
        }
        self.assertNotEqual(classify_elsevier(microneedle), "philosophy")

        philosophy = {
            "title": "Normative ethics and moral theory",
            "subjareas": ["ARTS"],
            "keywords": ["ethical theory"],
        }
        self.assertEqual(classify_elsevier(philosophy), "philosophy")

    def test_generic_ontology_does_not_define_philosophy(self) -> None:
        paleontology = {
            "title": "A virtual world of paleontology",
            "subjareas": ["AGRI"],
            "keywords": [],
        }
        self.assertNotEqual(classify_elsevier(paleontology), "philosophy")

        ontology_authoring = {
            "title": "Ontology authoring for scientific data integration",
            "subjareas": ["COMP"],
            "keywords": [],
        }
        self.assertNotEqual(classify_elsevier(ontology_authoring), "philosophy")

        philosophical_ontology = {
            "title": "Philosophical ontology and the structure of reality",
            "subjareas": ["ARTS"],
            "keywords": [],
        }
        self.assertEqual(classify_elsevier(philosophical_ontology), "philosophy")

    def test_catalog_discipline_assignment_records_pending_source_evidence(self) -> None:
        data = {
            "docId": "S0000000000000001",
            "metadata": {
                "openaccess": "Full",
                "title": "Museum collections and conservation of ancient paintings",
                "subjareas": ["ARTS", "SOCI"],
                "keywords": ["heritage", "painting"],
                "authors": [{"first": "Example", "last": "Author"}],
                "pub_year": 2019,
                "doi": "10.1234/example.1",
            },
        }
        entry = _elsevier_entry(data, Path("article.json"), 0)
        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertEqual(entry["disciplines"], ["art_history"])
        evidence = entry["discipline_assignment"]
        self.assertEqual(evidence["criteria_id"], "T070-DISCIPLINE-SOURCE-METADATA-V1")
        self.assertEqual(evidence["review_status"], "pending_human_review")
        self.assertEqual(evidence["evidence_fields"], ["title", "keywords", "subjareas"])
        self.assertEqual(evidence["subject_codes"], ["ARTS", "SOCI"])
        self.assertEqual(evidence["matched_subject_codes"], ["ARTS"])
        self.assertEqual(
            evidence["matched_terms"], ["conservation", "heritage", "museum", "painting"]
        )
        self.assertIn("museum", evidence["rule_terms"])
        self.assertEqual(
            evidence["matched_evidence"],
            {
                "keywords": ["heritage", "painting"],
                "subjareas": ["ARTS"],
                "title": ["conservation", "museum", "painting"],
            },
        )

    def test_discipline_evidence_uses_the_actual_classifier_predicate(self) -> None:
        psychological = {
            "docId": "S0000000000000002",
            "metadata": {
                "openaccess": "Full",
                "title": "Psychometric assessment of human memory",
                "subjareas": ["COMP"],
                "keywords": [],
                "authors": [{"first": "Example", "last": "Author"}],
                "pub_year": 2019,
                "doi": "10.1234/example.2",
            },
        }
        entry = _elsevier_entry(psychological, Path("psychological.json"), 0)
        self.assertIsNotNone(entry)
        assert entry is not None
        evidence = entry["discipline_assignment"]
        self.assertEqual(entry["disciplines"], ["psychology"])
        self.assertIn("psych", evidence["rule_terms"])
        self.assertEqual(evidence["matched_terms"], ["psych"])
        self.assertEqual(evidence["matched_evidence"]["title"], ["psych"])

        olh = {
            "pk": 5678,
            "license": {"short_name": "CC BY 4.0"},
            "galleys": [{"type": "xml", "path": "https://example.org/5678.xml"}],
            "frozenauthors": [{"first_name": "Example", "last_name": "Author"}],
            "title": "Collections and public memory",
            "section": "Research article",
            "abstract": "A study of museum collections.",
            "date_published": "2019-01-02",
        }
        with tempfile.TemporaryDirectory() as directory:
            content = Path(directory) / "collections.xml"
            content.write_text(
                '<article><front><article-meta><article-id pub-id-type="doi">'
                "10.16995/olh.5678</article-id></article-meta></front>"
                "<body><p>Article prose with enough words for candidates.</p></body></article>",
                encoding="utf-8",
            )
            olh_entry = _olh_entry(olh, content, 0)

            self.assertIsNotNone(olh_entry)
            assert olh_entry is not None
            olh_evidence = olh_entry["discipline_assignment"]
            self.assertEqual(olh_entry["disciplines"], ["art_history"])
            self.assertNotIn("collections", olh_evidence["rule_terms"])
            self.assertEqual(olh_evidence["matched_terms"], ["museum"])
            self.assertNotIn("title", olh_evidence["matched_evidence"])

    def test_generic_collections_does_not_define_olh_art_history(self) -> None:
        article = {
            "title": "Collections and public memory",
            "section": "Research article",
            "abstract": "A study of public memory and political humor.",
        }
        self.assertEqual(classify_olh(article), "humanities")

    def test_olh_classifier_matches_curator_terms_at_word_boundaries(self) -> None:
        ordinary = {
            "title": "Accurate methods for reliable evidence",
            "section": "Research article",
            "abstract": "Accurate measurements support reproducible conclusions.",
        }
        self.assertNotEqual(classify_olh(ordinary), "art_history")

        curator = {
            "title": "Curatorial practice in public museums",
            "section": "Research article",
            "abstract": "Curatorial work documents the history of collections.",
        }
        self.assertEqual(classify_olh(curator), "art_history")

    def test_catalog_rejects_sources_without_real_authors(self) -> None:
        elsevier = {
            "docId": "S0000000000000010",
            "metadata": {
                "openaccess": "Full",
                "title": "Engineering methods and reliable systems",
                "subjareas": ["ENGI"],
                "keywords": ["engineering"],
                "authors": [],
            },
        }
        self.assertIsNone(_elsevier_entry(elsevier, Path("missing-authors.json"), 0))

        olh = {
            "pk": 9010,
            "license": {"short_name": "CC BY 4.0"},
            "galleys": [{"type": "xml", "path": "https://example.org/9010.xml"}],
            "frozenauthors": [],
            "authors": [],
            "title": "A humanities source",
            "date_published": "2019-01-02",
        }
        self.assertIsNone(_olh_entry(olh, Path("missing-authors.xml"), 0))

    def test_rejected_source_does_not_invent_article_rights_uri(self) -> None:
        entry = {
            "source_id": "elsevier-unresolved",
            "doi": "10.1234/unresolved",
            "stable_uri": "https://doi.org/10.1234/unresolved",
            "content_uri": "file:///cache/unresolved.json",
            "title": "Unresolved rights",
            "authors": ["Example Author"],
            "publisher": "Example Press",
            "publication_date": "2019-01-02",
            "disciplines": ["engineering"],
            "licence": {
                "spdx": "UNKNOWN",
                "uri": "https://spdx.org/licenses/NOASSERTION.html",
                "version": "unspecified",
                "article_rights_uri": "",
                "verification": "unverified",
            },
            "attribution": "Example Author, Unresolved rights, Example Press",
            "allowed_uses": [],
            "third_party": {"status": "unknown", "warning": "Review rights."},
        }
        record = _source_record(
            entry,
            state="REJECTED_UNRESOLVED_LICENCE",
            acquired_uri=None,
            digest=None,
            reason="article-level rights URI is missing",
        )
        self.assertEqual(record["licence"]["article_rights_uri"], "")

        rejected = self._manifest()
        rejected_source = rejected["sources"][0]
        rejected_source["state"] = "REJECTED_UNRESOLVED_LICENCE"
        rejected_source["approval"] = {"status": "not_requested", "reviewer_id": None}
        rejected_source["rejection_reason"] = "article-level rights URI is missing"
        rejected_source["authors"] = []
        rejected_source["attribution"] = ""
        rejected_source["licence"]["spdx"] = "UNKNOWN"
        rejected_source["licence"]["article_rights_uri"] = ""
        rejected_source["licence"]["verification"] = "unverified"
        indexed = validate_source_candidate_manifest(rejected)
        self.assertEqual(indexed["source-1"]["state"], "REJECTED_UNRESOLVED_LICENCE")

        rejected_source["authors"] = ["Example Author"]
        rejected_source["attribution"] = "Example Author, A licensed example, Example Press"
        schema = json.loads(
            Path("schemas/research-grade/citation-source-candidate.schema.json").read_text(
                encoding="utf-8"
            )
        )
        import jsonschema

        self.assertEqual(list(jsonschema.Draft202012Validator(schema).iter_errors(rejected)), [])

    def test_candidate_binding_rejects_discipline_and_semantic_split_tampering(self) -> None:
        indexed = validate_source_candidate_manifest(self._manifest())

        wrong_discipline = self._pair("pair-discipline", "group-discipline")
        wrong_discipline["discipline"] = "technical_writing"
        with self.assertRaises(AcquisitionValidationError):
            validate_candidate_source_binding(wrong_discipline, indexed)

        wrong_split = self._pair("pair-split", "group-split")
        wrong_split["semantic_split"] = {
            "partition": "temporal",
            "criteria_id": "T070-TEMPORAL-LATER-YEAR-V1",
            "publication_year": 2020,
            "start_year": 2020,
            "catalog_declared_held_out_domain": False,
        }
        with self.assertRaises(AcquisitionValidationError):
            validate_candidate_source_binding(wrong_split, indexed)

    def test_source_partition_binding_recomputes_from_metadata_and_declared_domain(self) -> None:
        later_metadata = self._manifest()
        later_metadata["sources"][0]["publication_date"] = "2026-01-01"
        with self.assertRaises(AcquisitionValidationError):
            validate_source_candidate_manifest(later_metadata)

        wrong_ood_domain = self._manifest()
        source = wrong_ood_domain["sources"][0]
        source["disciplines"] = ["psychology"]
        source["semantic_split_default"] = {
            "partition": "ood",
            "criteria_id": "T070-OOD-DOMAIN-V1",
            "catalog_declared_held_out_domain": True,
            "domain_id": "technical-writing-held-out-v1",
        }
        with self.assertRaises(AcquisitionValidationError):
            validate_source_candidate_manifest(wrong_ood_domain)

    def test_source_manifest_requires_all_nested_and_digest_keys(self) -> None:
        mutations = (
            ("doi", lambda source: source.pop("doi")),
            ("sha256", lambda source: source.pop("sha256")),
            (
                "article rights",
                lambda source: source["licence"].pop("article_rights_uri"),
            ),
            ("approval reviewer", lambda source: source["approval"].pop("reviewer_id")),
            ("third-party warning", lambda source: source["third_party"].pop("warning")),
        )
        for name, mutate in mutations:
            with self.subTest(name=name):
                manifest = self._manifest()
                mutate(manifest["sources"][0])
                with self.assertRaises(AcquisitionValidationError):
                    validate_source_candidate_manifest(manifest)

    def test_existing_olh_cache_is_reacquired_for_the_current_galley_uri(self) -> None:
        article = {
            "pk": 9011,
            "license": {"short_name": "CC BY 4.0"},
            "galleys": [{"type": "xml", "path": "https://example.org/current.xml"}],
            "frozenauthors": [{"first_name": "Example", "last_name": "Author"}],
            "title": "An ordinary humanities source",
            "date_published": "2019-01-02",
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "elsevier.zip"
            with zipfile.ZipFile(archive, "w") as outer:
                nested_path = root / "json-articals.zip"
                with zipfile.ZipFile(nested_path, "w"):
                    pass
                outer.write(nested_path, "json-articals.zip")
            cache = root / "cache"
            stale = cache / "olh-xml" / "9011.xml"
            stale.parent.mkdir(parents=True)
            stale.write_text("stale bytes", encoding="utf-8")

            def write_current(_url: str, path: Path, *, max_bytes: int) -> None:
                self.assertEqual(max_bytes, MAX_ARTICLE_BYTES)
                path.write_text("current bytes", encoding="utf-8")

            # Re-run with the digest patched to the archive's actual bytes.
            from tools import prepare_t070_catalog

            actual_digest = prepare_t070_catalog._sha256(archive)
            with (
                patch("tools.prepare_t070_catalog._discover_olh", return_value=[article]),
                patch(
                    "tools.prepare_t070_catalog._download", side_effect=write_current
                ) as download,
                patch("tools.prepare_t070_catalog.ELSEVIER_ARCHIVE_SHA256", actual_digest),
            ):
                prepare_catalog(
                    archive,
                    cache,
                    root / "catalog.json",
                    per_discipline=1,
                    olh_per_discipline=1,
                )
            download.assert_called_once_with(
                "https://example.org/current.xml", stale, max_bytes=MAX_ARTICLE_BYTES
            )
            self.assertEqual(stale.read_text(encoding="utf-8"), "current bytes")

    def test_ood_domain_assignment_is_not_an_ordinal_bucket(self) -> None:
        self.assertEqual(_semantic_assignment(2019, "technical_writing", 1)["partition"], "ood")
        self.assertEqual(_semantic_assignment(2025, "technical_writing", 2)["partition"], "ood")
        self.assertEqual(_semantic_assignment(2025, "engineering", 1)["partition"], "temporal")

    def test_olh_catalog_preserves_every_named_author(self) -> None:
        article = {
            "pk": 1234,
            "license": {"short_name": "CC BY 4.0"},
            "galleys": [{"type": "xml", "path": "https://example.org/1234.xml"}],
            "frozenauthors": [
                {"first_name": "Ada", "last_name": "Lovelace"},
                {"given_name": "Grace", "family_name": "Hopper"},
                "Katherine Johnson",
            ],
            "date_published": "2022-01-02",
            "title": "A source with complete attribution",
        }

        with tempfile.TemporaryDirectory() as directory:
            content = Path(directory) / "article.xml"
            content.write_text(
                '<article><front><article-meta><article-id pub-id-type="doi">'
                "10.16995/olh.1234</article-id></article-meta></front>"
                "<body><p>Article prose with enough words for candidates.</p></body></article>",
                encoding="utf-8",
            )
            entry = _olh_entry(article, content, 0)

            self.assertIsNotNone(entry)
            assert entry is not None
            self.assertEqual(
                entry["authors"], ["Ada Lovelace", "Grace Hopper", "Katherine Johnson"]
            )
            self.assertIn("Ada Lovelace", entry["attribution"])
            self.assertIn("Grace Hopper", entry["attribution"])
            self.assertIn("Katherine Johnson", entry["attribution"])
            evidence = entry["discipline_assignment"]
            self.assertEqual(evidence["evidence_fields"], ["title", "section", "abstract"])
            self.assertIn("history", evidence["rule_terms"])
            self.assertEqual(evidence["matched_terms"], [])
            self.assertEqual(evidence["fallback_basis"], "official_olh_humanities_scope")

    def test_olh_entry_uses_doi_declared_in_acquired_xml(self) -> None:
        article = {
            "pk": 4432,
            "license": {"short_name": "CC BY 4.0"},
            "galleys": [{"type": "xml", "path": "https://example.org/4432.xml"}],
            "frozenauthors": [{"first_name": "Example", "last_name": "Author"}],
            "date_published": "2022-01-02",
            "title": "A source with a declared DOI",
        }
        with tempfile.TemporaryDirectory() as directory:
            content = Path(directory) / "article.xml"
            content.write_text(
                "<article><front><article-meta>"
                '<article-id pub-id-type="doi">10.16995/olh.80</article-id>'
                "</article-meta></front><body><p>Article prose with enough words for candidates.</p>"
                "</body></article>",
                encoding="utf-8",
            )

            entry = _olh_entry(article, content, 0)

        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertEqual(entry["doi"], "10.16995/olh.80")

    def test_jats_text_extraction_excludes_front_and_back_matter(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            content = Path(directory) / "article.xml"
            content.write_text(
                "<article><front><article-meta><article-title>Front metadata title</article-title>"
                "<permissions><copyright-statement>Copyright notice</copyright-statement>"
                "</permissions></article-meta></front>"
                "<body><p>The eligible article body contains a bounded scholarly claim here.</p>"
                "</body><back><ref-list><ref>Back matter reference text.</ref></ref-list></back></article>",
                encoding="utf-8",
            )

            text = _read_text_content(content)

        self.assertIn("eligible article body", text)
        self.assertNotIn("Front metadata title", text)
        self.assertNotIn("Copyright notice", text)
        self.assertNotIn("Back matter reference text", text)

    def test_jats_without_eligible_abstract_or_body_has_no_extractable_prose(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            content = Path(directory) / "metadata-only.xml"
            content.write_text(
                "<article><front><article-meta><article-title>Metadata only</article-title>"
                "</article-meta></front><back><ref-list><ref>Reference only.</ref>"
                "</ref-list></back></article>",
                encoding="utf-8",
            )

            text = _read_text_content(content)

        self.assertEqual(text, "")

    def test_jats_block_elements_remain_separate_prose_sentences(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            content = Path(directory) / "adjacent-paragraphs.xml"
            content.write_text(
                "<article><body><p>First bounded article sentence here.</p>"
                "<p>Second bounded article sentence here.</p></body></article>",
                encoding="utf-8",
            )

            text = _read_text_content(content)

        self.assertEqual(
            text, "First bounded article sentence here. Second bounded article sentence here."
        )

    def test_jats_section_titles_are_not_source_authored_prose(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            content = Path(directory) / "section-title.xml"
            content.write_text(
                "<article><body><sec><title>Introduction</title>"
                "<p>First bounded article sentence here.</p></sec></body></article>",
                encoding="utf-8",
            )

            text = _read_text_content(content)

        self.assertEqual(text, "First bounded article sentence here.")

    def test_olh_curatorial_terms_require_an_art_specific_context(self) -> None:
        generic_curation = {
            "title": "Four Theses on Algorithmic Folklore",
            "abstract": (
                "The paper studies content curation in algorithmic systems and treats "
                "art as a broad social category."
            ),
            "section": "Automation",
        }
        art_curation = {
            "title": "Curatorial practice in a museum collection",
            "abstract": "The article examines visual art and museum interpretation.",
            "section": "Art history",
        }

        self.assertNotEqual(classify_olh(generic_curation), "art_history")
        self.assertEqual(classify_olh(art_curation), "art_history")

    def test_packet_schema_encodes_partition_specific_semantic_requirements(self) -> None:
        schema = json.loads(
            Path(
                "schemas/research-grade/citation-unlabelled-candidate-packet.schema.json"
            ).read_text(encoding="utf-8")
        )
        import jsonschema

        validator = jsonschema.Draft202012Validator(schema)

        valid_undated = self._pair("schema-undated", "schema-undated")
        valid_undated["semantic_split"]["publication_year"] = None
        self.assertEqual(list(validator.iter_errors(valid_undated)), [])

        incomplete_in_domain = self._pair("schema-incomplete", "schema-incomplete")
        incomplete_in_domain["semantic_split"].pop("publication_year")
        incomplete_in_domain["semantic_split"].pop("catalog_declared_held_out_domain")
        self.assertTrue(list(validator.iter_errors(incomplete_in_domain)))

        missing_temporal_domain_flag = self._pair(
            "schema-temporal-domain-flag", "schema-temporal-domain-flag", "temporal"
        )
        missing_temporal_domain_flag["semantic_split"].pop("catalog_declared_held_out_domain")
        self.assertTrue(list(validator.iter_errors(missing_temporal_domain_flag)))

        temporal = self._pair("schema-temporal", "schema-temporal", "temporal")
        temporal["semantic_split"].pop("publication_year")
        self.assertTrue(list(validator.iter_errors(temporal)))

        in_domain = self._pair("schema-in-domain", "schema-in-domain")
        in_domain["semantic_split"]["publication_year"] = 2020
        self.assertTrue(list(validator.iter_errors(in_domain)))

        ood = self._pair("schema-ood", "schema-ood", "ood", publication_year=2025)
        ood["semantic_split"]["catalog_declared_held_out_domain"] = False
        self.assertTrue(list(validator.iter_errors(ood)))

    def test_pending_source_schema_forbids_a_reviewer_identity(self) -> None:
        schema = json.loads(
            Path("schemas/research-grade/citation-source-candidate.schema.json").read_text(
                encoding="utf-8"
            )
        )
        import jsonschema

        candidate = self._manifest()
        candidate["sources"][0]["approval"]["reviewer_id"] = "reviewer-1"
        errors = list(jsonschema.Draft202012Validator(schema).iter_errors(candidate))
        self.assertTrue(any(list(error.absolute_path)[-1:] == ["reviewer_id"] for error in errors))

    def test_source_schema_allows_missing_rejected_attribution_only(self) -> None:
        schema = json.loads(
            Path("schemas/research-grade/citation-source-candidate.schema.json").read_text(
                encoding="utf-8"
            )
        )
        import jsonschema

        validator = jsonschema.Draft202012Validator(schema)
        rejected = self._source(state="REJECTED_UNRESOLVED_LICENCE")
        rejected["attribution"] = ""
        rejected["approval"] = {"status": "not_requested", "reviewer_id": None}
        rejected["rejection_reason"] = "Article-level licence evidence is unresolved."
        rejected_manifest = {**self._manifest(), "sources": [rejected]}
        self.assertEqual(list(validator.iter_errors(rejected_manifest)), [])

        admissible = self._source()
        admissible["attribution"] = ""
        admissible_manifest = {**self._manifest(), "sources": [admissible]}
        self.assertTrue(list(validator.iter_errors(admissible_manifest)))

    def test_candidate_schema_has_valid_source_level_rights_condition(self) -> None:
        schema = json.loads(
            Path("schemas/research-grade/citation-source-candidate.schema.json").read_text(
                encoding="utf-8"
            )
        )
        import jsonschema

        jsonschema.Draft202012Validator.check_schema(schema)
        candidate = self._manifest()
        candidate["sources"][0]["licence"]["article_rights_uri"] = ""
        errors = list(jsonschema.Draft202012Validator(schema).iter_errors(candidate))
        self.assertTrue(
            any(list(error.absolute_path)[-1:] == ["article_rights_uri"] for error in errors)
        )

    def test_candidate_schema_enforces_the_admissible_source_contract(self) -> None:
        schema = json.loads(
            Path("schemas/research-grade/citation-source-candidate.schema.json").read_text(
                encoding="utf-8"
            )
        )
        import jsonschema

        mutations = (
            ("authors", lambda source: source.__setitem__("authors", [])),
            ("exact copy", lambda source: source.__setitem__("exact_acquired_copy_uri", None)),
            ("digest", lambda source: source.__setitem__("sha256", None)),
            ("allowed uses", lambda source: source.__setitem__("allowed_uses", [])),
            ("approval", lambda source: source["approval"].__setitem__("status", "not_requested")),
            ("semantic assignment", lambda source: source.pop("semantic_split_default")),
            (
                "article rights",
                lambda source: source["licence"].__setitem__("article_rights_uri", ""),
            ),
            (
                "rights verification",
                lambda source: source["licence"].__setitem__("verification", "unverified"),
            ),
        )
        for name, mutate in mutations:
            candidate = self._manifest()
            mutate(candidate["sources"][0])
            errors = list(jsonschema.Draft202012Validator(schema).iter_errors(candidate))
            self.assertTrue(errors, name)

    def test_candidate_span_collisions_are_rejected_and_backfilled(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            content = root / "source.json"
            content.write_text(
                json.dumps(
                    {
                        "title": "A source",
                        "publication_date": "2019-01-02",
                        "text": (
                            "Short claim with five words. "
                            "The established design provides reliable evidence across several engineering contexts. "
                            "Contextual analysis records independent sources and measured outcomes for the system. "
                            "The baseline method reports calibrated measurements from multiple independent engineering sources. "
                            "A contrary analysis does not provide reliable evidence for the proposed design. "
                            "The established design provides reliable evidence across several engineering contexts with additional validation."
                        ),
                    }
                ),
                encoding="utf-8",
            )
            catalog = root / "catalog.json"
            catalog.write_text(
                json.dumps(
                    {
                        "schema_version": "2.0.0",
                        "catalog_type": "citation_source_candidate_catalog",
                        "sources": [
                            {
                                "source_id": "source-1",
                                "doi": "10.1234/example.1",
                                "stable_uri": "https://doi.org/10.1234/example.1",
                                "content_uri": content.as_uri(),
                                "title": "A source",
                                "authors": ["Example Author"],
                                "publisher": "Example Press",
                                "publication_date": "2019-01-02",
                                "disciplines": ["engineering"],
                                "licence": {
                                    "spdx": "CC-BY-4.0",
                                    "uri": "https://creativecommons.org/licenses/by/4.0/",
                                    "version": "4.0",
                                    "article_rights_uri": "https://example.org/rights",
                                    "verification": "article_level_verified",
                                },
                                "attribution": "Example Author, A source, Example Press",
                                "allowed_uses": ["candidate_generation", "human_annotation"],
                                "third_party": {
                                    "status": "warning",
                                    "warning": "Review third-party content.",
                                },
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            report = acquire_candidates(catalog, root / "output", max_pairs=5)
            rows = [
                json.loads(line)
                for line in (root / "output" / "unlabelled-candidate-pairs.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]

            self.assertEqual(report["status"], "READY_FOR_HUMAN_ANNOTATION")
            self.assertEqual(report["candidate_families_rejected_for_span_collision"], 1)
            self.assertEqual(len(rows), 5)
            self.assertEqual(
                len(
                    {(row["source_id"], row["candidate_claim"], row["exact_quote"]) for row in rows}
                ),
                5,
            )
            self.assertNotIn(
                "Short claim with five words.", {row["candidate_claim"] for row in rows}
            )

    def test_temporal_policy_uses_a_frozen_later_window_with_ood_precedence(self) -> None:
        policy = self._manifest()["semantic_split_policy"]

        older = self._source()
        older.pop("semantic_split_default")
        older["publication_date"] = "2019-12-31"
        self.assertEqual(_source_semantic_assignment(older, policy)["partition"], "in_domain")

        later = self._source()
        later.pop("semantic_split_default")
        later["publication_date"] = "2020-01-01"
        self.assertEqual(_source_semantic_assignment(later, policy)["partition"], "temporal")

        held_out = self._source()
        held_out.pop("semantic_split_default")
        held_out["publication_date"] = "2024-01-01"
        held_out["catalog_declared_held_out_domain"] = True
        held_out["held_out_domain_id"] = "declared-ood-v1"
        self.assertEqual(_source_semantic_assignment(held_out, policy)["partition"], "ood")

        conflicting = dict(held_out)
        conflicting["semantic_split"] = {
            "partition": "temporal",
            "criteria_id": "T070-TEMPORAL-LATER-YEAR-V1",
        }
        with self.assertRaises(AcquisitionValidationError):
            _source_semantic_assignment(conflicting, policy)

        missing_temporal_domain_flag = self._pair(
            "runtime-temporal-domain-flag", "runtime-temporal-domain-flag", "temporal"
        )
        missing_temporal_domain_flag["semantic_split"].pop("catalog_declared_held_out_domain")
        with self.assertRaises(AcquisitionValidationError):
            validate_unlabelled_candidate_pair(missing_temporal_domain_flag, policy=policy)

    def test_temporal_cutoff_change_requires_a_policy_version_change(self) -> None:
        policy = self._manifest()["semantic_split_policy"]
        changed_boundary = deepcopy(policy)
        changed_boundary["temporal"]["start_year"] = 2019
        with self.assertRaises(AcquisitionValidationError):
            semantic_grouped_split(
                [self._pair("p-policy", "g-policy")],
                policy=changed_boundary,
            )

    def test_unlabelled_packet_has_blank_human_fields_and_hides_intent(self) -> None:
        packet = self._pair("p-1", "g-1")
        validate_unlabelled_candidate_pair(packet)

        labelled = self._pair("p-2", "g-2")
        labelled["label"] = "directly_supports"
        with self.assertRaises(AcquisitionValidationError):
            validate_unlabelled_candidate_pair(labelled)

        retrieval_intent = self._pair("p-3", "g-3")
        retrieval_intent["retrieval_intent"] = "direct"
        with self.assertRaises(AcquisitionValidationError):
            validate_unlabelled_candidate_pair(retrieval_intent)

        filled = self._pair("p-4", "g-4")
        filled["annotations"][0]["label"] = "directly_supports"
        with self.assertRaises(AcquisitionValidationError):
            validate_unlabelled_candidate_pair(filled)

    def test_candidate_source_binding_includes_exact_copy_and_pending_state(self) -> None:
        packet = self._pair("p-bound", "g-bound")
        indexed = validate_source_candidate_manifest(self._manifest())
        validate_candidate_source_binding(packet, indexed)

        wrong_copy = dict(packet)
        wrong_copy["acquired_copy_uri"] = "file:///cache/other.json"
        with self.assertRaises(AcquisitionValidationError):
            validate_candidate_source_binding(wrong_copy, indexed)

    def test_final_adjudicated_validator_still_rejects_candidate_packets(self) -> None:
        with self.assertRaises(DatasetValidationError):
            validate_pair_record(self._pair("still-unlabelled", "g-final-boundary"))

    def test_semantic_split_rejects_hash_only_assignment_and_keeps_groups_isolated(self) -> None:
        rows = [
            self._pair("p-in-1", "g-in", "in_domain"),
            self._pair("p-in-2", "g-in", "in_domain"),
            self._pair("p-temporal", "g-temporal", "temporal", source_id="source-temporal"),
            self._pair("p-ood", "g-ood", "ood", source_id="source-ood", publication_year=2024),
        ]
        policy = self._manifest()["semantic_split_policy"]
        splits = semantic_grouped_split(rows, policy=policy, seed=7)
        self.assertEqual(
            {row["semantic_split"]["partition"] for row in splits["temporal"]}, {"temporal"}
        )
        self.assertEqual({row["semantic_split"]["partition"] for row in splits["ood"]}, {"ood"})
        for split in ("train", "calibration", "locked_test"):
            self.assertNotIn("source-temporal", {row["source_id"] for row in splits[split]})
            self.assertNotIn("source-ood", {row["source_id"] for row in splits[split]})
        locations = {row["group_id"]: split for split, values in splits.items() for row in values}
        self.assertEqual(locations["g-in"], "train")
        self.assertNotIn("g-in", {row["group_id"] for row in splits["locked_test"]})

        hash_only = self._pair("p-hash", "g-hash", "in_domain")
        hash_only["semantic_split"] = {
            "partition": "temporal",
            "criteria_id": "HASH_BUCKET",
            "bucket": 3,
        }
        with self.assertRaises(AcquisitionValidationError):
            semantic_grouped_split([hash_only], policy=policy, seed=7)

        hash_ood = self._pair(
            "p-hash-ood", "g-hash-ood", "ood", source_id="source-hash-ood", publication_year=2024
        )
        hash_ood["semantic_split"]["bucket"] = 3
        with self.assertRaises(AcquisitionValidationError):
            semantic_grouped_split([hash_ood], policy=policy, seed=7)

    def test_canonical_source_and_claim_families_cannot_cross_final_partitions(self) -> None:
        source_crossing = [
            self._pair("p-source-old", "g-source-old", source_id="source-shared"),
            self._pair(
                "p-source-new",
                "g-source-new",
                "temporal",
                source_id="source-shared",
            ),
        ]
        with self.assertRaises(AcquisitionValidationError):
            semantic_grouped_split(
                source_crossing, policy=self._manifest()["semantic_split_policy"]
            )

        claim_crossing = [
            self._pair("p-claim-old", "g-claim-old", source_id="source-claim-old"),
            self._pair(
                "p-claim-new",
                "g-claim-new",
                "temporal",
                source_id="source-claim-new",
                claim_family_id="family-g-claim-old",
            ),
        ]
        with self.assertRaises(AcquisitionValidationError):
            semantic_grouped_split(claim_crossing, policy=self._manifest()["semantic_split_policy"])

        same_source_in_domain = [
            self._pair("p-source-train", "g-source-train", source_id="source-one"),
            self._pair("p-source-cal", "g-source-cal", source_id="source-one"),
        ]
        splits = semantic_grouped_split(
            same_source_in_domain, policy=self._manifest()["semantic_split_policy"], seed=11
        )
        locations = {
            split
            for split, values in splits.items()
            for row in values
            if row["source_id"] == "source-one"
        }
        self.assertEqual(len(locations), 1)

    def test_acquisition_reuses_an_immutable_copy_and_writes_a_reproducible_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            content = root / "source.json"
            content.write_text(
                json.dumps(
                    {
                        "title": "A source",
                        "publication_date": "2019-01-02",
                        "text": (
                            "This direct statement provides reliable evidence across several engineering contexts. "
                            "Contextual analysis records independent sources and measured outcomes for the system. "
                            "The baseline method reports calibrated measurements from multiple independent engineering sources. "
                            "A contrary analysis does not provide reliable evidence for the proposed design. "
                            "This direct statement provides reliable evidence across several engineering contexts with additional validation."
                        ),
                    }
                ),
                encoding="utf-8",
            )
            catalog = root / "catalog.json"
            catalog.write_text(
                json.dumps(
                    {
                        "schema_version": "2.0.0",
                        "catalog_type": "citation_source_candidate_catalog",
                        "sources": [
                            {
                                "source_id": "source-1",
                                "doi": "10.1234/example.1",
                                "stable_uri": "https://doi.org/10.1234/example.1",
                                "content_uri": content.as_uri(),
                                "title": "A source",
                                "authors": ["Example Author"],
                                "publisher": "Example Press",
                                "publication_date": "2019-01-02",
                                "disciplines": ["engineering"],
                                "licence": {
                                    "spdx": "CC-BY-4.0",
                                    "uri": "https://creativecommons.org/licenses/by/4.0/",
                                    "version": "4.0",
                                    "article_rights_uri": "https://example.org/rights",
                                    "verification": "article_level_verified",
                                },
                                "attribution": "Example Author, A source, Example Press",
                                "allowed_uses": ["candidate_generation", "human_annotation"],
                                "third_party": {
                                    "status": "warning",
                                    "warning": "Review third-party content.",
                                },
                                "semantic_split": {
                                    "partition": "in_domain",
                                    "criteria_id": "T070-IN-DOMAIN-V1",
                                },
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            output = root / "output"
            first = acquire_candidates(catalog, output, max_pairs=5)
            second = acquire_candidates(catalog, output, max_pairs=5)

            self.assertEqual(first["status"], "READY_FOR_HUMAN_ANNOTATION")
            self.assertEqual(second["reused_sources"], 1)
            self.assertEqual(first["candidate_pairs"], second["candidate_pairs"])
            self.assertEqual(first["output_digests"], second["output_digests"])
            output_files = (
                output / "source-candidate-manifest.json",
                output / "unlabelled-candidate-pairs.jsonl",
                output / "acquisition-report.json",
            )
            for output_file in output_files:
                self.assertTrue(output_file.is_file())
                self.assertNotIn(b"\r\n", output_file.read_bytes())

            limited = acquire_candidates(catalog, output, max_pairs=5, max_bytes=10)
            self.assertEqual(limited["status"], "ACQUISITION_INCOMPLETE")
            self.assertEqual(limited["candidate_pairs"], 0)

    def test_acquisition_revalidates_a_local_source_when_the_uri_bytes_change(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            content = root / "source.json"
            sentences = (
                "This original statement provides reliable evidence across several engineering contexts. "
                "Contextual analysis records independent sources and measured outcomes for the system. "
                "The baseline method reports calibrated measurements from multiple independent engineering sources. "
                "A contrary analysis does not provide reliable evidence for the proposed design. "
                "This original statement provides reliable evidence across several engineering contexts with validation."
            )
            content.write_text(json.dumps({"text": sentences}), encoding="utf-8")
            catalog = root / "catalog.json"
            catalog.write_text(
                json.dumps(
                    {
                        "schema_version": "2.0.0",
                        "catalog_type": "citation_source_candidate_catalog",
                        "sources": [
                            {
                                "source_id": "source-1",
                                "doi": "10.1234/example.1",
                                "stable_uri": "https://doi.org/10.1234/example.1",
                                "content_uri": content.as_uri(),
                                "title": "A source",
                                "authors": ["Example Author"],
                                "publisher": "Example Press",
                                "publication_date": "2019-01-02",
                                "disciplines": ["engineering"],
                                "licence": {
                                    "spdx": "CC-BY-4.0",
                                    "uri": "https://creativecommons.org/licenses/by/4.0/",
                                    "version": "4.0",
                                    "article_rights_uri": "https://example.org/rights",
                                    "verification": "article_level_verified",
                                },
                                "attribution": "Example Author, A source, Example Press",
                                "allowed_uses": ["candidate_generation", "human_annotation"],
                                "third_party": {
                                    "status": "warning",
                                    "warning": "Review third-party content.",
                                },
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            output = root / "output"
            first = acquire_candidates(catalog, output, max_pairs=5)

            content.write_text(
                json.dumps({"text": sentences.replace("original", "revised")}),
                encoding="utf-8",
            )
            second = acquire_candidates(catalog, output, max_pairs=5)

            self.assertEqual(first["downloaded_sources"], 1)
            self.assertEqual(second["reused_sources"], 0)
            self.assertEqual(second["downloaded_sources"], 1)
            self.assertNotEqual(first["output_digests"], second["output_digests"])


if __name__ == "__main__":
    unittest.main()
