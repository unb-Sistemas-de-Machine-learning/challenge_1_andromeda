"""Explainable claim matching with bounded paraphrases, not semantic probabilities."""
from __future__ import annotations

import re
from dataclasses import dataclass

from news_analysis.criteria.rating_normalization import normalize_text

MATCHER_VERSION = 'claim-match-v2-controlled-paraphrases'
STOPWORDS = {
    'a', 'o', 'os', 'as', 'um', 'uma', 'de', 'da', 'do', 'das', 'dos', 'em',
    'no', 'na', 'nos', 'nas', 'para', 'por', 'com', 'que', 'e', 'ou', 'the',
    'of', 'to', 'in', 'on', 'for', 'and', 'or', 'is', 'are',
}
REPORTING = r'diz|disse|afirma|afirmou|declara|declarou|falou'
NEGATIONS = {'nao', 'nunca', 'jamais', 'not', 'never', 'sem'}
DEBUNKING = {'falso', 'fake', 'boato', 'mentira', 'desmente', 'desmentido', 'enganoso'}


@dataclass(frozen=True)
class ClaimMatch:
    classification: str
    similarity: float
    reason: str
    normalized_target: str
    normalized_claim: str

    @property
    def applicable(self) -> bool:
        return self.classification == 'SAME_CLAIM'


def canonical_claim(value: str) -> str:
    """Small, explicit equivalences. Do not delete negations, actors or numbers."""
    text = normalize_text(value)
    text = re.sub(r'\bdistrito federal\b', 'df', text)
    text = re.sub(r'\b(?:garis|lixeiros?)\b', 'gari', text)
    text = re.sub(r'\b(?:proporciona|proporcionam|traz|gera) orgulho\b', 'da orgulho', text)
    text = re.sub(rf'\b(?:{REPORTING})\b', 'diz', text)
    if 'gari' in text.split():
        text = re.sub(r'\b(?:ser|trabalhar como) gari\b', 'gari', text)
        text = re.sub(r'\b(?:coisa|profissao|trabalho) pobre\b', 'pobre', text)
    return text


def location_anchors(value: str) -> set[str]:
    states = {'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS',
              'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC',
              'SP', 'SE', 'TO'}
    anchors = set(re.findall(r'\b[A-Z]{2}\b', value)) & states
    if re.search(r'\bdistrito federal\b', normalize_text(value)):
        anchors.add('DF')
    return anchors


def _tokens(value: str) -> set[str]:
    return {token for token in value.split() if len(token) >= 2 and token not in STOPWORDS}


def _attribution(value: str) -> tuple[str, str] | None:
    match = re.match(rf'^(.+?)\s+({REPORTING})\s+(?:que\s+)?(.+)$', normalize_text(value))
    if not match:
        return None
    actor = re.sub(r'^(?:o|a)\s+', '', match[1])
    # Titles are only removed in this actor slot, not from the proposition.
    actor = re.sub(r'^(?:presidente|ex presidente)\s+', '', actor)
    return actor, match[3]


def match_claims(target: str | None, checked_claim: str | None) -> ClaimMatch:
    source, checked = canonical_claim(target or ''), canonical_claim(checked_claim or '')
    left, right = _tokens(source), _tokens(checked)
    overlap = left & right
    similarity = min(len(overlap) / len(left), len(overlap) / len(right)) if left and right else 0.0

    def result(classification: str, reason: str) -> ClaimMatch:
        return ClaimMatch(classification, round(similarity, 4), reason, source, checked)

    def uncertain(reason: str) -> ClaimMatch:
        return result('RELATED' if len(overlap) >= 2 else 'DIFFERENT', reason)

    if not source or not checked:
        return result('DIFFERENT', 'missing_claim_text')
    if re.findall(r'\d+(?:[.,]\d+)*', target or '') != re.findall(r'\d+(?:[.,]\d+)*', checked_claim or ''):
        return uncertain('numeric_mismatch')
    for location in location_anchors(target or '') | location_anchors(checked_claim or ''):
        if (location.lower() in source.split()) != (location.lower() in checked.split()):
            return uncertain('location_mismatch')
    for markers in (NEGATIONS, DEBUNKING, {'aumenta', 'aumentou', 'aumentam'},
                    {'reduz', 'reduziu', 'reduzem'}, {'retoma', 'retomou', 'retomaram'},
                    {'suspende', 'suspendeu', 'suspenderam'}):
        if bool(set(source.split()) & markers) != bool(set(checked.split()) & markers):
            return uncertain('polarity_or_action_mismatch')
    source_actor, checked_actor = _attribution(target or ''), _attribution(checked_claim or '')
    if bool(source_actor) != bool(checked_actor):
        return uncertain('attribution_missing')
    if source_actor and checked_actor:
        if source_actor[0] != checked_actor[0]:
            return uncertain('attribution_mismatch')
        # A negation before "said" is not equivalent to one inside the quotation.
        for part in (0, 1):
            if bool(set(source_actor[part].split()) & NEGATIONS) != bool(set(checked_actor[part].split()) & NEGATIONS):
                return uncertain('negation_scope_mismatch')
    if source == checked or (len(overlap) >= 3 and similarity >= .8):
        return result('SAME_CLAIM', 'exact_normalized' if source == checked else 'controlled_lexical_match')
    return uncertain('insufficient_proposition_overlap')
