from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.db import get_db
from app.models.match import Match, MatchStage
from app.models.simulation import SimulationRun, TeamSimulationResult
from app.models.team import Team
from app.prediction.ensemble import predict_match
from app.simulation.monte_carlo import run_monte_carlo

router = APIRouter(prefix="/simulation", tags=["simulation"])


class TeamProbs(BaseModel):
    team_id: int
    name: str
    fifa_code: str
    p_advance_group: float
    p_r16: float
    p_qf: float
    p_sf: float
    p_final: float
    p_winner: float


class SimulationResponse(BaseModel):
    run_id: int
    n_runs: int
    teams: list[TeamProbs]


@router.post("/run", response_model=SimulationResponse)
def run_simulation(n_runs: int = 0, db: Session = Depends(get_db)) -> SimulationResponse:
    n = n_runs or settings.MC_DEFAULT_RUNS

    group_matches_q = (
        db.query(Match)
        .options(joinedload(Match.home_team), joinedload(Match.away_team))
        .filter(Match.stage == MatchStage.GROUP)
        .order_by(Match.group, Match.kickoff)
        .all()
    )
    # Restrict to the 48 WC 2026 teams (Team.group is set only on seeded
    # tournament participants) so historical-only teams don't appear in the
    # simulation table with 0% probabilities everywhere.
    teams_by_id: dict[int, Team] = {
        t.id: t for t in db.query(Team).filter(Team.group.isnot(None)).all()
    }

    group_matches: dict[str, list] = {}
    for m in group_matches_q:
        pred = predict_match(db, m)
        group_matches.setdefault(m.group or "?", []).append(
            (m.home_team_id, m.away_team_id, pred)
        )

    # Pre-compute predictions for every possible knockout pairing once.
    # Without this, the MC loop hits the DB ~30 times per simulation per pairing,
    # which scales to hundreds of thousands of queries for 10k runs.
    ko_cache: dict[tuple[int, int], object] = {}

    def knockout_pred_fn(team_a: int, team_b: int):
        key = (team_a, team_b)
        if key not in ko_cache:
            synthetic = Match(
                home_team_id=team_a,
                away_team_id=team_b,
                kickoff=group_matches_q[-1].kickoff,
                stage=MatchStage.R16,
                group=None,
            )
            synthetic.home_team = teams_by_id[team_a]
            synthetic.away_team = teams_by_id[team_b]
            ko_cache[key] = predict_match(db, synthetic)
        return ko_cache[key]

    team_ids = list(teams_by_id.keys())
    results = run_monte_carlo(
        n_runs=n,
        team_ids=team_ids,
        group_matches=group_matches,
        knockout_pred_fn=knockout_pred_fn,
    )

    run = SimulationRun(n_runs=n, model_name="ensemble")
    db.add(run)
    db.flush()
    rows: list[TeamProbs] = []
    for tid, stages in results.items():
        team = teams_by_id[tid]
        tsr = TeamSimulationResult(
            run_id=run.id,
            team_id=tid,
            p_advance_group=stages.get("r32", 0),
            p_r16=stages.get("r16", 0),
            p_qf=stages.get("qf", 0),
            p_sf=stages.get("sf", 0),
            p_final=stages.get("final", 0),
            p_winner=stages.get("winner", 0),
        )
        db.add(tsr)
        rows.append(
            TeamProbs(
                team_id=tid,
                name=team.name,
                fifa_code=team.fifa_code,
                p_advance_group=stages.get("r32", 0),
                p_r16=stages.get("r16", 0),
                p_qf=stages.get("qf", 0),
                p_sf=stages.get("sf", 0),
                p_final=stages.get("final", 0),
                p_winner=stages.get("winner", 0),
            )
        )
    db.commit()
    rows.sort(key=lambda r: r.p_winner, reverse=True)
    return SimulationResponse(run_id=run.id, n_runs=n, teams=rows)
