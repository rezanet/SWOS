"""Test-first contracts for shared Research Grade foundations."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from swos_runtime.models import (
    ErrorCode,
    ResourceLimitError,
    ResourceLimits,
    SWOSRuntimeError,
    artifact_identity,
    canonical_digest,
    canonical_json,
    require_version,
    stable_identifier,
    utc_timestamp,
)


class ResearchGradeFoundationTests(unittest.TestCase):
    def test_canonical_json_is_sorted_compact_unicode_and_rejects_nan(self) -> None:
        self.assertEqual(
            '{"a":[2,"é"],"z":1}',
            canonical_json({"z": 1, "a": [2, "é"]}),
        )
        with self.assertRaises(ValueError):
            canonical_json({"bad": float("nan")})

    def test_digest_is_content_stable_and_distinguishes_bytes(self) -> None:
        first = canonical_digest({"b": 2, "a": 1})
        second = canonical_digest({"a": 1, "b": 2})
        self.assertEqual(first, second)
        self.assertEqual(64, len(first))
        self.assertNotEqual(first, canonical_digest({"a": 1, "b": 3}))
        self.assertEqual(first, canonical_digest(canonical_json({"a": 1, "b": 2}).encode()))

    def test_identifiers_are_stable_and_namespaced(self) -> None:
        first = stable_identifier("rpm-event", {"scope": "p", "n": 1})
        second = stable_identifier("rpm-event", {"n": 1, "scope": "p"})
        self.assertEqual(first, second)
        self.assertRegex(first, r"^rpm-event-[0-9a-f]{32}$")
        self.assertEqual(
            "artifact-abc123",
            artifact_identity("artifact", "abc123"),
        )
        with self.assertRaises(ValueError):
            stable_identifier("", {})

    def test_timestamp_is_utc_rfc3339_with_microseconds(self) -> None:
        value = utc_timestamp()
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        self.assertEqual(timezone.utc, parsed.tzinfo)
        self.assertTrue(value.endswith("Z"))

    def test_resource_limits_are_positive_and_fail_closed(self) -> None:
        limits = ResourceLimits(max_bytes=4, max_items=2, max_depth=2)
        self.assertEqual(4, limits.max_bytes)
        limits.check_bytes(b"1234")
        limits.check_items([1, 2])
        limits.check_depth(2)
        for action in (
            lambda: limits.check_bytes(b"12345"),
            lambda: limits.check_items([1, 2, 3]),
            lambda: limits.check_depth(3),
        ):
            with self.assertRaises(ResourceLimitError):
                action()
        with self.assertRaises(ValueError):
            ResourceLimits(max_bytes=0)

    def test_typed_errors_expose_stable_code_and_details(self) -> None:
        error = SWOSRuntimeError(ErrorCode.SCOPE_REQUIRED, "scope required", details={"field": "scope"})
        self.assertEqual("scope_required", error.code)
        self.assertEqual({"field": "scope"}, error.details)
        self.assertEqual("unknown_version", ErrorCode.UNKNOWN_VERSION.value)
        with self.assertRaises(SWOSRuntimeError) as raised:
            require_version({"schema_version": "1.0.0"}, "2.0.0")
        self.assertEqual("unknown_version", raised.exception.code)


if __name__ == "__main__":
    unittest.main()
