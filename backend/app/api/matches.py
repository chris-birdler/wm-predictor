from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from app.db import get_db
from app.models.match import Match, MatchStage

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
    db: Session = Depends(get_db),
) -> list[MatchOut]:
    q = db.query(Match).options(joinedload(Match.home_team), joinedload(Match.away_team))
    if stage:
        try:
            q = q.filter(Match.stage == MatchStage(stage))
        except ValueError as e:
            raise HTTPException(400, f"Unknown stage '{stage}'") from e
    if group:
        q = q.filter(Match.group == group)
    return [_to_out(m) for m in q.order_by(Match.kickoff).all()]
