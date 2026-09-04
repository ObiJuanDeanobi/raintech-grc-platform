"""Shared, dependency-free 5x5 risk calculation primitive."""

from typing import Literal, TypedDict

Band = Literal["Low", "Moderate", "High", "Critical"]


class RiskScore(TypedDict):
    likelihood: int
    impact: int
    score: int
    band: Band


def score_risk(likelihood: int, impact: int) -> RiskScore:
    if (
        isinstance(likelihood, bool)
        or isinstance(impact, bool)
        or not isinstance(likelihood, int)
        or not isinstance(impact, int)
        or not 1 <= likelihood <= 5
        or not 1 <= impact <= 5
    ):
        raise ValueError("likelihood and impact must be integers from 1 through 5")
    score = likelihood * impact
    band: Band = (
        "Low" if score <= 4 else "Moderate" if score <= 9 else "High" if score <= 16 else "Critical"
    )
    return {"likelihood": likelihood, "impact": impact, "score": score, "band": band}
