"""Materialize knockout fixtures from previous-stage predictions.

Lets the UI walk a deterministic single-tournament path: predict groups →
seed R32 from standings (using the official FIFA 2026 slotting cascade) →
predict R32 → seed R16 from R32 winners (chained via KO_PROGRESSION) → …

Each KO Match row stores its `fifa_match_no` (73..104) so subsequent stages
can chain via `app.data.wc2026_bracket.KO_PROGRESSION`.
"""

from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

import math

from app.api.predictions import PredictionOut, _compute_and_persist, _predicted_score
from app.data.wc2026_bracket import (
    FINAL_MATCH,
    KO_PROGRESSION,
    KO_STAGE_MATCHES,
    QF_MATCHES,
    R16_MATCHES,
    R32_MATCHES,
    SF_MATCHES,
    THIRD_FROM_LOSERS,
    THIRD_MATCH,
    assemble_r32,
)
from app.db import get_db
from app.models.match import Match, MatchStage, MatchType
from app.models.prediction import ModelPrediction

router = APIRouter(prefix="/bracket", tags=["bracket"])

KO_STAGES = ["r32", "r16", "qf", "sf", "final", "third"]
NEXT_STAGE = {"r32": "r16", "r16": "qf", "qf": "sf", "sf": "final"}
PREV_STAGE = {v: k for k, v in NEXT_STAGE.items()}

_KO_KICKOFF_BASE = {
    "r32":   datetime(2026, 6, 28, 18, 0),
    "r16":   datetime(2026, 7, 4, 18, 0),
    "qf":    datetime(2026, 7, 9, 18, 0),
    "sf":    datetime(2026, 7, 14, 18, 0),
    "third": datetime(2026, 7, 18, 18, 0),
    "final": datetime(2026, 7, 19, 18, 0),
}


def _latest_predictions(db: Session, match_ids: list[int]) -> dict[int, ModelPrediction]:
    out: dict[int, ModelPrediction] = {}
    rows = (
        db.query(ModelPrediction)
        .filter(ModelPrediction.match_id.in_(match_ids))
        .order_by(ModelPrediction.match_id, desc(ModelPrediction.computed_at))
        .all()
    )
    for r in rows:
        if r.match_id not in out:
            out[r.match_id] = r
    return out


def _winner_team_id(match: Match, pred: ModelPrediction) -> int:
    h, a = _predicted_score(
        pred.expected_home_goals, pred.expected_away_goals,
        pred.p_home, pred.p_draw, pred.p_away,
    )
    if h > a:
        return match.home_team_id
    if a > h:
        return match.away_team_id
    # 90' draw → extra time. Baseline ET goals via half-rate Poisson mode,
    # then the 1X2 edge resolves residual ties (clear favourite wins in ET;
    # near-level 1X2 goes to penalties, where the slight favourite still
    # wins). Mirrors `_ko_extension` in predictions.py.
    et_h = math.floor(pred.expected_home_goals / 2)
    et_a = math.floor(pred.expected_away_goals / 2)
    if et_h > et_a:
        return match.home_team_id
    if et_a > et_h:
        return match.away_team_id
    return match.home_team_id if pred.p_home >= pred.p_away else match.away_team_id


def _loser_team_id(match: Match, pred: ModelPrediction) -> int:
    winner = _winner_team_id(match, pred)
    return match.away_team_id if winner == match.home_team_id else match.home_team_id


