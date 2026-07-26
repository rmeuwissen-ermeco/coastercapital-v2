from __future__ import annotations

from dataclasses import dataclass

from app import models


@dataclass(frozen=True)
class ScoreInput:
    entity_match: float
    source_quality: float
    agreement: float
    semantic_fit: float
    freshness: float
    validation: float
    independent_sources: int
    has_primary_source: bool = False
    has_conflict: bool = False


@dataclass(frozen=True)
class ScoreResult:
    confidence: float
    confidence_class: models.ConfidenceClass
    auto_approval_eligible: bool
    breakdown: dict[str, float]


WEIGHTS = {
    "entity_match": 0.20,
    "source_quality": 0.25,
    "agreement": 0.25,
    "semantic_fit": 0.15,
    "freshness": 0.10,
    "validation": 0.05,
}


def classify(confidence: float) -> models.ConfidenceClass:
    percent = round(confidence * 100)
    if percent <= 19:
        return models.ConfidenceClass.REJECT
    if percent <= 44:
        return models.ConfidenceClass.PROBABLY_INCORRECT
    if percent <= 69:
        return models.ConfidenceClass.NEEDS_REVIEW
    if percent <= 89:
        return models.ConfidenceClass.PROBABLY_CORRECT
    return models.ConfidenceClass.VERY_PROBABLY_CORRECT


def calculate(data: ScoreInput, automation_class: models.AutomationClass) -> ScoreResult:
    values = {
        "entity_match": _bounded(data.entity_match),
        "source_quality": _bounded(data.source_quality),
        "agreement": _bounded(data.agreement),
        "semantic_fit": _bounded(data.semantic_fit),
        "freshness": _bounded(data.freshness),
        "validation": _bounded(data.validation),
    }
    score = round(sum(values[key] * weight for key, weight in WEIGHTS.items()), 4)
    threshold = 0.95 if automation_class == models.AutomationClass.A else 0.97
    enough_evidence = data.independent_sources >= 2 or data.has_primary_source
    eligible = (
        automation_class != models.AutomationClass.C
        and score >= threshold
        and data.entity_match >= 0.98
        and enough_evidence
        and not data.has_conflict
        and data.validation == 1
    )
    return ScoreResult(score, classify(score), eligible, values)


def _bounded(value: float) -> float:
    return min(1.0, max(0.0, value))
