"""World Football Elo-style rating.

Reference: eloratings.net formulae. K-factor depends on match importance,
score margin amplifies updates, home advantage adds a fixed delta to the
home team's effective rating.
"""

import math
from dataclasses import dataclass

from app.config import settings
from app.data.confederations import CONFED_K_MULT
from app.models.match import MatchType


HOME_ADVANTAGE_ELO = 100.0

# Match types where confederation depth matters. WC + Continental + Nations
# League pit confederations against each other or are universally taken
# seriously, so we keep the base K. Qualifiers and friendlies are where weak
# co-confed opponents inflate Elo, so we down-weight by the weaker confed.
_CONFED_SENSITIVE = {MatchType.QUALIFIER, MatchType.FRIENDLY}


def k_factor(
    match_type: MatchType,
    home_confed: str | None = None,
    away_confed: str | None = None,
) -> float:
    base = {
        MatchType.WORLDCUP: settings.ELO_K_WORLDCUP,
        MatchType.CONTINENTAL: settings.ELO_K_CONTINENTAL,
        MatchType.QUALIFIER: settings.ELO_K_QUALIFIER,
        MatchType.NATIONS: settings.ELO_K_NATIONS,
        MatchType.FRIENDLY: settings.ELO_K_FRIENDLY,
    }[match_type]

    if match_type not in _CONFED_SENSITIVE or home_confed is None or away_confed is None:
        return base

    # Take the weaker (lower) multiplier — the match is only as reliable as the
    # weaker confederation context.
    mult = min(
        CONFED_K_MULT.get(home_confed, CONFED_K_MULT["UNKNOWN"]),
        CONFED_K_MULT.get(away_confed, CONFED_K_MULT["UNKNOWN"]),
    )
    return base * mult


def expected_score(elo_home: float, elo_away: float, neutral: bool = False) -> float:
    """Pre-match expected score for the home team (0..1)."""
    bonus = 0.0 if neutral else HOME_ADVANTAGE_ELO
    return 1.0 / (1.0 + 10 ** ((elo_away - (elo_home + bonus)) / 400))


def goal_diff_multiplier(goal_diff: int) -> float:
    gd = abs(goal_diff)
    if gd <= 1:
        return 1.0
    if gd == 2:
        return 1.5
    return (11 + gd) / 8.0


def update_ratings(
    elo_home: float,
    elo_away: float,
    home_goals: int,
    away_goals: int,
    match_type: MatchType,
    neutral: bool = False,
    home_confed: str | None = None,
    away_confed: str | None = None,
) -> tuple[float, float]:
    """Return new (home, away) ratings after a played match."""
    k = k_factor(match_type, home_confed, away_confed)
    if home_goals > away_goals:
        actual = 1.0
    elif home_goals < away_goals:
        actual = 0.0
    else:
        actual = 0.5

    expected = expected_score(elo_home, elo_away, neutral=neutral)
    mult = goal_diff_multiplier(home_goals - away_goals)
    delta = k * mult * (actual - expected)
    return elo_home + delta, elo_away - delta


@dataclass
class EloMatchProbs:
    p_home: float
    p_draw: float
    p_away: float


def match_probs(elo_home: float, elo_away: float, neutral: bool = False) -> EloMatchProbs:
    """Convert Elo difference into 1X2 probabilities using a draw-aware model.

    The draw probability is highest when teams are equal and decays with rating
    difference. Empirically a Gaussian-shaped draw component works well; here we
    use a simple parametric form calibrated against historical data.
    """
    bonus = 0.0 if neutral else HOME_ADVANTAGE_ELO
    diff = (elo_home + bonus) - elo_away

    p_home_no_draw = 1.0 / (1.0 + 10 ** (-diff / 400))
    p_away_no_draw = 1.0 - p_home_no_draw

    # Empirical draw rate: ~28% at diff=0, ~12% at |diff|=400.
    p_draw = 0.28 * math.exp(-(diff / 350) ** 2)

    scale = 1.0 - p_draw
    return EloMatchProbs(
        p_home=p_home_no_draw * scale,
        p_draw=p_draw,
        p_away=p_away_no_draw * scale,
    )