def _compute_group_standings(
    db: Session,
) -> tuple[dict[str, int], dict[str, int], dict[str, int]]:
    """Returns (top1, top2, best_thirds) — each is {group_letter: team_id}.
    `top1`/`top2` cover all 12 groups; `best_thirds` has exactly 8 entries.
    """
    group_matches = (
        db.query(Match)
        .filter(Match.stage == MatchStage.GROUP)
        .order_by(Match.group, Match.kickoff)
        .all()
    )
    if not group_matches:
        raise HTTPException(400, "No group matches seeded.")
    preds = _latest_predictions(db, [m.id for m in group_matches])
    missing = [m.id for m in group_matches if m.id not in preds]
    if missing:
        raise HTTPException(
            400,
            f"{len(missing)} group matches not predicted yet. Predict groups first.",
        )

    standings: dict[str, dict[int, dict]] = defaultdict(dict)
    for m in group_matches:
        h, a = _predicted_score(
            preds[m.id].expected_home_goals, preds[m.id].expected_away_goals,
            preds[m.id].p_home, preds[m.id].p_draw, preds[m.id].p_away,
        )
        for tid in (m.home_team_id, m.away_team_id):
            if tid not in standings[m.group]:
                standings[m.group][tid] = {"team_id": tid, "pts": 0, "gd": 0, "gf": 0}
        standings[m.group][m.home_team_id]["gf"] += h
        standings[m.group][m.away_team_id]["gf"] += a
        standings[m.group][m.home_team_id]["gd"] += h - a
        standings[m.group][m.away_team_id]["gd"] += a - h
        if h > a:
            standings[m.group][m.home_team_id]["pts"] += 3
        elif a > h:
            standings[m.group][m.away_team_id]["pts"] += 3
        else:
            standings[m.group][m.home_team_id]["pts"] += 1
            standings[m.group][m.away_team_id]["pts"] += 1

    top1: dict[str, int] = {}
    top2: dict[str, int] = {}
    third_pool: list[dict] = []
    for group in sorted(standings.keys()):
        sorted_t = sorted(
            standings[group].values(),
            key=lambda t: (t["pts"], t["gd"], t["gf"]),
            reverse=True,
        )
        if len(sorted_t) >= 2:
            top1[group] = sorted_t[0]["team_id"]
            top2[group] = sorted_t[1]["team_id"]
        if len(sorted_t) >= 3:
            third_pool.append({**sorted_t[2], "group": group})

    best_thirds = sorted(
        third_pool, key=lambda t: (t["pts"], t["gd"], t["gf"]), reverse=True
    )[:8]
    thirds = {t["group"]: t["team_id"] for t in best_thirds}
    if len(thirds) != 8 or len(top1) != 12 or len(top2) != 12:
        raise HTTPException(
            500, f"Group standings incomplete: top1={len(top1)} top2={len(top2)} thirds={len(thirds)}"
        )
    return top1, top2, thirds


def _delete_ko_from(db: Session, from_stage: str) -> None:
    idx = KO_STAGES.index(from_stage)
    stages = [MatchStage(s) for s in KO_STAGES[idx:]]
    match_ids = [
        mid for (mid,) in db.query(Match.id).filter(Match.stage.in_(stages)).all()
    ]
    if not match_ids:
        return
    db.query(ModelPrediction).filter(
        ModelPrediction.match_id.in_(match_ids)
    ).delete(synchronize_session=False)
    db.query(Match).filter(Match.id.in_(match_ids)).delete(synchronize_session=False)


def _ko_kickoff(stage: str, fifa_match_no: int) -> datetime:
    """Order kickoffs by FIFA match number so DB queries sort the same way."""
    base = _KO_KICKOFF_BASE[stage]
    offset = fifa_match_no - KO_STAGE_MATCHES[stage][0]
    return base + timedelta(hours=offset * 6)


def _create_ko_match(
    db: Session, stage: str, fifa_match_no: int, home: int, away: int
) -> Match:
    m = Match(
        home_team_id=home,
        away_team_id=away,
        kickoff=_ko_kickoff(stage, fifa_match_no),
        match_type=MatchType.WORLDCUP,
        stage=MatchStage(stage),
        group=None,
        fifa_match_no=fifa_match_no,
    )
    db.add(m)
    return m


class SeedResult(BaseModel):
    stage: str
    created: int


@router.post("/seed-r32", response_model=SeedResult)
def seed_r32(db: Session = Depends(get_db)) -> SeedResult:
    top1, top2, thirds = _compute_group_standings(db)
    fixtures = assemble_r32(top1, top2, thirds)  # [(match_no, home, away), ...]
    _delete_ko_from(db, "r32")
    for match_no, home, away in fixtures:
        _create_ko_match(db, "r32", match_no, home, away)
    db.commit()
    return SeedResult(stage="r32", created=len(fixtures))


