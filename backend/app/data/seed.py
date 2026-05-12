"""Seed the database with WM 2026 teams + group-stage match schedule.

Run inside the backend container:
    python -m app.data.seed
"""

from datetime import datetime, timedelta
from itertools import combinations

from app.data.wc2026_groups import TEAMS_BY_GROUP
from app.db import Base, SessionLocal, engine
from app.models.match import Match, MatchStage, MatchType
from app.models.team import Team


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        wc_teams = db.query(Team).filter(Team.group.isnot(None)).count()
        if wc_teams > 0:
            print("WM teams already seeded — clearing WM matches and WM teams")
            db.query(Match).filter(Match.group.isnot(None)).delete()
            db.query(Team).filter(Team.group.isnot(None)).delete()
            db.commit()

        teams_by_group: dict[str, list[Team]] = {}
        for letter, seeded_teams in TEAMS_BY_GROUP.items():
            teams_by_group[letter] = []
            for st in seeded_teams:
                t = Team(
                    name=st.name,
                    fifa_code=st.fifa_code,
                    confederation=st.confederation,
                    group=letter,
                    elo=st.initial_elo,
                    is_host=st.is_host,
                )
                db.add(t)
                teams_by_group[letter].append(t)
        db.commit()

        start = datetime(2026, 6, 11, 18, 0)
        slot = 0
        for letter in sorted(teams_by_group):
            teams = teams_by_group[letter]
            for home, away in combinations(teams, 2):
                kickoff = start + timedelta(hours=slot * 3)
                db.add(
                    Match(
                        home_team_id=home.id,
                        away_team_id=away.id,
                        kickoff=kickoff,
                        match_type=MatchType.WORLDCUP,
                        stage=MatchStage.GROUP,
                        group=letter,
                    )
                )
                slot += 1
        db.commit()
        n_teams = db.query(Team).filter(Team.group.isnot(None)).count()
        n_matches = db.query(Match).filter(Match.group.isnot(None)).count()
        print(f"Seeded {n_teams} WM teams, {n_matches} group matches.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
