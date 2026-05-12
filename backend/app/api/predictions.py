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


def _predicted_score(
    lam_h: float,
    lam_a: float,
    p_h: float,
    p_d: float,
    p_a: float,
) -> tuple[int, int]:
    """Scoreline from team-rate model, constrained to the ensemble's winner.

    Start from round(λ_h), round(λ_a) — what the team-rate Poisson model
    expects on average. If that already produces the same winner as
    argmax(p_h, p_d, p_a) from the ensemble, return it. Otherwise pick the
    integer scoreline (closest in L2 distance to (λ_h, λ_a)) that respects
    the ensemble winner — minimum tweak to remove the contradiction.

    Result: predicted score never disagrees with the W/D/L probability bar,
    while the goal counts still reflect the team-rate Poisson means.
    """
    if p_h >= p_d and p_h >= p_a:
        winner = 1   # home wins → h > a
    elif p_a >= p_d:
        winner = -1  # away wins → a > h
    else:
        winner = 0   # draw → h == a

    h_base = round(lam_h)
    a_base = round(lam_a)
    base_winner = 1 if h_base > a_base else -1 if a_base > h_base else 0
    if base_winner == winner:
        return h_base, a_base

    best = (1, 0) if winner == 1 else (0, 1) if winner == -1 else (0, 0)
    best_dev = float("inf")
    for h in range(8):
        for a in range(8):
            if winner == 1 and h <= a:
                continue
            if winner == -1 and a <= h:
                continue
            if winner == 0 and h != a:
                continue
            dev = (h - lam_h) ** 2 + (a - lam_a) ** 2
            if dev < best_dev:
                best_dev = dev
                best = (h, a)
    return best


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
        predicted_score=_predicted_score(
            pred.expected_home_goals,
            pred.expected_away_goals,
            pred.p_home,
            pred.p_draw,
            pred.p_away,
        ),
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
