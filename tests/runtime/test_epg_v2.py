"""EPG v2 model and schema contract tests."""

from __future__ import annotations

import unittest

from swos_runtime.prov_interop import epg_to_prov, prov_to_epg
from swos_runtime.prov_model import EPG_VERSION


def sample_epg() -> dict:
    return {
        "schema_version": EPG_VERSION,
        "profile": "swos.prov-dm-round-trip.v2",
        "base_iri": "https://example.org/prov/",
        "namespaces": {"ex": "https://example.org/"},
        "scope": {"work_id": "work-1"},
        "entities": {
            "https://example.org/e1": {
                "type": "entity",
                "attributes": {
                    "label": {"value": "A", "datatype": "http://www.w3.org/2001/XMLSchema#string"},
                    "count": {"value": "2", "datatype": "http://www.w3.org/2001/XMLSchema#integer"},
                },
            }
        },
        "activities": {"https://example.org/a1": {"type": "activity", "attributes": {}}},
        "agents": {"https://example.org/ag1": {"type": "agent", "attributes": {}}},
        "relations": [
            {"type": "wasGeneratedBy", "entity": "https://example.org/e1", "activity": "https://example.org/a1"},
            {"type": "wasAssociatedWith", "activity": "https://example.org/a1", "agent": "https://example.org/ag1"},
        ],
        "bundles": {
            "https://example.org/b1": {
                "statements": [{"type": "entity", "id": "https://example.org/e1"}]
            }
        },
        "extensions": [
            {
                "subject": "https://example.org/e1",
                "predicate": "https://swos.dev/prov#custom",
                "object": "7",
                "object_type": "literal",
                "datatype": "http://www.w3.org/2001/XMLSchema#integer",
            }
        ],
        "integrity": {"source_digest": "a" * 64},
    }


class EpgV2Tests(unittest.TestCase):
    def test_epg_v2_roundtrip_preserves_qualified_relations_typed_literals_and_extensions(self) -> None:
        epg = sample_epg()
        document = epg_to_prov(epg, base_iri=epg["base_iri"])
        converted = prov_to_epg(document, profile=epg["profile"])
        self.assertEqual(EPG_VERSION, converted["schema_version"])
        self.assertEqual(epg["bundles"], converted["bundles"])
        self.assertEqual(epg["extensions"], converted["extensions"])
        self.assertEqual(epg["entities"]["https://example.org/e1"]["attributes"], converted["entities"]["https://example.org/e1"]["attributes"])

    def test_absolute_namespace_policy_rejects_relative_ids(self) -> None:
        epg = sample_epg()
        epg["entities"] = {"relative": {"type": "entity", "attributes": {}}}
        with self.assertRaises(ValueError):
            epg_to_prov(epg, base_iri=epg["base_iri"])


if __name__ == "__main__":
    unittest.main()
