"""Write real WC 2026 results onto the seeded tournament fixtures.

The martj42 results CSV starts carrying FIFA World Cup 2026 matches as soon as
they are played. This module finds the matching seeded fixture and marks it
finished with the real scoreline, so the app shows the actual result instead of
a prediction (and standings / the bracket are derived from real outcomes).

Matching is by **unordered team pair**, not date: the seeded fixtures use a
synthetic kickoff schedule (see app.data.seed), so dates won't line up, whereas
each pair of teams meets at most once in the group stage.

Scope: group-stage fixtures. Knockout results are deferred — a level KO score
is decided on penalties (winner not derivable from the goal columns alone) and
the Monte-Carlo bracket would also need to honour a fixed KO result; both are a
separate follow-up. KO rows are left untouched (and still predicted) here.

Run inside the backend container:
    python -m app.data.apply_results
"""

import pandas as pd

from app.data.historical_ingestor import NAME_ALIASES, fetch_results_csv
from app.db import SessionLocal
from app.models.match import Match, MatchStage
from app.models.team import Team

WC_TOURNAMENT = "FIFA World Cup"
WC_YEAR = 2026


def _canonical(name: str) -> str:
    return NAME_ALIASES.get(name, name)


def apply_results(db) -> tuple[int, int, list[str]]:
    """Mark seeded group fixtures finished from the CSV.

    Returns (newly_finished, already_finished, unmatched_descriptions).
    """
    df = fetch_results_csv()
    df["date"] = pd.to_datetime(df["date"])
    df = df[(df["date"].dt.year == WC_YEAR) & (df["tournament"] == WC_TOURNAMENT)]
    df = df.dropna(subset=["home_score", "away_score"])

    # Index seeded group fixtures by unordered team pair.
    fixtures = (
        db.query(Match)
        .filter(Match.stage == MatchStage.GROUP)
        .all()
    )
    by_pair: dict[frozenset, Match] = {}
    for m in fixtures:
        by_pair[frozenset((m.home_team_id, m.away_team_id))] = m

    teams = {t.name: t for t in db.query(Team).all()}

    newly_finished = 0
    already_finished = 0
    unmatched: list[str] = []

    for _, row in df.iterrows():
        home_name = _canonical(row["home_team"])
        away_name = _canonical(row["away_team"])
        home = teams.get(home_name)
        away = teams.get(away_name)
        if not home or not away:
            unmatched.append(f"{row['home_team']} vs {row['away_team']} (team not found)")
            continue

        fixture = by_pair.get(frozenset((home.id, away.id)))
        if fixture is None:
            # Not a group-stage pairing (e.g. a knockout match) — skip for now.
            continue

        # Orient the CSV scores to the fixture's stored home/away order.
        if fixture.home_team_id == home.id:
            hs, as_ = int(row["home_score"]), int(row["away_score"])
        else:
            hs, as_ = int(row["away_score"]), int(row["home_score"])

        if (
            fixture.is_finished
            and fixture.home_score == hs
            and fixture.away_score == as_
        ):
            already_finished += 1
            continue

        fixture.home_score = hs
        fixture.away_score = as_
        fixture.is_finished = True
        newly_finished += 1

    db.commit()
    return newly_finished, already_finished, unmatched


def main() -> None:
    db = SessionLocal()
    try:
        new, existing, unmatched = apply_results(db)
        print(
            f"Applied WC results: {new} newly finished, {existing} already up to date, "
            f"{len(unmatched)} unmatched"
        )
        for u in unmatched:
            print(f"  unmatched: {u}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
