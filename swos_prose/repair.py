"""Fail-closed bounded local repair for SWOS Prose Milestone 1."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Callable, Protocol

from .models import (
    DeltaType,
    RepairAttempt,
    SemanticDelta,
    Severity,
    VerificationResult,
    VerificationStatus,
)
from .providers.rewrite_base import RewriteCandidate

MAX_REPAIR_ATTEMPTS = 2
MIN_LOCALISATION_CONFIDENCE = 0.95
MAX_REPAIR_SPAN_CHARS = 96
MAX_REPAIR_SPAN_TOKENS = 4

REPAIRABLE_DELTA_TYPES = frozenset(
    {
        DeltaType.MODALITY_STRENGTHENED,
        DeltaType.MODALITY_WEAKENED,
        DeltaType.QUANTIFIER_CHANGED,
        DeltaType.ATTRIBUTION_CHANGED,
        DeltaType.NEGATION_CHANGED,
        DeltaType.CAUSAL_STRENGTH_CHANGED,
    }
)
HARD_INVARIANT_DELTA_TYPES = frozenset(
    {
        DeltaType.NUMBER_CHANGED,
        DeltaType.DATE_CHANGED,
        DeltaType.UNIT_CHANGED,
        DeltaType.QUOTATION_CHANGED,
        DeltaType.CITATION_REMOVED,
        DeltaType.CITATION_RELOCATED,
    }
)
_TOKEN_RE = re.compile(r"[A-Za-z0-9]+(?:['’.-][A-Za-z0-9]+)*|[^\w\s]", re.UNICODE)
_CLAUSE_BOUNDARY_RE = re.compile(r"[,;:]|\b(?:and|but|while|whereas|although|though)\b", re.I)
_AUX_NOT_RE = re.compile(
    r"\b(?:do|does|did|is|are|was|were|has|have|had|can|could|may|might|must|shall|should|will|would)\s+not\b",
    re.I,
)
_NEGATIVE_PREFIX_RE = re.compile(r"\b(?:un|in|im|ir|il|dis|non)[A-Za-z]{3,}\b", re.I)
_NOT_PREFIX_RE = re.compile(r"\bnot\s+(?:un|in|im|ir|il|dis|non)[A-Za-z]{3,}\b", re.I)
_WEAK_MODAL_MARKERS = frozenset({"may", "might", "could", "possibly", "perhaps"})
_QUANTIFIER_MARKERS = frozenset(
    {"none", "few", "some", "many", "most", "all", "sometimes", "often", "always"}
)
_NEGATION_AUXILIARIES = frozenset(
    {
        "do",
        "does",
        "did",
        "is",
        "are",
        "was",
        "were",
        "has",
        "have",
        "had",
        "can",
        "could",
        "may",
        "might",
        "must",
        "shall",
        "should",
        "will",
        "would",
    }
)
_MODAL_FINITE_CARRIERS = frozenset({"do", "does", "did"})
_ANAPHORIC_ALL_RE = re.compile(r"\ball\s+of\s+(?:which|whom|them|these|those)\b", re.I)
_SIMPLE_ASSOC_RE = re.compile(
    r"^\s*(?P<subject>.+?)\s+(?:is|are|was|were)\s+"
    r"(?:associated\s+with|correlated\s+with|linked\s+to|related\s+to)\s+"
    r"(?P<object>.+?)\s*[.!?]?\s*$",
    re.I,
)
_SIMPLE_CAUSAL_RE = re.compile(
    r"^\s*(?P<subject>.+?)\s+"
    r"(?:(?:is|are|was|were)\s+)?"
    r"(?:caused\s+by|causes?|caused|leads?\s+to|led\s+to|results?\s+in|resulted\s+in|"
    r"produces?|produced|drives?|drove|determines?|determined)\s+"
    r"(?P<object>.+?)\s*[.!?]?\s*$",
    re.I,
)


@dataclass(frozen=True)
class RepairSpan:
    source_start: int
    source_end: int
    candidate_start: int
    candidate_end: int
    confidence: float


@dataclass(frozen=True)
class LexicalEdit:
    """The sole non-equal token opcode between source and candidate."""

    source_tokens: tuple[str, ...]
    candidate_tokens: tuple[str, ...]


@dataclass
class RepairExecution:
    candidate: str
    verification: VerificationResult
    attempts: list[RepairAttempt]
    success: bool
    failure_reason: str | None = None
    verifier_call_count: int = 0
    verifier_token_usage: dict[str, int] | None = None
    verifier_cost_estimate: float | None = None


class RepairProvider(Protocol):
    def repair(
        self,
        *,
        prompt: str,
        source: str,
        candidate: str,
        delta: SemanticDelta,
        candidate_start: int,
        candidate_end: int,
    ) -> RewriteCandidate: ...


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _add_usage(total: dict[str, int], usage: dict[str, int] | None) -> None:
    if not usage:
        return
    for key, value in usage.items():
        if isinstance(value, int):
            total[key] = total.get(key, 0) + value


def _cost_total(values: list[float | None]) -> float | None:
    if not values:
        return 0.0
    if any(value is None for value in values):
        return None
    return round(sum(float(value) for value in values), 10)


def _tokens(text: str) -> list[tuple[str, int, int]]:
    return [(m.group(0), m.start(), m.end()) for m in _TOKEN_RE.finditer(text)]


def _bounded(text: str) -> bool:
    return (
        len(text) <= MAX_REPAIR_SPAN_CHARS
        and len(_TOKEN_RE.findall(text)) <= MAX_REPAIR_SPAN_TOKENS
    )


def _unique(text: str, marker: str | None) -> tuple[int, int] | None:
    if not marker:
        return None
    for candidate_marker in (marker, marker.strip().strip(".,;:!?()[]{}\"'“”‘’")):
        if not candidate_marker:
            continue
        folded_text, folded_marker = text.casefold(), candidate_marker.casefold()
        start = folded_text.find(folded_marker)
        if start >= 0 and folded_text.find(folded_marker, start + 1) < 0:
            return start, start + len(candidate_marker)
    return None


def _surface_marker(delta: SemanticDelta, span: str | None) -> str | None:
    if span is None:
        return None
    if delta.delta_type is DeltaType.ATTRIBUTION_CHANGED and "::" in span:
        if "," in span:
            return None
        return span.rsplit("::", 1)[1].strip() or None
    return span


def _valid_offsets(text: str, start: int | None, end: int | None, expected: str | None) -> bool:
    return bool(
        start is not None
        and end is not None
        and 0 <= start <= end <= len(text)
        and (expected is None or text[start:end] == expected)
    )


def _token_range(
    tokens: list[tuple[str, int, int]], start: int, end: int
) -> tuple[int, int] | None:
    indexes = [i for i, (_, a, b) in enumerate(tokens) if b > start and a < end]
    return (indexes[0], indexes[-1] + 1) if indexes else None


def _single_lexical_edit(source: str, candidate: str) -> LexicalEdit | None:
    """Return exactly one changed token opcode; any second edit blocks M1 repair."""
    left = _tokens(source)
    right = _tokens(candidate)
    matcher = SequenceMatcher(
        a=[token.casefold() for token, _, _ in left],
        b=[token.casefold() for token, _, _ in right],
        autojunk=False,
    )
    edits = [opcode for opcode in matcher.get_opcodes() if opcode[0] != "equal"]
    if len(edits) != 1:
        return None
    _, i1, i2, j1, j2 = edits[0]
    if i2 - i1 > MAX_REPAIR_SPAN_TOKENS or j2 - j1 > MAX_REPAIR_SPAN_TOKENS:
        return None
    return LexicalEdit(
        source_tokens=tuple(token.casefold() for token, _, _ in left[i1:i2]),
        candidate_tokens=tuple(token.casefold() for token, _, _ in right[j1:j2]),
    )


def _inflection_variants(word: str) -> set[str]:
    """Return a deliberately small set of grammatical carrier variants."""
    value = word.casefold()
    variants = {value, value + "s", value + "es", value + "ed"}
    if value.endswith("e"):
        variants.add(value + "d")
    if len(value) > 1 and value.endswith("y"):
        variants.add(value[:-1] + "ies")
        variants.add(value[:-1] + "ied")
    return variants


def _same_lexeme(left: str, right: str) -> bool:
    return right.casefold() in _inflection_variants(
        left
    ) or left.casefold() in _inflection_variants(right)


def _aligned_span(source: str, candidate: str, source_marker: tuple[int, int]) -> RepairSpan | None:
    left, right = _tokens(source), _tokens(candidate)
    marker_range = _token_range(left, *source_marker)
    if marker_range is None:
        return None
    mi1, mi2 = marker_range
    matches = []
    matcher = SequenceMatcher(
        a=[t[0].casefold() for t in left], b=[t[0].casefold() for t in right], autojunk=False
    )
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag != "equal" and i1 <= mi1 and mi2 <= i2:
            matches.append((i1, i2, j1, j2))
    if len(matches) != 1:
        return None
    i1, i2, j1, j2 = matches[0]
    if i2 - i1 > MAX_REPAIR_SPAN_TOKENS or j2 - j1 > MAX_REPAIR_SPAN_TOKENS:
        return None

    if j1 == j2:
        if j2 < len(right) and i2 < len(left) and left[i2][0].casefold() == right[j2][0].casefold():
            i2 += 1
            j2 += 1
        elif j1 > 0 and i1 > 0 and left[i1 - 1][0].casefold() == right[j1 - 1][0].casefold():
            i1 -= 1
            j1 -= 1
        else:
            return None
    if i1 >= i2 or j1 >= j2:
        return None

    span = RepairSpan(left[i1][1], left[i2 - 1][2], right[j1][1], right[j2 - 1][2], 0.97)
    if not _bounded(source[span.source_start : span.source_end]) or not _bounded(
        candidate[span.candidate_start : span.candidate_end]
    ):
        return None
    return span


def locate_span(source: str, candidate: str, delta: SemanticDelta) -> RepairSpan | None:
    """Return one high-confidence bounded replacement window, otherwise None."""
    if _valid_offsets(
        source, delta.source_start, delta.source_end, delta.source_span
    ) and _valid_offsets(
        candidate, delta.candidate_start, delta.candidate_end, delta.candidate_span
    ):
        left = source[delta.source_start : delta.source_end]
        right = candidate[delta.candidate_start : delta.candidate_end]
        if _bounded(left) and _bounded(right):
            return RepairSpan(
                delta.source_start,
                delta.source_end,
                delta.candidate_start,
                delta.candidate_end,
                1.0,
            )

    source_match = _unique(source, _surface_marker(delta, delta.source_span))
    candidate_match = _unique(candidate, _surface_marker(delta, delta.candidate_span))
    if source_match is None:
        return None

    aligned = _aligned_span(source, candidate, source_match)
    if aligned is not None and (
        candidate_match is None
        or (
            aligned.candidate_start <= candidate_match[0]
            and candidate_match[1] <= aligned.candidate_end
        )
    ):
        return aligned

    if candidate_match is not None:
        left, right = source[slice(*source_match)], candidate[slice(*candidate_match)]
        if _bounded(left) and _bounded(right):
            return RepairSpan(*source_match, *candidate_match, 1.0)
    return None


def _single_clause(text: str) -> bool:
    stripped = text.strip()
    core = stripped[:-1] if stripped.endswith((".", "!", "?")) else stripped
    return _CLAUSE_BOUNDARY_RE.search(core) is None and re.search(r"[.!?]", core) is None


def _single_marker(span: str | None, vocabulary: frozenset[str]) -> str | None:
    if span is None or "," in span:
        return None
    value = " ".join(span.casefold().split()).strip(" .,:;!?")
    return value if value in vocabulary else None


def _negative_prefix_tokens(text: str) -> tuple[str, ...]:
    return tuple(sorted(match.group(0).casefold() for match in _NEGATIVE_PREFIX_RE.finditer(text)))


def _modal_edit_only(edit: LexicalEdit, delta: SemanticDelta) -> bool:
    if delta.delta_type not in {DeltaType.MODALITY_STRENGTHENED, DeltaType.MODALITY_WEAKENED}:
        return False
    source_modals = [token for token in edit.source_tokens if token in _WEAK_MODAL_MARKERS]
    candidate_modals = [token for token in edit.candidate_tokens if token in _WEAK_MODAL_MARKERS]
    if delta.delta_type is DeltaType.MODALITY_STRENGTHENED:
        if len(source_modals) != 1 or candidate_modals:
            return False
    elif source_modals or len(candidate_modals) != 1:
        return False
    source_rest = [token for token in edit.source_tokens if token not in _WEAK_MODAL_MARKERS]
    candidate_rest = [token for token in edit.candidate_tokens if token not in _WEAK_MODAL_MARKERS]
    if delta.delta_type is DeltaType.MODALITY_STRENGTHENED and not source_rest:
        return not candidate_rest or (
            len(candidate_rest) == 1 and candidate_rest[0] in _MODAL_FINITE_CARRIERS
        )
    if delta.delta_type is DeltaType.MODALITY_WEAKENED and not candidate_rest:
        return not source_rest or (
            len(source_rest) == 1 and source_rest[0] in _MODAL_FINITE_CARRIERS
        )
    if len(source_rest) == 1 and len(candidate_rest) == 1:
        return _same_lexeme(source_rest[0], candidate_rest[0])
    return False


def _quantifier_edit_only(edit: LexicalEdit, source_marker: str) -> bool:
    if edit.source_tokens != (source_marker,):
        return False
    return not edit.candidate_tokens or (
        len(edit.candidate_tokens) == 1 and edit.candidate_tokens[0] in _QUANTIFIER_MARKERS
    )


def _attribution_edit_only(edit: LexicalEdit, source_act: str, candidate_act: str) -> bool:
    return edit.source_tokens == (source_act,) and edit.candidate_tokens == (candidate_act,)


def _negation_content(tokens: tuple[str, ...]) -> tuple[int, tuple[str, ...]]:
    not_count = sum(1 for token in tokens if token == "not")
    content = tuple(
        token for token in tokens if token != "not" and token not in _NEGATION_AUXILIARIES
    )
    return not_count, content


def _negation_edit_only(edit: LexicalEdit) -> bool:
    source_not, source_content = _negation_content(edit.source_tokens)
    candidate_not, candidate_content = _negation_content(edit.candidate_tokens)
    if {source_not, candidate_not} != {0, 1}:
        return False
    if len(source_content) > 1 or len(candidate_content) > 1:
        return False
    if source_content and candidate_content:
        return _same_lexeme(source_content[0], candidate_content[0])
    return not source_content and not candidate_content


def _same_simple_relation_roles(source: str, candidate: str) -> bool:
    if not _single_clause(source) or not _single_clause(candidate):
        return False
    left = _SIMPLE_ASSOC_RE.match(source)
    right = _SIMPLE_CAUSAL_RE.match(candidate)
    if left is None or right is None:
        return False

    def normalise(value: str) -> str:
        return " ".join(value.casefold().split()).strip(" .,:;!?")

    return normalise(left.group("subject")) == normalise(right.group("subject")) and normalise(
        left.group("object")
    ) == normalise(right.group("object"))


def _causal_edit_only(source: str, candidate: str, edit: LexicalEdit) -> bool:
    if not _same_simple_relation_roles(source, candidate):
        return False
    source_surface = " ".join(edit.source_tokens)
    candidate_surface = " ".join(edit.candidate_tokens)
    return any(
        marker in source_surface for marker in ("associated", "correlated", "linked", "related")
    ) and any(
        marker in candidate_surface
        for marker in (
            "cause",
            "causes",
            "caused",
            "leads",
            "lead",
            "led",
            "results",
            "resulted",
            "produces",
            "produced",
            "drives",
            "drove",
            "determines",
            "determined",
        )
    )


def _reviewed_repair_shape(source: str, candidate: str, delta: SemanticDelta) -> bool:
    """Return whether M1 explicitly authorises this lexical repair shape.

    Repair eligibility requires exactly one token-level edit and that edit must be
    entirely explained by the reviewed semantic-force family. A bounded diff is
    not, by itself, evidence that a change is lexical-only.
    """
    if delta.delta_type in HARD_INVARIANT_DELTA_TYPES:
        return False
    if not _single_clause(source) or not _single_clause(candidate):
        return False
    edit = _single_lexical_edit(source, candidate)
    if edit is None:
        return False

    if delta.delta_type in {DeltaType.MODALITY_STRENGTHENED, DeltaType.MODALITY_WEAKENED}:
        marker_span = (
            delta.source_span
            if delta.delta_type is DeltaType.MODALITY_STRENGTHENED
            else delta.candidate_span
        )
        return (
            _single_marker(marker_span, _WEAK_MODAL_MARKERS) is not None
            and "explicit weak modal" in delta.explanation.casefold()
            and _modal_edit_only(edit, delta)
        )

    if delta.delta_type is DeltaType.QUANTIFIER_CHANGED:
        if _ANAPHORIC_ALL_RE.search(candidate):
            return False
        source_marker = _single_marker(delta.source_span, _QUANTIFIER_MARKERS)
        candidate_marker = _single_marker(delta.candidate_span, _QUANTIFIER_MARKERS)
        return bool(
            source_marker is not None
            and (candidate_marker is None or candidate_marker != source_marker)
            and _quantifier_edit_only(edit, source_marker)
        )

    if delta.delta_type is DeltaType.ATTRIBUTION_CHANGED:
        left, right = delta.source_span, delta.candidate_span
        if (
            not left
            or not right
            or "," in left
            or "," in right
            or "::" not in left
            or "::" not in right
        ):
            return False
        left_agent, left_act = (part.strip().casefold() for part in left.split("::", 1))
        right_agent, right_act = (part.strip().casefold() for part in right.split("::", 1))
        return bool(
            left_agent
            and left_act
            and left_agent == right_agent
            and left_act != right_act
            and _attribution_edit_only(edit, left_act, right_act)
        )

    if delta.delta_type is DeltaType.NEGATION_CHANGED:
        source_aux = len(_AUX_NOT_RE.findall(source))
        candidate_aux = len(_AUX_NOT_RE.findall(candidate))
        if {source_aux, candidate_aux} != {0, 1}:
            return False
        if _NOT_PREFIX_RE.search(source) or _NOT_PREFIX_RE.search(candidate):
            return False
        if _negative_prefix_tokens(source) != _negative_prefix_tokens(candidate):
            return False
        return _negation_edit_only(edit)

    if delta.delta_type is DeltaType.CAUSAL_STRENGTH_CHANGED:
        return _causal_edit_only(source, candidate, edit)

    return False


def annotate_local_repairability(
    source: str, candidate: str, deltas: list[SemanticDelta]
) -> list[SemanticDelta]:
    """Authorise only reviewed lexical delta shapes with >=95% localisation."""
    result: list[SemanticDelta] = []
    for delta in deltas:
        if delta.delta_type not in REPAIRABLE_DELTA_TYPES or not _reviewed_repair_shape(
            source, candidate, delta
        ):
            result.append(replace(delta, repairable=False))
            continue
        span = locate_span(source, candidate, delta)
        if span is None or span.confidence < MIN_LOCALISATION_CONFIDENCE:
            result.append(replace(delta, repairable=False))
            continue
        result.append(
            replace(
                delta,
                source_span=source[span.source_start : span.source_end],
                candidate_span=candidate[span.candidate_start : span.candidate_end],
                source_start=span.source_start,
                source_end=span.source_end,
                candidate_start=span.candidate_start,
                candidate_end=span.candidate_end,
                severity=Severity.BLOCKER,
                repairable=True,
            )
        )
    return result


def render_repair_prompt(
    *, source: str, candidate: str, delta: SemanticDelta, offending_span: str
) -> str:
    return f'''You are a semantic-safe editor. The following text has a single, localised defect.

Source (original):
{source}

Candidate (your previous rewrite):
{candidate}

Defect:
{delta.explanation}

Offending span in candidate:
"{offending_span}"

Task:
Replace ONLY the offending span with a corrected version that resolves the defect.
Do NOT change anything else in the candidate.
Do NOT add new claims, citations, examples, or evidence.
Do NOT rephrase the surrounding context.

Return ONLY the full corrected candidate text.'''


def _confined_middle(candidate: str, repaired: str, start: int, end: int) -> str | None:
    prefix, suffix = candidate[:start], candidate[end:]
    if not repaired.startswith(prefix) or (suffix and not repaired.endswith(suffix)):
        return None
    middle_end = len(repaired) - len(suffix) if suffix else len(repaired)
    middle = repaired[len(prefix) : middle_end]
    if middle == candidate[start:end]:
        return None
    if (
        len(middle) > MAX_REPAIR_SPAN_CHARS * 2
        or len(_TOKEN_RE.findall(middle)) > MAX_REPAIR_SPAN_TOKENS * 2
    ):
        return None
    return middle


def _failed_attempt(
    number: int,
    span: str,
    candidate: str,
    deltas: list[SemanticDelta],
    reason: str,
    usage=None,
    provider_notes: list[str] | None = None,
    cost_estimate: float | None = None,
    provider_called: bool = False,
) -> RepairAttempt:
    return RepairAttempt(
        number,
        span,
        "",
        candidate,
        candidate,
        list(deltas),
        list(deltas),
        False,
        reason,
        _utc_now(),
        usage,
        list(provider_notes or []),
        cost_estimate,
        provider_called,
    )


def repair_loop(
    *,
    source: str,
    candidate: str,
    initial_verification: VerificationResult,
    repair_provider: RepairProvider,
    verify_candidate: Callable[[str], VerificationResult],
    max_attempts: int = MAX_REPAIR_ATTEMPTS,
) -> RepairExecution:
    """Attempt at most two confined mutations, with full re-verification each time."""
    if not 1 <= max_attempts <= MAX_REPAIR_ATTEMPTS:
        raise ValueError(f"max_attempts must be between 1 and {MAX_REPAIR_ATTEMPTS}")
    current, verification, attempts = candidate, initial_verification, []
    verifier_call_count = getattr(
        verification, "verifier_call_count", int(bool(verification.verifier_used))
    )
    verifier_usage: dict[str, int] = {}
    _add_usage(verifier_usage, verification.token_usage)
    verifier_costs: list[float | None] = [verification.cost_estimate] if verifier_call_count else []

    def record_verification(result: VerificationResult) -> None:
        nonlocal verifier_call_count
        verifier_call_count += getattr(
            result, "verifier_call_count", int(bool(result.verifier_used))
        )
        _add_usage(verifier_usage, result.token_usage)
        if getattr(result, "verifier_call_count", int(bool(result.verifier_used))):
            verifier_costs.append(result.cost_estimate)

    def finish(
        final_candidate: str,
        final_verification: VerificationResult,
        successful: bool,
        failure_reason: str | None = None,
    ) -> RepairExecution:
        return RepairExecution(
            final_candidate,
            final_verification,
            attempts,
            successful,
            failure_reason,
            verifier_call_count,
            verifier_usage or None,
            _cost_total(verifier_costs),
        )

    if verification.status is VerificationStatus.PASS:
        return finish(current, verification, False)
    if not verification.semantic_deltas:
        return finish(
            current,
            verification,
            False,
            "No structured semantic delta is available for bounded repair.",
        )
    if any(not d.repairable for d in verification.semantic_deltas):
        return finish(
            current,
            verification,
            False,
            "At least one semantic delta is not bounded and repairable; repair bypassed.",
        )

    for number in range(1, max_attempts + 1):
        if not verification.semantic_deltas or any(
            not d.repairable for d in verification.semantic_deltas
        ):
            return finish(
                current,
                verification,
                False,
                "Repair stopped because the remaining delta set is not fully repairable.",
            )
        delta = verification.semantic_deltas[0]
        span = locate_span(source, current, delta)
        if span is None or span.confidence < MIN_LOCALISATION_CONFIDENCE:
            reason = "Offending span could not be localised with >=95% confidence."
            attempts.append(
                _failed_attempt(
                    number,
                    delta.candidate_span or "",
                    current,
                    verification.semantic_deltas,
                    reason,
                )
            )
            return finish(current, verification, False, reason)

        offending = current[span.candidate_start : span.candidate_end]
        prompt = render_repair_prompt(
            source=source, candidate=current, delta=delta, offending_span=offending
        )
        try:
            proposal = repair_provider.repair(
                prompt=prompt,
                source=source,
                candidate=current,
                delta=delta,
                candidate_start=span.candidate_start,
                candidate_end=span.candidate_end,
            )
        except (TypeError, ValueError, RuntimeError) as exc:
            reason = f"Repair provider failed: {exc}"
            attempts.append(
                _failed_attempt(
                    number,
                    offending,
                    current,
                    verification.semantic_deltas,
                    reason,
                    provider_called=True,
                )
            )
            return finish(current, verification, False, reason)
        if not isinstance(proposal, RewriteCandidate) or not isinstance(
            proposal.candidate_text, str
        ):
            reason = "Repair provider returned a malformed result object."
            attempts.append(
                _failed_attempt(
                    number,
                    offending,
                    current,
                    verification.semantic_deltas,
                    reason,
                    provider_called=True,
                )
            )
            return finish(current, verification, False, reason)

        repaired = proposal.candidate_text
        repaired_span = _confined_middle(
            current, repaired, span.candidate_start, span.candidate_end
        )
        if repaired_span is None:
            reason = (
                "Repair changed text outside the authorised local span or made no local change."
            )
            attempts.append(
                _failed_attempt(
                    number,
                    offending,
                    current,
                    verification.semantic_deltas,
                    reason,
                    proposal.token_usage,
                    proposal.notes,
                    proposal.cost_estimate,
                    True,
                )
            )
            return finish(current, verification, False, reason)

        new_verification = verify_candidate(repaired)
        record_verification(new_verification)
        success = new_verification.status is VerificationStatus.PASS
        attempts.append(
            RepairAttempt(
                number,
                offending,
                repaired_span,
                current,
                repaired,
                list(verification.semantic_deltas),
                list(new_verification.semantic_deltas),
                success,
                None if success else f"Re-verification returned {new_verification.status.value}.",
                _utc_now(),
                proposal.token_usage,
                list(proposal.notes),
                proposal.cost_estimate,
                True,
                getattr(
                    new_verification,
                    "verifier_call_count",
                    int(bool(new_verification.verifier_used)),
                ),
                new_verification.token_usage,
                new_verification.cost_estimate,
            )
        )
        if success:
            return finish(repaired, new_verification, True)
        current, verification = repaired, new_verification
        if any(not d.repairable for d in verification.semantic_deltas):
            return finish(
                current,
                verification,
                False,
                "Re-verification produced a non-repairable delta; repair stopped.",
            )

    return finish(current, verification, False, "Maximum repair attempts exceeded.")
