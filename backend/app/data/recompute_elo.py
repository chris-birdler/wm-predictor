"""Reset all Elo ratings and replay historical results from scratch.

Run inside the backend container after changing K-factors or Elo math:
    docker compose exec backend python -m app.data.recompute_elo

Resets every team to 1500 (a uniform prior — the seeded `initial_elo` values
in wc2026_groups.py are deliberately ignored here so the replay isn't biased
by hand-picked starting ratings), deletes all finished matches (WC 2026
fixtures kept), then re-runs `ingest_historical` to refetch the CSV and
replay chronologically.
"""

from app.data.compute_attack_defense import compute as compute_attack_defense
from app.data.historical_ingestor import ingest_historical
from app.db import SessionLocal
from app.models.match import Match
from app.models.team import Team


def recompute() -> None:
    db = SessionLocal()
    try:
        n_teams = db.query(Team).update({Team.elo: 1500.0})
        deleted = db.query(Match).filter(Match.is_finished.is_(True)).delete()
        db.commit()
        print(f"Reset {n_teams} team ratings to 1500, deleted {deleted} finished matches")

        matches_added, teams_touched = ingest_historical(db)
        print(f"Replayed {matches_added} matches across {teams_touched} teams")

        n_rated, league_avg = compute_attack_defense(db)
        print(f"Computed attack/defense rates for {n_rated} teams (league avg = {league_avg:.3f} goals/team/match)")
    finally:
        db.close()


if __name__ == "__main__":
    recompute()
