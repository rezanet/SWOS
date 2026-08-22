"""Reviewed lexical-negation equivalences for deterministic risk detection.

This module is intentionally tiny and evidence-led. Entries are added only when
an explicit-negation <-> lexical-negation pair has been reviewed and covered by
a regression. Presence here means the lexical form may count as a negation
signal; it does not establish full sentence-level semantic equivalence and never
bypasses downstream semantic verification for changed prose.
"""

from __future__ import annotations

# Keep this table deliberately small. Do not infer entries from English prefixes.
REVIEWED_NEGATION_EQUIVALENCES: tuple[tuple[str, str], ...] = (("not sufficient", "insufficient"),)

REVIEWED_LEXICAL_NEGATION_TERMS: tuple[str, ...] = tuple(
    lexical for _, lexical in REVIEWED_NEGATION_EQUIVALENCES
)
