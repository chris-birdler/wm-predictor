"""Compute per-team attack and defense rates from historical match results.

Replaces the hardcoded 2.7 expected-total split in the prediction pipeline with
team-specific Poisson rates. Output: each Team gets `attack_rate` and
`defense_rate` multipliers normalized around the league average (1.0).

Method:
  * Walk all finished matches.
  * Weight each match by exp(-Δt / τ) so recent results count more (τ from
    half-life in years).
  * Goals scored / conceded per team across the weighted sample → attack and
    defense rates relative to league per-team average.
  * Bayesian shrinkage toward 1.0 with strength SHRINK_K (equivalent to that
    many average matches), so teams with few historical games don't get
    extreme rates from small samples.

Run inside the backend container:
    docker compose exec backend python -m app.data.compute_attack_defense
"""

import math

from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models.match import Match
from app.models.team import Team


HALF_LIFE_YEARS = 4.0
# Effective number of "average matches" pulling each rate toward 1.0. Higher =
# more shrinkage. 4 lets top teams keep ~95% of their observed rate while still
# regularizing teams with very few matches.
SHRINK_K = 4.0


def compute(db: Session) -> tuple[int, float]:
    """Populate Team.attack_rate / defense_rate. Returns (n_teams, league_avg)."""
    teams = db.query(Team).all()
    matches = (
        db.query(Match)
        .filter(
            Match.is_finished.is_(True),
            Match.home_score.is_not(None),
            Match.away_score.is_not(None),
        )
        .all()
    )
    if not matches:
        for t in teams:
            t.attack_rate = 1.0
            t.defense_rate = 1.0
        db.commit()
        return len(teams), 0.0

    ref_date = max(m.kickoff for m in matches)
    # Exponential decay constant from half-life.
    decay = math.log(2) / (HALF_LIFE_YEARS * 365.25 * 24 * 3600)

    goals_scored: dict[int, float] = {t.id: 0.0 for t in teams}
    goals_conceded: dict[int, float] = {t.id: 0.0 for t in teams}
    weighted_games: dict[int, float] = {t.id: 0.0 for t in teams}
    total_goals = 0.0
    total_weight = 0.0

    for m in matches:
        age_s = (ref_date - m.kickoff).total_seconds()
        w = math.exp(-decay * age_s)
        h, a = m.home_score, m.away_score
        if h is None or a is None:
            continue
        goals_scored[m.home_team_id] = goals_scored.get(m.home_team_id, 0.0) + h * w
        goals_scored[m.away_team_id] = goals_scored.get(m.away_team_id, 0.0) + a * w
        goals_conceded[m.home_team_id] = goals_conceded.get(m.home_team_id, 0.0) + a * w
        goals_conceded[m.away_team_id] = goals_conceded.get(m.away_team_id, 0.0) + h * w
        weighted_games[m.home_team_id] = weighted_games.get(m.home_team_id, 0.0) + w
        weighted_games[m.away_team_id] = weighted_games.get(m.away_team_id, 0.0) + w
        total_goals += (h + a) * w
        total_weight += w

    # League average goals per team per match (~1.35 for international football).
    league_avg = total_goals / (2 * total_weight) if total_weight > 0 else 1.35

    for t in teams:
        n = weighted_games.get(t.id, 0.0)
        if n < 0.01 or league_avg == 0:
            t.attack_rate = 1.0
            t.defense_rate = 1.0
            continue
        observed_attack = (goals_scored[t.id] / n) / league_avg
        observed_defense = (goals_conceded[t.id] / n) / league_avg
        # Bayesian shrinkage: posterior = (n·obs + k·1.0) / (n + k).
        t.attack_rate = (n * observed_attack + SHRINK_K) / (n + SHRINK_K)
        t.defense_rate = (n * observed_defense + SHRINK_K) / (n + SHRINK_K)

    db.commit()
    return len(teams), league_avg


def main() -> None:
    db = SessionLocal()
    try:
        n_teams, league_avg = compute(db)
        print(f"Computed attack/defense rates for {n_teams} teams (league avg = {league_avg:.3f} goals/team/match)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
