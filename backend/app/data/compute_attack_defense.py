"""Compute per-team attack and defense rates from historical match results.

Replaces the hardcoded 2.7 expected-total split in the prediction pipeline with
team-specific Poisson rates. Output: each Team gets `attack_rate` and
`defense_rate` multipliers normalized so the global weighted mean attack = 1.0.

Method — iterative MLE (Dixon-Coles style):
  λ_home_in_match = a_home × d_away × league_avg
  λ_away_in_match = a_away × d_home × league_avg

  For each iteration:
    a_i_new = a_i × (actual_goals_scored_i / expected_goals_scored_i)
    d_i_new = d_i × (actual_goals_conceded_i / expected_goals_conceded_i)
  After ~30 iterations the rates converge to MLE values that *account for
  opponent strength* — scoring 5 vs a weak defense is worth less than scoring
  2 vs a top defense.

  Without this, a CAF team that thrashes co-confed minnows ends up with a
  higher attack rate than a CONMEBOL team that grinds 1:0 wins past Brazil.

Each match is time-weighted with a 4-year exponential decay so recent results
count more. Final rates are Bayesian-shrunk toward 1.0 with strength k=4 so
teams with few historical games don't get extreme values from small samples.

Run inside the backend container:
    docker compose exec backend python -m app.data.compute_attack_defense
"""

import math

from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models.match import Match
from app.models.team import Team


HALF_LIFE_YEARS = 4.0
SHRINK_K = 4.0
N_ITERATIONS = 40


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
    decay = math.log(2) / (HALF_LIFE_YEARS * 365.25 * 24 * 3600)

    # One pass: gather per-team actuals, per-match weights, league average.
    actual_scored: dict[int, float] = {t.id: 0.0 for t in teams}
    actual_conceded: dict[int, float] = {t.id: 0.0 for t in teams}
    weighted_games: dict[int, float] = {t.id: 0.0 for t in teams}
    games: list[tuple[int, int, float]] = []  # (home_id, away_id, weight)
    total_goals_w = 0.0
    total_weight = 0.0

    for m in matches:
        h, a = m.home_score, m.away_score
        if h is None or a is None:
            continue
        age_s = (ref_date - m.kickoff).total_seconds()
        w = math.exp(-decay * age_s)
        games.append((m.home_team_id, m.away_team_id, w))
        actual_scored[m.home_team_id] = actual_scored.get(m.home_team_id, 0.0) + h * w
        actual_scored[m.away_team_id] = actual_scored.get(m.away_team_id, 0.0) + a * w
        actual_conceded[m.home_team_id] = actual_conceded.get(m.home_team_id, 0.0) + a * w
        actual_conceded[m.away_team_id] = actual_conceded.get(m.away_team_id, 0.0) + h * w
        weighted_games[m.home_team_id] = weighted_games.get(m.home_team_id, 0.0) + w
        weighted_games[m.away_team_id] = weighted_games.get(m.away_team_id, 0.0) + w
        total_goals_w += (h + a) * w
        total_weight += w

    league_avg = total_goals_w / (2 * total_weight) if total_weight > 0 else 1.35

    # Iterative MLE on raw attack / defense values (pre-shrinkage).
    attack: dict[int, float] = {t.id: 1.0 for t in teams}
    defense: dict[int, float] = {t.id: 1.0 for t in teams}

    for _ in range(N_ITERATIONS):
        exp_scored: dict[int, float] = {t.id: 0.0 for t in teams}
        exp_conceded: dict[int, float] = {t.id: 0.0 for t in teams}
        for home_id, away_id, w in games:
            exp_h = attack[home_id] * defense[away_id] * league_avg * w
            exp_a = attack[away_id] * defense[home_id] * league_avg * w
            exp_scored[home_id] = exp_scored.get(home_id, 0.0) + exp_h
            exp_scored[away_id] = exp_scored.get(away_id, 0.0) + exp_a
            exp_conceded[home_id] = exp_conceded.get(home_id, 0.0) + exp_a
            exp_conceded[away_id] = exp_conceded.get(away_id, 0.0) + exp_h

        new_attack: dict[int, float] = {}
        new_defense: dict[int, float] = {}
        for t in teams:
            n = weighted_games.get(t.id, 0.0)
            if n < 0.5 or exp_scored.get(t.id, 0.0) < 0.01:
                new_attack[t.id] = attack[t.id]
            else:
                new_attack[t.id] = attack[t.id] * actual_scored[t.id] / exp_scored[t.id]
                # Clamp to keep iteration stable for tiny samples.
                new_attack[t.id] = max(0.1, min(4.0, new_attack[t.id]))
            if n < 0.5 or exp_conceded.get(t.id, 0.0) < 0.01:
                new_defense[t.id] = defense[t.id]
            else:
                new_defense[t.id] = defense[t.id] * actual_conceded[t.id] / exp_conceded[t.id]
                new_defense[t.id] = max(0.1, min(4.0, new_defense[t.id]))

        # Normalize attack to weighted mean 1.0 (defense floats with it — only
        # the product attack_i × defense_j matters for predictions).
        played = [(tid, n) for tid, n in weighted_games.items() if n > 0.5]
        total_n = sum(n for _, n in played)
        if total_n > 0:
            weighted_mean = sum(new_attack[tid] * n for tid, n in played) / total_n
            if weighted_mean > 0:
                for tid in new_attack:
                    new_attack[tid] /= weighted_mean
                    new_defense[tid] *= weighted_mean

        attack = new_attack
        defense = new_defense

    # Apply Bayesian shrinkage toward 1.0 and write back.
    for t in teams:
        n = weighted_games.get(t.id, 0.0)
        if n < 0.01:
            t.attack_rate = 1.0
            t.defense_rate = 1.0
            continue
        t.attack_rate = (n * attack[t.id] + SHRINK_K) / (n + SHRINK_K)
        t.defense_rate = (n * defense[t.id] + SHRINK_K) / (n + SHRINK_K)

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
