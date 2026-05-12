from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.match import Match, MatchStage
from app.models.prediction import ModelPrediction
from app.prediction.ensemble import predict_match

router = APIRouter(prefix="/predictions", tags=["predictions"])


class PredictionOut(BaseModel):
    match_id: int
    p_home: float
    p_draw: float
    p_away: float
    expected_home_goals: float
    expected_away_goals: float
    predicted_score: tuple[int, int]


def _predicted_score(lam_h: float, lam_a: float) -> tuple[int, int]:
    """Predicted scoreline = rounded expected goals.

    With team rates fitted by iterative MLE, λ spreads widely enough (0.5 to
    3.5+) that simple rounding already produces a diverse, sensible
    distribution: top-vs-mid → 2:1 or 3:1, top-vs-weak → 3:0 or 4:0,
    top-vs-top → 1:1, mid-vs-mid → 1:1 or 2:1. Random Poisson sampling per
    match was tried but produced rare upsets that contradicted the win
    probabilities (e.g. a heavily-favoured team predicted to lose), confusing
    the UX. Rounding the mean reflects what the model actually expects.
    """
    return round(lam_h), round(lam_a)


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
        predicted_score=_predicted_score(pred.expected_home_goals, pred.expected_away_goals),
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
