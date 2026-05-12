import math
import random
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


def _poisson_sample(rng: random.Random, lam: float, cap: int = 9) -> int:
    """Sample from Poisson(lam) via inverse CDF. Bounded for safety."""
    u = rng.random()
    cum = 0.0
    p = math.exp(-lam)
    for k in range(cap):
        cum += p
        if u < cum:
            return k
        p *= lam / (k + 1)
    return cap


def _predicted_score(match_id: int, lam_h: float, lam_a: float) -> tuple[int, int]:
    """Deterministic Poisson sample seeded by match id.

    Rounding the mean or taking the joint mode collapses to (1,1) or (2,1) for
    almost every WC match because λ_h and λ_a both sit in 1–2 for teams of
    similar strength. Sampling captures the natural variance of football
    scorelines (many 1:0, 2:0, 0:0, 2:2 etc.) while remaining stable across
    requests by seeding the RNG with the match id.
    """
    rng = random.Random(match_id)
    return _poisson_sample(rng, lam_h), _poisson_sample(rng, lam_a)


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
        predicted_score=_predicted_score(match.id, pred.expected_home_goals, pred.expected_away_goals),
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
