from app import confidence, models


def test_confidence_classes_use_agreed_boundaries() -> None:
    assert confidence.classify(0.19) == models.ConfidenceClass.REJECT
    assert confidence.classify(0.44) == models.ConfidenceClass.PROBABLY_INCORRECT
    assert confidence.classify(0.69) == models.ConfidenceClass.NEEDS_REVIEW
    assert confidence.classify(0.89) == models.ConfidenceClass.PROBABLY_CORRECT
    assert confidence.classify(0.90) == models.ConfidenceClass.VERY_PROBABLY_CORRECT


def test_class_a_can_auto_approve_strong_independent_evidence() -> None:
    result = confidence.calculate(
        confidence.ScoreInput(
            entity_match=0.99,
            source_quality=0.98,
            agreement=1.0,
            semantic_fit=1.0,
            freshness=0.95,
            validation=1.0,
            independent_sources=2,
        ),
        models.AutomationClass.A,
    )
    assert result.confidence >= 0.95
    assert result.auto_approval_eligible is True


def test_class_c_never_auto_approves_and_conflicts_block_automation() -> None:
    evidence = confidence.ScoreInput(
        entity_match=1.0,
        source_quality=1.0,
        agreement=1.0,
        semantic_fit=1.0,
        freshness=1.0,
        validation=1.0,
        independent_sources=3,
        has_conflict=True,
    )
    assert confidence.calculate(evidence, models.AutomationClass.A).auto_approval_eligible is False
    assert confidence.calculate(evidence, models.AutomationClass.C).auto_approval_eligible is False
