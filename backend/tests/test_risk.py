from backend.blotguard.domain.risk import (
    RISK_LEVEL_BOUNDARIES,
    risk_level_for_score,
)


def test_experimental_five_level_boundaries():
    b0, b1, b2, b3 = RISK_LEVEL_BOUNDARIES

    assert risk_level_for_score(None) is None
    assert risk_level_for_score(0.0) == "very_low"
    assert risk_level_for_score(b0) == "low"
    assert risk_level_for_score(b1) == "medium"
    assert risk_level_for_score(b2) == "high"
    assert risk_level_for_score(b3) == "very_high"
    assert risk_level_for_score(1.0) == "very_high"
