from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class SimulationRun(Base):
    __tablename__ = "simulation_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    n_runs: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    model_name: Mapped[str] = mapped_column(String(32), default="ensemble")


class TeamSimulationResult(Base):
    __tablename__ = "team_simulation_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("simulation_runs.id"), index=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    p_advance_group: Mapped[float] = mapped_column(Float)
    p_r16: Mapped[float] = mapped_column(Float)
    p_qf: Mapped[float] = mapped_column(Float)
    p_sf: Mapped[float] = mapped_column(Float)
    p_final: Mapped[float] = mapped_column(Float)
    p_winner: Mapped[float] = mapped_column(Float)
