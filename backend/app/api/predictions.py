import math
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.match import Match, MatchStage
from app.models.prediction import ModelPrediction
from app.prediction.ensemble import predict_match

router = APIRouter(prefix="/predictions", tags=["predictions"])


KO_STAGES = {
    MatchStage.R32,
    MatchStage.R16,
    MatchStage.QF,
    MatchStage.SF,
    MatchStage.THIRD,
    MatchStage.FINAL,
}


class PredictionOut(BaseModel):
    match_id: int
    p_home: float
    p_draw: float
    p_away: float
    expected_home_goals: float
    expected_away_goals: float
    predicted_score: tuple[int, int]
    # KO matches: filled in when 90' is a draw. `extra_time_score` is the
    # cumulative score after 120' (regulation + ET). `penalty_score` is set
    # only when ET also ended level — the shootout result, displayed as
    # "1:1 i.E. 4:3" in standard German football notation.
    extra_time_score: tuple[int, int] | None = None
    penalty_score: tuple[int, int] | None = None
    has_odds: bool  # bookmaker odds were used as one of the ensemble components


def _predicted_score(
    lam_h: float,
    lam_a: float,
    p_h: float,
    p_d: float,
    p_a: float,
) -> tuple[int, int]:
    """Scoreline from team-rate model, constrained to the ensemble's winner.

    Start from floor(λ_h), floor(λ_a) — the mode of independent Poissons,
    not the rounded mean. With λ_underdog typically in 0.5–0.9, floor(0.74)
    is 0, producing 1:0 / 2:0 scorelines that match real football
    distributions, while round(0.74) = 1 forces every match to give the
    underdog at least a goal.

    If the mode already produces the same winner as the ensemble's
    preferred outcome, return it. Otherwise pick the integer scoreline
    closest in L2 distance to (λ_h, λ_a) that respects that outcome.

    Draws are picked when `p_draw` is within 15pp of the leader. Pure
    argmax under-counts draws because the ensemble's `p_draw` rarely
    exceeds ~30% even in pick'em matches (typical close line: 38/30/32),
    yet a 1:1 is the right prediction for such matches. 15pp lands the
    overall draw share near the ~25–28% baseline seen in international
    tournaments.
    """
    leader = max(p_h, p_d, p_a)
    if p_d >= leader - 0.15:
        winner = 0   # draw → h == a
    elif p_h >= p_a:
        winner = 1   # home wins → h > a
    else:
        winner = -1  # away wins → a > h

    h_base = math.floor(lam_h)
    a_base = math.floor(lam_a)
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


def _ko_extension(
    score: tuple[int, int],
    lam_h: float,
    lam_a: float,
    p_h: float,
    p_a: float,
) -> tuple[tuple[int, int] | None, tuple[int, int] | None]:
    """For a KO match whose 90' ended level, predict the ET total and
    (if still tied) the penalty-shootout result.

    Step 1 — baseline ET goals via Poisson mode at half rate (30 min ≈
    half a regulation match). Step 2 — if ET still tied, the 1X2 edge
    breaks it: a clear favourite (>5pp gap on home/away, ignoring the
    draw column) scores the decisive ET goal; an essentially level
    1X2 (<5pp gap) goes to penalties. This produces a realistic mix
    instead of routing every KO draw to a shootout."""
    h, a = score
    et_h = h + math.floor(lam_h / 2)
    et_a = a + math.floor(lam_a / 2)
    if et_h != et_a:
        return (et_h, et_a), None
    if p_h - p_a >= 0.05:
        return (et_h + 1, et_a), None
    if p_a - p_h >= 0.05:
        return (et_h, et_a + 1), None
    pen = (4, 3) if p_h >= p_a else (3, 4)
    return (et_h, et_a), pen


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

    score = _predicted_score(
        pred.expected_home_goals,
        pred.expected_away_goals,
        pred.p_home,
        pred.p_draw,
        pred.p_away,
    )
    et_score: tuple[int, int] | None = None
    pen_score: tuple[int, int] | None = None
    if match.stage in KO_STAGES and score[0] == score[1]:
        et_score, pen_score = _ko_extension(
            score,
            pred.expected_home_goals,
            pred.expected_away_goals,
            pred.p_home,
            pred.p_away,
        )

    return PredictionOut(
        match_id=match.id,
        p_home=pred.p_home,
        p_draw=pred.p_draw,
        p_away=pred.p_away,
        expected_home_goals=pred.expected_home_goals,
        expected_away_goals=pred.expected_away_goals,
        predicted_score=score,
        extra_time_score=et_score,
        penalty_score=pen_score,
        has_odds="odds" in pred.components,
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
