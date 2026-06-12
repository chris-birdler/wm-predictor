"""Overwrite the seeded synthetic kickoffs with the real WC 2026 schedule.

app.data.seed lays down placeholder kickoffs (11 Jun + 3h per slot, packed
group-by-group) just so the fixtures have an ordering. This module replaces them
with the actual kick-off times from The Odds API /scores feed (the same feed used
for results), matched by unordered team pair. Run from the 6h refresh so the
schedule stays correct as the upstream feed firms up.

Times are stored as naive UTC, matching the rest of the app's datetime columns.

Run inside the backend container:
    python -m app.data.schedule_sync
"""

from datetime import datetime

from app.data.apply_results import _fetch_live_scores
from app.data.odds_ingestor import ODDS_NAME_ALIASES
from app.db import SessionLocal
from app.models.match import Match, MatchStage
from app.models.team import Team


def sync_schedule(db) -> tuple[int, list[str]]:
    """Set each group fixture's kickoff from the real schedule feed.

    Returns (updated_count, unmatched_event_descriptions).
    """
    events = _fetch_live_scores()

    fixtures = db.query(Match).filter(Match.stage == MatchStage.GROUP).all()
    by_pair: dict[frozenset, Match] = {
        frozenset((m.home_team_id, m.away_team_id)): m for m in fixtures
    }
    teams = {t.name: t for t in db.query(Team).all()}

    updated = 0
    unmatched: list[str] = []
    for ev in events:
        commence = ev.get("commence_time")
        if not commence:
            continue
        home_name, away_name = ev.get("home_team"), ev.get("away_team")
        home = teams.get(ODDS_NAME_ALIASES.get(home_name, home_name))
        away = teams.get(ODDS_NAME_ALIASES.get(away_name, away_name))
        if not home or not away:
            unmatched.append(f"{home_name} vs {away_name} (team not found)")
            continue

        fixture = by_pair.get(frozenset((home.id, away.id)))
        if fixture is None:
            continue

        kickoff = datetime.fromisoformat(commence.replace("Z", "+00:00")).replace(
            tzinfo=None
        )
        if fixture.kickoff != kickoff:
            fixture.kickoff = kickoff
            updated += 1

    db.commit()
    return updated, unmatched


def main() -> None:
    db = SessionLocal()
    try:
        updated, unmatched = sync_schedule(db)
        print(f"Synced schedule: {updated} kickoffs updated, {len(unmatched)} unmatched")
        for u in unmatched:
            print(f"  unmatched: {u}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
