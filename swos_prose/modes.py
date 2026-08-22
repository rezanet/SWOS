"""Explicit writer-mode and preset policy contracts for SWOS Prose."""

from __future__ import annotations

from typing import Any

SUPPORTED_MODES = ("polish", "naturalise", "clarify", "tighten")
SUPPORTED_PRESETS = (
    "scholarly-natural",
    "precise-technical",
    "plain-intelligent",
    "elegant-essay",
    "executive",
)

_MODE_OBJECTIVES: dict[str, tuple[str, ...]] = {
    "polish": (
        "improve clarity and sentence construction",
        "reduce unnecessary repetition and wordiness",
        "improve local flow and natural readability",
    ),
    "naturalise": (
        "improve idiomatic flow and natural sentence construction",
        "retain the author's register while removing stiff or mechanical phrasing",
        "make the prose read naturally without changing its material meaning",
    ),
    "clarify": (
        "improve readability and syntactic ambiguity handling",
        "make referents and clause relationships clearer only when licensed by the source",
        "leave unresolved ambiguity unchanged rather than resolving it by guess",
    ),
    "tighten": (
        "remove redundant wording and unnecessary repetition",
        "compress expression without dropping material detail or force-bearing qualifiers",
        "preserve every condition, exception, attribution, and epistemic commitment",
    ),
}

_PRESET_GUIDANCE: dict[str, tuple[str, ...]] = {
    "scholarly-natural": (
        "Use natural scholarly prose with precise terminology and restrained transitions.",
        "Prefer explicit epistemic qualification over rhetorical certainty.",
    ),
    "precise-technical": (
        "Prefer exact technical terminology, explicit relationships, and concise syntax.",
        "Do not simplify away units, conditions, interfaces, or operational detail.",
    ),
    "plain-intelligent": (
        "Prefer clear, direct language accessible to an informed non-specialist.",
        "Explain only what the source already states; never add an explanation as a fact.",
    ),
    "elegant-essay": (
        "Prefer graceful rhythm and varied sentence construction without ornamental drift.",
        "Preserve the author's stance, qualification, and argumentative progression.",
    ),
    "executive": (
        "Prefer concise, decision-useful wording and foreground the source's stated implications.",
        "Do not turn a qualified observation into a recommendation or decision.",
    ),
}

_COMMON_PRESERVE = (
    "material propositions",
    "attribution",
    "speech act",
    "uncertainty and modality",
    "epistemic status",
    "degree and scalar force",
    "negation",
    "causal force",
    "relational direction",
    "scope and quantifiers",
    "chronology, conditions, and exceptions",
    "normative stance",
    "protected anchors verbatim",
    "protected numbers, dates, units, citations, and quotations",
)

_COMMON_FORBIDDEN = (
    "new factual claims",
    "new examples, evidence, explanations, citations, or conclusions",
    "certainty or causal strengthening",
    "degree-to-modality substitution",
    "modal-force substitution",
    "ambiguity resolution by guessing",
    "whole-text regeneration disguised as local repair",
)


def _validate_mode(mode: str) -> str:
    if not isinstance(mode, str) or mode not in SUPPORTED_MODES:
        raise ValueError(f"Unknown prose mode: {mode!r}; expected one of {SUPPORTED_MODES}.")
    return mode


def _validate_preset(preset: str | None) -> str | None:
    if preset is not None and (not isinstance(preset, str) or preset not in SUPPORTED_PRESETS):
        raise ValueError(
            f"Unknown prose preset: {preset!r}; expected one of {SUPPORTED_PRESETS} or None."
        )
    return preset


def writer_policy(mode: str = "polish", preset: str | None = None) -> dict[str, Any]:
    """Return explicit, serialisable policy data for one writer invocation.

    The policy describes editorial objectives only. It is never a semantic
    approval signal; the common verification pipeline remains authoritative.
    """

    mode = _validate_mode(mode)
    preset = _validate_preset(preset)
    return {
        "policy_version": "swos-prose-writer-policy-v1",
        "mode": mode,
        "preset": preset,
        "objectives": list(_MODE_OBJECTIVES[mode]),
        "preset_guidance": list(_PRESET_GUIDANCE[preset]) if preset else [],
        "must_preserve": list(_COMMON_PRESERVE),
        "forbidden": list(_COMMON_FORBIDDEN),
    }


def validate_mode_and_preset(mode: str = "polish", preset: str | None = None) -> None:
    """Validate a public mode/preset pair before any provider construction/call."""

    writer_policy(mode, preset)
