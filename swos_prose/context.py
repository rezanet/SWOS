"""Fail-closed handling for untrusted read-only prose context."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from .models import DeltaType, SemanticDelta, Severity

MAX_CONTEXT_CHARS = 12_000
_INSTRUCTION_LIKE_RE = re.compile(
    r"\b(?:ignore|disregard|override|follow|obey|system|developer|prompt|instruction|jailbreak)\b",
    re.IGNORECASE,
)
_WORD_RE = re.compile(r"\b[\w’'-]+\b", re.UNICODE)
_SENTENCE_TERMINATORS = frozenset(".!?。！？｡؟।॥‼⁇⁈⁉⸮")
_NO_SPACE_SENTENCE_TERMINATORS = frozenset("。！？｡؟।॥‼⁇⁈⁉⸮")
_CLOSING_SENTENCE_DELIMITERS = frozenset("\"')]}”’")
_INITIALISM_RE = re.compile(r"(?:\b[A-Za-z]\.){2,}")
_INITIALISM_AT_FRAGMENT_END_RE = re.compile(r"(?:\b[A-Za-z]\.){2,}$")
_CONTEXT_WRAPPER_RE = re.compile(r"^[\"'([{“‘]+|[\"')]}”’]+$")
_CONTEXT_MARKDOWN_WRAPPERS = ("```", "***", "___", "~~", "``", "**", "__", "`", "*", "_")
_CONTEXT_PRESENTATION_PREFIX_RE = re.compile(
    r"^(?:(?:>{1,3}\s+(?=[^\W\d_]|[\"'“‘]))|"
    r"(?:#{1,6}\s+(?=[^\W\d_]|[\"'“‘]))|"
    r"(?:[-+*•◦▪‣]\s+(?=[^\W\d_]|[\"'“‘]))|"
    r"(?:\d{1,9}[.)]\s+(?=[^\W\d_]|[\"'“‘])))+"
)
_CONTEXT_TERMINAL_PUNCTUATION_RE = re.compile(r"[.!?。！？｡؟।॥‼⁇⁈⁉⸮]+$")
_CONTEXT_IGNORED_SYMBOLS = frozenset(".!?。！？｡؟।॥‼⁇⁈⁉⸮")
_TECHNICAL_SENTENCE_START_WORDS = frozenset(
    {
        "api",
        "bash",
        "curl",
        "docker",
        "git",
        "http",
        "https",
        "jq",
        "kubectl",
        "kubernetes",
        "linux",
        "make",
        "nginx",
        "npm",
        "postgres",
        "powershell",
        "pytest",
        "python",
        "redis",
        "sql",
        "ssh",
        "systemd",
        "terraform",
        "windows",
        "yarn",
    }
)


@dataclass(frozen=True)
class ContextSafety:
    accepted: bool
    signals: tuple[str, ...]
    before_sha256: str | None
    after_sha256: str | None
    before_chars: int
    after_chars: int

    def to_dict(self) -> dict[str, object]:
        return {
            "accepted": self.accepted,
            "signals": list(self.signals),
            "before_sha256": self.before_sha256,
            "after_sha256": self.after_sha256,
            "before_chars": self.before_chars,
            "after_chars": self.after_chars,
            "untrusted": True,
        }

    def to_provider_dict(self, *, before: str | None, after: str | None) -> dict[str, object]:
        payload = self.to_dict()
        payload.update({"before": before, "after": after})
        return payload


def _digest(value: str | None) -> str | None:
    return hashlib.sha256(value.encode("utf-8")).hexdigest() if value is not None else None


def inspect_context(before: str | None = None, after: str | None = None) -> ContextSafety:
    """Validate bounds and record untrusted context metadata without judging prose."""

    signals: list[str] = []
    for label, value in (("before", before), ("after", after)):
        if value is not None and not isinstance(value, str):
            raise TypeError(f"context_{label} must be a string or None")
        if value is not None and len(value) > MAX_CONTEXT_CHARS:
            signals.append(f"context_{label}_exceeds_character_budget")
        if value is not None and "\x00" in value:
            signals.append(f"context_{label}_contains_nul")
        if value and _INSTRUCTION_LIKE_RE.search(value):
            signals.append(f"context_{label}_contains_instruction_like_text")
    if (before and before.strip()) or (after and after.strip()):
        signals.append("context_is_untrusted_read_only_input")
    hard_failures = {
        signal
        for signal in signals
        if signal.endswith("_exceeds_character_budget") or signal.endswith("_contains_nul")
    }
    return ContextSafety(
        accepted=not hard_failures,
        signals=tuple(dict.fromkeys(signals)),
        before_sha256=_digest(before),
        after_sha256=_digest(after),
        before_chars=len(before or ""),
        after_chars=len(after or ""),
    )


def _strip_markdown_wrapper(value: str) -> str:
    surface = value.strip()
    for wrapper in _CONTEXT_MARKDOWN_WRAPPERS:
        if (
            len(surface) > len(wrapper) * 2
            and surface.startswith(wrapper)
            and surface.endswith(wrapper)
        ):
            inner = surface[len(wrapper) : -len(wrapper)].strip()
            if inner:
                return inner
    return surface


def _find_markdown_closer(value: str, start: int, opening: str, closing: str) -> int | None:
    depth = 0
    escaped = False
    for index in range(start, len(value)):
        character = value[index]
        if escaped:
            escaped = False
            continue
        if character == "\\":
            escaped = True
            continue
        if character == opening:
            depth += 1
        elif character == closing:
            depth -= 1
            if depth == 0:
                return index
    return None


def _strip_markdown_links(value: str) -> str:
    """Replace valid Markdown link syntax with its visible label only.

    A link destination is presentation metadata for this context-only
    comparison, while a raw URL outside link syntax remains untouched as
    potentially meaning-bearing prose.
    """

    surface = value.strip()
    pieces: list[str] = []
    copy_start = 0
    index = 0
    changed = False
    while index < len(surface):
        if surface[index] != "[" or (index > 0 and surface[index - 1] == "!"):
            index += 1
            continue
        label_end = _find_markdown_closer(surface, index, "[", "]")
        if label_end is None or label_end + 1 >= len(surface) or surface[label_end + 1] != "(":
            index += 1
            continue
        destination_end = _find_markdown_closer(surface, label_end + 1, "(", ")")
        if destination_end is None or not surface[label_end + 2 : destination_end].strip():
            index += 1
            continue
        pieces.append(surface[copy_start:index])
        pieces.append(surface[index + 1 : label_end])
        copy_start = destination_end + 1
        index = copy_start
        changed = True
    if not changed:
        return surface
    pieces.append(surface[copy_start:])
    return "".join(pieces).strip()


def _canonical_context_surface(value: str) -> str:
    surface = value.strip()
    while True:
        unwrapped = _strip_markdown_links(surface)
        unwrapped = _CONTEXT_WRAPPER_RE.sub("", unwrapped)
        unwrapped = _strip_markdown_wrapper(unwrapped)
        unpresented = _CONTEXT_PRESENTATION_PREFIX_RE.sub("", unwrapped).strip()
        if unpresented == surface:
            return surface
        surface = unpresented


def _normalise_sentence(value: str) -> str:
    # Keep meaning-bearing operators and identifier punctuation (for example
    # ``C#`` vs ``C++`` and ``foo::bar`` vs ``foo/bar``). Only sentence/display
    # delimiters are discarded before whitespace is canonicalised.
    surface = _strip_closing_sentence_delimiters(_canonical_context_surface(value))
    terminal = _terminal_punctuation(surface)
    if terminal:
        surface = surface.rstrip()[: -len(terminal)].rstrip()
    normalised = " ".join(surface.split())
    return f"{normalised}{terminal}"


def _terminal_punctuation(value: str) -> str:
    match = _terminal_punctuation_match(value)
    return match.group(0) if match is not None else ""


def _strip_closing_sentence_delimiters(value: str) -> str:
    surface = value.rstrip()
    while surface and surface[-1] in _CLOSING_SENTENCE_DELIMITERS:
        surface = surface[:-1].rstrip()
    return surface


def _terminal_punctuation_match(value: str) -> re.Match[str] | None:
    surface = _strip_closing_sentence_delimiters(_canonical_context_surface(value.rstrip()))
    return _CONTEXT_TERMINAL_PUNCTUATION_RE.search(surface)


def _content_tokens(value: str) -> tuple[str, ...]:
    """Return ordered words, initialisms, and meaning-bearing punctuation."""

    folded = _canonical_context_surface(value)
    tokens: list[str] = []
    index = 0
    terminal_match = _terminal_punctuation_match(value)
    terminal_start = terminal_match.start() if terminal_match is not None else None
    while index < len(folded):
        initialism = _INITIALISM_RE.match(folded, index)
        if initialism is not None:
            tokens.append(initialism.group(0))
            index = initialism.end()
            continue
        word = _WORD_RE.match(folded, index)
        if word is not None:
            tokens.append(word.group(0))
            index = word.end()
            continue
        character = folded[index]
        if not character.isspace() and (
            character not in _CONTEXT_IGNORED_SYMBOLS
            or terminal_start is None
            or index < terminal_start
        ):
            tokens.append(character)
        index += 1
    return tuple(tokens)


def _looks_like_technical_sentence_start(value: str) -> bool:
    match = re.match(r"[^\s.!?,;:()\[\]{}]+", value)
    if match is None:
        return False
    token = match.group(0).casefold()
    return (
        token in _TECHNICAL_SENTENCE_START_WORDS
        or any(character.isdigit() for character in token)
        or any(character in "_/-\\" for character in token)
    )


def _source_licenses_context_sentence(
    context_surface: str,
    source_sentences: list[tuple[str, str]],
    *,
    candidate_sentence_count: int,
) -> bool:
    """Allow only a same-length, punctuation-preserving licensed sentence."""

    if candidate_sentence_count != len(source_sentences):
        return False
    context_tokens = _content_tokens(context_surface)
    context_terminal = _terminal_punctuation(context_surface)
    return any(
        _content_tokens(source_surface) == context_tokens
        and _terminal_punctuation(source_surface) == context_terminal
        for source_surface, _ in source_sentences
    )


def _sentences(value: str) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    start = 0

    def append_surface(surface: str) -> None:
        normalised = _normalise_sentence(surface)
        if normalised:
            result.append((surface, normalised))

    for index, character in enumerate(value):
        if character not in _SENTENCE_TERMINATORS:
            continue
        end = index + 1
        while end < len(value) and value[end] in _CLOSING_SENTENCE_DELIMITERS:
            end += 1
        if (
            end < len(value)
            and not value[end].isspace()
            and character not in _NO_SPACE_SENTENCE_TERMINATORS
        ):
            continue
        fragment = value[start:end].strip()
        following = value[end:].lstrip()
        if (
            character == "."
            and _INITIALISM_AT_FRAGMENT_END_RE.search(fragment)
            and following
            and following[0].islower()
            and not _looks_like_technical_sentence_start(following)
        ):
            continue
        append_surface(fragment)
        start = end

    tail = value[start:].strip()
    if tail:
        append_surface(tail)
    return result


def context_only_deltas(
    source: str,
    candidate: str,
    *,
    context_before: str | None = None,
    context_after: str | None = None,
) -> list[SemanticDelta]:
    """Flag a complete context-only sentence copied into a changed candidate.

    This is deliberately an exact, conservative guard. It does not attempt to
    prove that all context use is unsafe; it only blocks a high-confidence
    context-only proposition from receiving an automatic PASS.
    """

    if not candidate or source == candidate:
        return []
    source_sentence_items = _sentences(source)
    candidate_sentence_items = _sentences(candidate)
    source_sentences = {normalised for _, normalised in source_sentence_items}
    candidate_sentences = {normalised for _, normalised in candidate_sentence_items}
    deltas: list[SemanticDelta] = []
    for label, value in (("before", context_before), ("after", context_after)):
        if not value:
            continue
        for surface, normalised in _sentences(value):
            if normalised in source_sentences:
                continue
            if _source_licenses_context_sentence(
                surface,
                source_sentence_items,
                candidate_sentence_count=len(candidate_sentence_items),
            ):
                continue
            if normalised in candidate_sentences:
                deltas.append(
                    SemanticDelta(
                        delta_type=DeltaType.CONTEXT_ONLY_CLAIM,
                        source_span=None,
                        candidate_span=surface,
                        severity=Severity.WARNING,
                        explanation=(
                            f"Candidate contains a complete sentence copied from untrusted "
                            f"context_{label}; context-only propositions are not licensed by source text."
                        ),
                        repairable=False,
                        confidence=1.0,
                    )
                )
    return deltas
