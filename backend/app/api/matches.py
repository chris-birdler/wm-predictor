from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from app.db import get_db
from app.models.match import Match, MatchStage, MatchType

router = APIRouter(prefix="/matches", tags=["matches"])


class TeamRef(BaseModel):
    id: int
    name: str
    fifa_code: str


class MatchOut(BaseModel):
    id: int
    kickoff: datetime
    stage: str
    group: str | None
    home: TeamRef
    away: TeamRef
    home_score: int | None
    away_score: int | None
    is_finished: bool


def _to_out(m: Match) -> MatchOut:
    return MatchOut(
        id=m.id,
        kickoff=m.kickoff,
        stage=m.stage.value,
        group=m.group,
        home=TeamRef(id=m.home_team.id, name=m.home_team.name, fifa_code=m.home_team.fifa_code),
        away=TeamRef(id=m.away_team.id, name=m.away_team.name, fifa_code=m.away_team.fifa_code),
        home_score=m.home_score,
        away_score=m.away_score,
        is_finished=m.is_finished,
    )


@router.get("", response_model=list[MatchOut])
def list_matches(
    stage: str | None = None,
    group: str | None = None,
    match_type: str | None = None,
    since: datetime | None = None,
    db: Session = Depends(get_db),
) -> list[MatchOut]:
    """List matches, optionally filtered.

    The DB holds ~32k historical matches (Elo training data) alongside the 104
    WC 2026 fixtures. An unfiltered call therefore returns a ~7.5 MB payload —
    so callers that only want the tournament must filter. The Knockout page
    uses `match_type=worldcup&since=2026-01-01`, which isolates exactly the 104
    seeded fixtures (`match_type=worldcup` alone still includes past World
    Cups; `since` alone still includes 2026 qualifiers/friendlies).
    """
    q = db.query(Match).options(joinedload(Match.home_team), joinedload(Match.away_team))
    if stage:
        try:
            q = q.filter(Match.stage == MatchStage(stage))
        except ValueError as e:
            raise HTTPException(400, f"Unknown stage '{stage}'") from e
    if group:
        q = q.filter(Match.group == group)
    if match_type:
        try:
            q = q.filter(Match.match_type == MatchType(match_type))
        except ValueError as e:
            raise HTTPException(400, f"Unknown match_type '{match_type}'") from e
    if since is not None:
        q = q.filter(Match.kickoff >= since)
    return [_to_out(m) for m in q.order_by(Match.kickoff).all()]
