"""Ensemble combines odds + Elo + form + H2H + home-advantage into 1X2 probs.

This is Phase 1 — a transparent weighted soft-voter. Phase 2 will replace the
fixed weights with an XGBoost stacker trained on historical matches that takes
these same features as input.
"""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.match import Match, MatchType
from app.models.odds import OddsSnapshot
from app.models.team import Team
from app.prediction import elo, form, h2h
from app.prediction.odds_aggregator import aggregate


@dataclass
class MatchPrediction:
    p_home: float
    p_draw: float
    p_away: float
    expected_home_goals: float
    expected_away_goals: float
    components: dict[str, tuple[float, float, float]]  # debug: per-source probs


def _form_to_probs(form_home: float, form_away: float) -> tuple[float, float, float]:
    """Map two Elo-surprise scores (each in ~[-0.5, +0.5]) to (p_home, p_draw, p_away).

    Both scores are deltas relative to long-term Elo. The difference indicates
    which team is currently over-performing more.
    """
    diff = form_home - form_away  # range roughly [-1, +1]
    p_home = 0.34 + 0.6 * diff
    p_away = 0.34 - 0.6 * diff
    p_home = max(0.05, min(0.85, p_home))
    p_away = max(0.05, min(0.85, p_away))
    p_draw = max(0.05, 1.0 - p_home - p_away)
    total = p_home + p_draw + p_away
    return (p_home / total, p_draw / total, p_away / total)


def _is_home_advantage_team(team: Team) -> bool:
    return team.is_host or team.fifa_code in {"USA", "CAN", "MEX"}


def predict_match(db: Session, match: Match) -> MatchPrediction:
    home: Team = db.get(Team, match.home_team_id)
    away: Team = db.get(Team, match.away_team_id)
    neutral = not _is_home_advantage_team(home)

    # 1. Odds
    snapshots = db.execute(
        select(OddsSnapshot).where(OddsSnapshot.match_id == match.id)
    ).scalars().all()
    odds_probs = aggregate(snapshots)

    # 2. Elo
    elo_probs = elo.match_probs(home.elo, away.elo, neutral=neutral)

    # 3. Form
    f_home = form.team_form(db, home.id, match.kickoff)
    f_away = form.team_form(db, away.id, match.kickoff)
    form_probs = _form_to_probs(f_home, f_away)

    # 4. H2H
    h2h_probs_tuple = h2h.h2h_probs(db, home.id, away.id, match.kickoff)

    # Host advantage is already encoded inside Elo via the +100 home bonus
    # (see elo.match_probs / HOME_ADVANTAGE_ELO), so no separate component.

    components: dict[str, tuple[float, float, float]] = {
        "elo": (elo_probs.p_home, elo_probs.p_draw, elo_probs.p_away),
        "form": form_probs,
        "h2h": h2h_probs_tuple,
    }
    weights = {
        "elo": settings.ENSEMBLE_WEIGHT_ELO,
        "form": settings.ENSEMBLE_WEIGHT_FORM,
        "h2h": settings.ENSEMBLE_WEIGHT_H2H,
    }
    if odds_probs is not None:
        components["odds"] = (odds_probs.p_home, odds_probs.p_draw, odds_probs.p_away)
        weights["odds"] = settings.ENSEMBLE_WEIGHT_ODDS
    else:
        # Redistribute odds weight to Elo when no odds available
        weights["elo"] += settings.ENSEMBLE_WEIGHT_ODDS

    total_w = sum(weights.values())
    p_h = sum(components[k][0] * w for k, w in weights.items()) / total_w
    p_d = sum(components[k][1] * w for k, w in weights.items()) / total_w
    p_a = sum(components[k][2] * w for k, w in weights.items()) / total_w
    s = p_h + p_d + p_a
    p_h, p_d, p_a = p_h / s, p_d / s, p_a / s

    # Expected goals: team-specific Poisson rates (Dixon-Coles style).
    # λ_h = home.attack × away.defense × league_avg × home_factor
    # League average goals per team per match for international football ≈ 1.35.
    # Home advantage adds ~15% to the home team's expected goals.
    LEAGUE_AVG_GOALS = 1.35
    HOME_GOAL_BONUS = 1.15
    home_factor = HOME_GOAL_BONUS if not neutral else 1.0
    lam_home = home.attack_rate * away.defense_rate * LEAGUE_AVG_GOALS * home_factor
    lam_away = away.attack_rate * home.defense_rate * LEAGUE_AVG_GOALS
    # Guard against degenerate rates.
    lam_home = max(0.05, min(6.0, lam_home))
    lam_away = max(0.05, min(6.0, lam_away))

    return MatchPrediction(
        p_home=p_h,
        p_draw=p_d,
        p_away=p_a,
        expected_home_goals=lam_home,
        expected_away_goals=lam_away,
        components=components,
    )
