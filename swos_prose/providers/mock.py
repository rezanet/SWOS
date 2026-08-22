"""Static/mock semantic verifier provider for tests and adapter development."""

from __future__ import annotations

import copy
import json
from typing import Any

from .base import ProviderAssessment


class StaticSemanticVerifierProvider:
    """Return a scripted provider assessment from static JSON-compatible data.

    This provider deliberately performs no model call. It exists so the SWOS
    Prose core can be tested against complete, contradictory, unresolved and
    malicious verifier responses before any vendor/model adapter is introduced.
    """

    def __init__(self, payload: dict[str, Any] | str):
        if isinstance(payload, str):
            decoded = json.loads(payload)
            if not isinstance(decoded, dict):
                raise ValueError("Static verifier JSON must decode to an object.")
            payload = decoded
        if not isinstance(payload, dict):
            raise TypeError("Static verifier payload must be a dict or JSON object string.")
        self._payload = copy.deepcopy(payload)
        self.calls = 0

    def verify(self, **_: Any) -> ProviderAssessment:
        self.calls += 1
        return ProviderAssessment.from_dict(copy.deepcopy(self._payload))
