from __future__ import annotations

import re

from news_analysis.explanation.models import ExplanationContext


_FORBIDDEN = re.compile(r"<\/?[a-z][^>]*>|(?:ignore|ignore estas instruções|system prompt|instruções do sistema)", re.I)
_URL = re.compile(r"https?://|www\.", re.I)
_NUMBER = re.compile(r"\d+(?:[.,]\d+)?%?")
_INSTRUCTION_FRAGMENT = re.compile(r"^(?:priorize|explique|responda|write|task|answer|explanation)\b", re.I)


def validate_explanation(text: str, context: ExplanationContext) -> tuple[bool, str]:
    """Apply cheap structural and consistency checks to generated text.

    This intentionally does not claim to be a semantic verifier.  Any failed
    check causes the caller to reject the generated response.
    """
    normalized = " ".join(text.split())
    if not normalized or len(normalized) < 70 or len(normalized) > 520:
        return False, "length"
    if normalized[-1] not in ".!?":
        return False, "incomplete"
    if re.search(r"\b(?:veiculo_reconhecido|tld_institucional|transparencia_editorial|idade_dominio)\b", normalized, re.I):
        return False, "internal_label"
    if re.search(r"\b(?:nota|pontua[çc][ãa]o)\s*(?:de|foi|:)?\s*\d", normalized, re.I):
        return False, "numeric_score"
    if _INSTRUCTION_FRAGMENT.search(normalized) or "UNTRUSTED_DATA" in normalized.upper():
        return False, "instruction_fragment"
    if len(re.findall(r"[.!?](?:\s|$)", normalized)) > 3:
        return False, "sentence_limit"
    if _FORBIDDEN.search(normalized) or _URL.search(normalized):
        return False, "unsafe_content"
    allowed = set(context.allowed_numbers)
    if any(number not in allowed for number in _NUMBER.findall(normalized)):
        return False, "new_number"
    if context.fact_check.evidence_status == "UNAVAILABLE" and re.search(
        r"\b(confirmad[oa]|refutad[oa]|comprovad[oa])\b", normalized, re.I
    ):
        return False, "unavailable_claim"
    if context.source_veto_applied is False and re.search(r"\bveto\b", normalized, re.I):
        return False, "veto_contradiction"
    return True, "valid"
