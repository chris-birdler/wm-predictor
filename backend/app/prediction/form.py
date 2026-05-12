"""Recent form as Elo-Surprise EWMA.

Naive W/D/L counting is what made our old form module rank DR Congo above
Portugal: Congo wins lots of CAF qualifiers vs weak sides; Portugal loses to
top sides in Nations League. Result-counting punishes Portugal for the harder
schedule.

This version follows the same principle Tennis ratings (ITN/UTR) and Glicko
use: each match contributes (actual − expected) where the expectation comes
from the Elo gap. A team that *beats* a top side has a big positive surprise;
a team that beats a much weaker side has near-zero surprise (already
expected).

Returns a surprise score in roughly [-0.5, +0.5]. Positive = over-performing
the long-term Elo; negative = under-performing.
"""

from datetime import datetime
from math import exp

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.match import Match
from app.models.team import Team
from app.prediction.elo import HOME_ADVANTAGE_ELO

FORM_WINDOW = 15
DECAY_TAU_DAYS = 180.0


def _expected_for(team_elo: float, opp_elo: float, is_home: bool, neutral: bool) -> float:
    bonus = 0.0 if neutral else (HOME_ADVANTAGE_ELO if is_home else -HOME_ADVANTAGE_ELO)
    return 1.0 / (1.0 + 10 ** ((opp_elo - team_elo - bonus) / 400))


def team_form(db: Session, team_id: int, as_of: datetime) -> float:
    """Return the team's recent surprise score (over-/underperformance vs Elo).

    Uses each opponent's CURRENT Elo as a proxy for their Elo at the time of
    the match. Within a 6-month decay window this is accurate enough — most
    teams don't move >50 Elo in that span.
    """
    team = db.get(Team, team_id)
    if team is None:
        return 0.0

    stmt = (
        select(Match)
        .where(
            Match.is_finished.is_(True),
            Match.kickoff < as_of,
            or_(Match.home_team_id == team_id, Match.away_team_id == team_id),
        )
        .order_by(Match.kickoff.desc())
        .limit(FORM_WINDOW)
    )
    matches = db.execute(stmt).scalars().all()
    if not matches:
        return 0.0

    surprise_sum = 0.0
    weight_sum = 0.0
    for m in matches:
        is_home = m.home_team_id == team_id
        gf = m.home_score if is_home else m.away_score
        ga = m.away_score if is_home else m.home_score
        if gf is None or ga is None:
            continue
        opp_id = m.away_team_id if is_home else m.home_team_id
        opp = db.get(Team, opp_id)
        if opp is None:
            continue

        if gf > ga:
            actual = 1.0
        elif gf == ga:
            actual = 0.5
        else:
            actual = 0.0

        expected = _expected_for(team.elo, opp.elo, is_home=is_home, neutral=False)
        surprise = actual - expected  # in [-1, +1]

        age_days = (as_of - m.kickoff).days
        w = exp(-age_days / DECAY_TAU_DAYS)
        surprise_sum += w * surprise
        weight_sum += w

    return surprise_sum / weight_sum if weight_sum > 0 else 0.0
