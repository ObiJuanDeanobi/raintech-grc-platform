from typing import Any

import pytest

from api.risk import score_risk


@pytest.mark.parametrize(
    ("likelihood", "impact", "score", "band"),
    [
        (1, 1, 1, "Low"),
        (1, 4, 4, "Low"),
        (2, 3, 6, "Moderate"),
        (3, 3, 9, "Moderate"),
        (3, 4, 12, "High"),
        (4, 4, 16, "High"),
        (4, 5, 20, "Critical"),
        (5, 5, 25, "Critical"),
    ],
)
def test_score_risk_all_boundary_bands(likelihood: int, impact: int, score: int, band: str) -> None:
    assert score_risk(likelihood, impact) == {
        "likelihood": likelihood,
        "impact": impact,
        "score": score,
        "band": band,
    }


@pytest.mark.parametrize("value", [0, 6, -1, 1.0, "3", True, None])
def test_score_risk_rejects_invalid_likelihood(value: Any) -> None:
    with pytest.raises(ValueError):
        score_risk(value, 1)


@pytest.mark.parametrize("value", [0, 6, -1, 1.0, "3", False, None])
def test_score_risk_rejects_invalid_impact(value: Any) -> None:
    with pytest.raises(ValueError):
        score_risk(1, value)