@router.post("/seed-next/{stage}", response_model=SeedResult)
def seed_next(stage: str, db: Session = Depends(get_db)) -> SeedResult:
    if stage not in PREV_STAGE:
        raise HTTPException(400, "stage must be r16, qf, sf, or final")
    prev = PREV_STAGE[stage]
    prev_matches = (
        db.query(Match)
        .filter(Match.stage == MatchStage(prev))
        .all()
    )
    if not prev_matches:
        raise HTTPException(400, f"No {prev} matches. Seed and predict {prev} first.")
    if any(m.fifa_match_no is None for m in prev_matches):
        raise HTTPException(
            400,
            f"{prev} matches missing fifa_match_no. Re-seed from R32.",
        )
    preds = _latest_predictions(db, [m.id for m in prev_matches])
    missing = [m.id for m in prev_matches if m.id not in preds]
    if missing:
        raise HTTPException(
            400,
            f"{len(missing)} {prev} matches not predicted yet. Predict {prev} first.",
        )

    by_fifa_no: dict[int, Match] = {m.fifa_match_no: m for m in prev_matches}
    winners_by_match: dict[int, int] = {
        fno: _winner_team_id(m, preds[m.id]) for fno, m in by_fifa_no.items()
    }

    _delete_ko_from(db, stage)
    target_match_nos = KO_STAGE_MATCHES[stage]
    for match_no in target_match_nos:
        prev_a, prev_b = KO_PROGRESSION[match_no]
        if prev_a not in winners_by_match or prev_b not in winners_by_match:
            raise HTTPException(
                500,
                f"Can't seed match {match_no}: missing winners for {prev_a}/{prev_b}",
            )
        _create_ko_match(
            db,
            stage,
            match_no,
            winners_by_match[prev_a],
            winners_by_match[prev_b],
        )
    created = len(target_match_nos)

    # Seed the 3rd-place playoff alongside the Final, from semifinal losers.
    if stage == "final":
        sf_a, sf_b = THIRD_FROM_LOSERS
        sf_a_match = by_fifa_no.get(sf_a)
        sf_b_match = by_fifa_no.get(sf_b)
        if sf_a_match is not None and sf_b_match is not None:
            loser_a = _loser_team_id(sf_a_match, preds[sf_a_match.id])
            loser_b = _loser_team_id(sf_b_match, preds[sf_b_match.id])
            _create_ko_match(db, "third", THIRD_MATCH, loser_a, loser_b)
            created += 1

    db.commit()
    return SeedResult(stage=stage, created=created)


class AutoFillResult(BaseModel):
    stages_seeded: list[str]
    champion_team_id: int | None = None
    predictions: list[PredictionOut]


@router.post("/auto-fill", response_model=AutoFillResult)
def auto_fill(db: Session = Depends(get_db)) -> AutoFillResult:
    """Walks R32 → Final from the existing group predictions.

    Requires that all group matches have already been predicted (Standings
    tab). Group predictions are not recomputed here — re-running the
    bracket should keep the group-stage baseline stable so the user's
    "predicted games" counter doesn't drift each click.
    """
    stages_done: list[str] = []
    out_preds: list[PredictionOut] = []

    # `seed_r32` calls `_compute_group_standings`, which raises 400 if
    # any group match is missing a prediction — preserving the contract
    # that groups must be filled before the knockout can be derived.
    seed_r32(db)
    stages_done.append("r32")

    for stage in KO_STAGES:
        cur = (
            db.query(Match)
            .filter(Match.stage == MatchStage(stage))
            .order_by(Match.kickoff, Match.id)
            .all()
        )
        for m in cur:
            out_preds.append(_compute_and_persist(db, m))
        next_stage = NEXT_STAGE.get(stage)
        if next_stage:
            seed_next(next_stage, db)
            stages_done.append(next_stage)
            if next_stage == "final":
                stages_done.append("third")  # seeded as side-effect of final

    final = (
        db.query(Match)
        .filter(Match.stage == MatchStage.FINAL)
        .order_by(Match.kickoff, Match.id)
        .first()
    )
    champion: int | None = None
    if final is not None:
        final_pred = _latest_predictions(db, [final.id]).get(final.id)
        if final_pred is not None:
            champion = _winner_team_id(final, final_pred)

    return AutoFillResult(
        stages_seeded=stages_done,
        champion_team_id=champion,
        predictions=out_preds,
    )
