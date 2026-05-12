"""Head-to-head: direct match record between two teams."""

from datetime import datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models.match import Match

H2H_WINDOW = 10


def h2h_probs(db: Session, home_id: int, away_id: int, as_of: datetime) -> tuple[float, float, float]:
    """Return (p_home, p_draw, p_away) from direct-match history.

    If no history, returns a neutral (0.40, 0.27, 0.33) prior reflecting modest
    home advantage; otherwise an additively-smoothed Laplace estimate.
    """
    stmt = (
        select(Match)
        .where(
            Match.is_finished.is_(True),
            Match.kickoff < as_of,
            or_(
                and_(Match.home_team_id == home_id, Match.away_team_id == away_id),
                and_(Match.home_team_id == away_id, Match.away_team_id == home_id),
            ),
        )
        .order_by(Match.kickoff.desc())
        .limit(H2H_WINDOW)
    )
    matches = db.execute(stmt).scalars().all()
    if not matches:
        return (0.40, 0.27, 0.33)

    wins_home, draws, wins_away = 1, 1, 1
    for m in matches:
        if m.home_score is None or m.away_score is None:
            continue
        is_home_at_home = m.home_team_id == home_id
        gf = m.home_score if is_home_at_home else m.away_score
        ga = m.away_score if is_home_at_home else m.home_score
        if gf > ga:
            wins_home += 1
        elif gf < ga:
            wins_away += 1
        else:
            draws += 1
    total = wins_home + draws + wins_away
    return (wins_home / total, draws / total, wins_away / total)
