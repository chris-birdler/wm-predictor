from collections import defaultdict

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.team import Team

router = APIRouter(prefix="/teams", tags=["teams"])


class TeamOut(BaseModel):
    id: int
    name: str
    fifa_code: str
    confederation: str
    group: str | None
    elo: float
    is_host: bool

    class Config:
        from_attributes = True


@router.get("", response_model=list[TeamOut])
def list_teams(db: Session = Depends(get_db)) -> list[TeamOut]:
    return [TeamOut.model_validate(t) for t in db.query(Team).order_by(Team.group, Team.name).all()]


@router.get("/by-group")
def teams_by_group(db: Session = Depends(get_db)) -> dict[str, list[TeamOut]]:
    teams = db.query(Team).order_by(Team.group, Team.elo.desc()).all()
    groups: dict[str, list[TeamOut]] = defaultdict(list)
    for t in teams:
        if t.group:
            groups[t.group].append(TeamOut.model_validate(t))
    return dict(sorted(groups.items()))
