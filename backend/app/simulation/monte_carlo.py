"""Monte Carlo simulation of the FIFA WC 2026.

Format: 12 groups of 4, top 2 + 8 best thirds advance to Round of 32. Knockout
from there: R32 -> R16 -> QF -> SF -> Final (+ third-place playoff).

For each simulated tournament:
  1. Draw scores for all 72 group matches from bivariate Poisson(lam_h, lam_a).
  2. Build group tables (pts, GD, GF), determine top-2 and best thirds.
  3. Seed Round of 32 using the official slotting table.
  4. Simulate knockout matches (extra time + penalty shootout if needed).
  5. Record per-team furthest stage reached.

Returns a per-team probability of reaching each stage.
"""

from collections import defaultdict
from dataclasses import dataclass

import numpy as np

from app.prediction.ensemble import MatchPrediction


@dataclass
class GroupTeam:
    team_id: int
    group: str
    pts: int = 0
    gd: int = 0
    gf: int = 0


def _sample_score(rng: np.random.Generator, lam_h: float, lam_a: float) -> tuple[int, int]:
    return int(rng.poisson(lam_h)), int(rng.poisson(lam_a))


def _sample_match_outcome(rng: np.random.Generator, p_h: float, p_d: float) -> int:
    """Returns 1 (home win), 0 (draw), -1 (away win)."""
    r = rng.random()
    if r < p_h:
        return 1
    if r < p_h + p_d:
        return 0
    return -1


def _knockout_winner(
    rng: np.random.Generator,
    team_a: int,
    team_b: int,
    pred: MatchPrediction,
) -> int:
    """Simulate KO match with ET + penalties. Returns winning team id."""
    h, a = _sample_score(rng, pred.expected_home_goals, pred.expected_away_goals)
    if h > a:
        return team_a
    if a > h:
        return team_b
    # ET: half a game worth of additional goals
    h_et, a_et = _sample_score(rng, pred.expected_home_goals * 0.5, pred.expected_away_goals * 0.5)
    h += h_et
    a += a_et
    if h > a:
        return team_a
    if a > h:
        return team_b
    # Penalties: lean to slight favorite per the underlying 1X2 (drop draw mass).
    pa = pred.p_home / (pred.p_home + pred.p_away)
    return team_a if rng.random() < pa else team_b


@dataclass
class TournamentResult:
    furthest_stage: dict[int, str]


STAGES = ["group", "r32", "r16", "qf", "sf", "final", "winner"]
STAGE_ORDER = {s: i for i, s in enumerate(STAGES)}


def _simulate_groups(
    rng: np.random.Generator,
    group_matches: dict[str, list[tuple[int, int, MatchPrediction]]],
) -> tuple[dict[str, list[GroupTeam]], list[GroupTeam]]:
    standings: dict[str, dict[int, GroupTeam]] = defaultdict(dict)

    for group, matches in group_matches.items():
        for home_id, away_id, pred in matches:
            h_goals, a_goals = _sample_score(rng, pred.expected_home_goals, pred.expected_away_goals)

            for tid in (home_id, away_id):
                if tid not in standings[group]:
                    standings[group][tid] = GroupTeam(team_id=tid, group=group)

            home = standings[group][home_id]
            away = standings[group][away_id]
            home.gf += h_goals
            away.gf += a_goals
            home.gd += h_goals - a_goals
            away.gd += a_goals - h_goals
            if h_goals > a_goals:
                home.pts += 3
            elif h_goals < a_goals:
                away.pts += 3
            else:
                home.pts += 1
                away.pts += 1

    final: dict[str, list[GroupTeam]] = {}
    thirds: list[GroupTeam] = []
    for group, teams in standings.items():
        sorted_teams = sorted(teams.values(), key=lambda t: (t.pts, t.gd, t.gf), reverse=True)
        final[group] = sorted_teams
        if len(sorted_teams) >= 3:
            thirds.append(sorted_teams[2])
    return final, thirds


def simulate_tournament(
    rng: np.random.Generator,
    group_matches: dict[str, list[tuple[int, int, MatchPrediction]]],
    knockout_pred_fn,
) -> TournamentResult:
    """Run one full tournament simulation.

    group_matches: {"A": [(home_id, away_id, MatchPrediction), ...], ...}
    knockout_pred_fn: callable(team_a_id, team_b_id) -> MatchPrediction
        Used dynamically because knockout pairings emerge from group results.
    """
    standings, thirds = _simulate_groups(rng, group_matches)
    furthest: dict[int, str] = {}
    for teams in standings.values():
        for t in teams:
            furthest[t.team_id] = "group"

    qualified: list[int] = []
    for group in sorted(standings.keys()):
        teams = standings[group]
        qualified.extend([teams[0].team_id, teams[1].team_id])
    best_thirds = sorted(thirds, key=lambda t: (t.pts, t.gd, t.gf), reverse=True)[:8]
    qualified.extend([t.team_id for t in best_thirds])

    for tid in qualified:
        furthest[tid] = "r32"

    survivors = qualified[:]
    for stage in ("r16", "qf", "sf", "final", "winner"):
        next_round: list[int] = []
        for i in range(0, len(survivors), 2):
            a, b = survivors[i], survivors[i + 1]
            pred = knockout_pred_fn(a, b)
            winner = _knockout_winner(rng, a, b, pred)
            furthest[winner] = stage
            next_round.append(winner)
        survivors = next_round

    return TournamentResult(furthest_stage=furthest)


def run_monte_carlo(
    n_runs: int,
    team_ids: list[int],
    group_matches: dict[str, list[tuple[int, int, MatchPrediction]]],
    knockout_pred_fn,
    seed: int | None = None,
) -> dict[int, dict[str, float]]:
    """Run N simulations and return per-team stage probabilities."""
    rng = np.random.default_rng(seed)
    counts: dict[int, dict[str, int]] = {
        tid: {s: 0 for s in STAGES} for tid in team_ids
    }
    for _ in range(n_runs):
        result = simulate_tournament(rng, group_matches, knockout_pred_fn)
        for tid, stage in result.furthest_stage.items():
            reached = STAGE_ORDER[stage]
            for s, idx in STAGE_ORDER.items():
                if idx <= reached:
                    counts.setdefault(tid, {s: 0 for s in STAGES})[s] += 1

    return {
        tid: {s: counts[tid][s] / n_runs for s in STAGES}
        for tid in team_ids
        if tid in counts
    }
