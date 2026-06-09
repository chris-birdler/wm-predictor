"""Full data refresh pipeline for the WM Predictor.

Runs the complete chain in a single process so a scheduler only needs one
entrypoint:

    1. ingest_odds        -> pull fresh 1X2 odds snapshots from The Odds API
    2. recompute (Elo)    -> refetch the historical results CSV (new results
                             that happened since the last run land here),
                             replay Elo chronologically, recompute attack/
                             defense rates
    3. predict_all_groups -> re-predict all 72 group matches with the fresh
                             odds + Elo
    4. auto_fill          -> rebuild the entire R32 -> Final knockout bracket
    5. run_simulation     -> re-run the Monte Carlo tournament simulation

Run inside the backend container:

    python -m app.data.refresh_all

Intended to be invoked by cron every 6 hours (see scripts/refresh.sh).

Each step is wrapped so a failure in one stage is logged but does not abort
the whole run where it is safe to continue. Odds-ingestion failures (e.g. the
external API being down or out of quota) are non-fatal: the rest of the
pipeline still recomputes with whatever odds are already stored.
"""

import asyncio
import sys
import traceback
from datetime import datetime

from app.api.bracket import auto_fill
from app.api.predictions import predict_all_groups
from app.api.simulation import run_simulation
from app.data.apply_results import apply_results
from app.data.odds_ingestor import ingest_odds
from app.data.recompute_elo import recompute
from app.db import SessionLocal


def _log(msg: str) -> None:
    print(f"[{datetime.utcnow().isoformat(timespec='seconds')}Z] {msg}", flush=True)


def main() -> int:
    _log("=== refresh_all START ===")
    failures: list[str] = []

    # 1. Fresh odds (non-fatal: external API may be down / out of quota).
    db = SessionLocal()
    try:
        inserted, matched, unmatched = asyncio.run(ingest_odds(db))
        _log(
            f"[odds] inserted {inserted} snapshots for {matched} matches; "
            f"{len(unmatched)} unmatched events"
        )
    except Exception as e:  # noqa: BLE001 - keep going with existing odds
        failures.append("odds")
        _log(f"[odds] FAILED: {e!r} (continuing with stored odds)")
        traceback.print_exc()
    finally:
        db.close()

    # 2. New results + Elo replay + attack/defense (opens its own session).
    try:
        recompute()
        _log("[elo] recompute done (results refetched, Elo + rates updated)")
    except Exception as e:  # noqa: BLE001
        failures.append("elo")
        _log(f"[elo] FAILED: {e!r}")
        traceback.print_exc()

    # 3. Write real WC results onto the seeded fixtures (mark them finished).
    db = SessionLocal()
    try:
        new, existing, unmatched = apply_results(db)
        _log(
            f"[results] {new} fixtures newly finished, {existing} already up to date, "
            f"{len(unmatched)} unmatched"
        )
    except Exception as e:  # noqa: BLE001
        failures.append("results")
        _log(f"[results] FAILED: {e!r}")
        traceback.print_exc()
    finally:
        db.close()

    # 4-6. Predictions -> bracket -> simulation share one session.
    db = SessionLocal()
    try:
        preds = predict_all_groups(db)
        _log(f"[predict] re-predicted {len(preds)} group matches")

        result = auto_fill(db)
        _log(
            f"[bracket] auto-filled stages {result.stages_seeded}; "
            f"champion_team_id={result.champion_team_id}"
        )

        sim = run_simulation(0, db)
        top = sim.teams[0] if sim.teams else None
        _log(
            f"[sim] run_id={sim.run_id} n_runs={sim.n_runs}"
            + (f"; favourite={top.name} ({top.p_winner:.1%})" if top else "")
        )
    except Exception as e:  # noqa: BLE001
        failures.append("predict/bracket/sim")
        _log(f"[predict/bracket/sim] FAILED: {e!r}")
        traceback.print_exc()
    finally:
        db.close()

    if failures:
        _log(f"=== refresh_all DONE with failures: {failures} ===")
        return 1
    _log("=== refresh_all DONE ok ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
