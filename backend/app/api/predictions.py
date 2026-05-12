from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.auth import current_user
from app.db import get_db
from app.models.match import Match, MatchStage
from app.models.prediction import ModelPrediction, UserTip
from app.models.user import User
from app.prediction.ensemble import predict_match

router = APIRouter(prefix="/predictions", tags=["predictions"])


class PredictionOut(BaseModel):
    match_id: int
    p_home: float
    p_draw: float
    p_away: float
    expected_home_goals: float
    expected_away_goals: float
    most_likely_score: tuple[int, int]


def _most_likely_score(lam_h: float, lam_a: float) -> tuple[int, int]:
    return (round(lam_h), round(lam_a))


def _compute_and_persist(db: Session, match: Match) -> PredictionOut:
    pred = predict_match(db, match)
    record = ModelPrediction(
        match_id=match.id,
        p_home=pred.p_home,
        p_draw=pred.p_draw,
        p_away=pred.p_away,
        expected_home_goals=pred.expected_home_goals,
        expected_away_goals=pred.expected_away_goals,
        computed_at=datetime.utcnow(),
    )
    db.add(record)
    db.commit()
    return PredictionOut(
        match_id=match.id,
        p_home=pred.p_home,
        p_draw=pred.p_draw,
        p_away=pred.p_away,
        expected_home_goals=pred.expected_home_goals,
        expected_away_goals=pred.expected_away_goals,
        most_likely_score=_most_likely_score(pred.expected_home_goals, pred.expected_away_goals),
    )


@router.post("/match/{match_id}", response_model=PredictionOut)
def predict_single(match_id: int, db: Session = Depends(get_db)) -> PredictionOut:
    match = db.get(Match, match_id)
    if match is None:
        raise HTTPException(404, "Match not found")
    return _compute_and_persist(db, match)


@router.post("/group/{group}", response_model=list[PredictionOut])
def predict_group(group: str, db: Session = Depends(get_db)) -> list[PredictionOut]:
    matches = (
        db.query(Match)
        .filter(Match.group == group, Match.stage == MatchStage.GROUP)
        .order_by(Match.kickoff)
        .all()
    )
    return [_compute_and_persist(db, m) for m in matches]


@router.post("/groups/all", response_model=list[PredictionOut])
def predict_all_groups(db: Session = Depends(get_db)) -> list[PredictionOut]:
    matches = (
        db.query(Match)
        .filter(Match.stage == MatchStage.GROUP)
        .order_by(Match.kickoff)
        .all()
    )
    return [_compute_and_persist(db, m) for m in matches]


@router.post("/stage/{stage}", response_model=list[PredictionOut])
def predict_stage(stage: str, db: Session = Depends(get_db)) -> list[PredictionOut]:
    try:
        stage_enum = MatchStage(stage)
    except ValueError as e:
        raise HTTPException(400, f"Unknown stage '{stage}'") from e
    matches = db.query(Match).filter(Match.stage == stage_enum).order_by(Match.kickoff).all()
    return [_compute_and_persist(db, m) for m in matches]


# --- User tips ----------------------------------------------------------------

class TipIn(BaseModel):
    home_score: int
    away_score: int


class TipOut(BaseModel):
    match_id: int
    home_score: int
    away_score: int
    points: int | None


@router.post("/tip/{match_id}", response_model=TipOut)
def submit_tip(
    match_id: int,
    tip: TipIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> TipOut:
    match = db.get(Match, match_id)
    if match is None:
        raise HTTPException(404, "Match not found")
    existing = (
        db.query(UserTip)
        .filter(UserTip.user_id == user.id, UserTip.match_id == match_id)
        .first()
    )
    if existing:
        existing.home_score = tip.home_score
        existing.away_score = tip.away_score
    else:
        existing = UserTip(
            user_id=user.id,
            match_id=match_id,
            home_score=tip.home_score,
            away_score=tip.away_score,
        )
        db.add(existing)
    db.commit()
    return TipOut(
        match_id=match_id,
        home_score=existing.home_score,
        away_score=existing.away_score,
        points=existing.points,
    )


@router.get("/tips/mine", response_model=list[TipOut])
def my_tips(db: Session = Depends(get_db), user: User = Depends(current_user)) -> list[TipOut]:
    tips = db.query(UserTip).filter(UserTip.user_id == user.id).all()
    return [TipOut(match_id=t.match_id, home_score=t.home_score, away_score=t.away_score, points=t.points) for t in tips]
