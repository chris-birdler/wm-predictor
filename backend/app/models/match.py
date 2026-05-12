import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.team import Team


class MatchType(str, enum.Enum):
    WORLDCUP = "worldcup"
    CONTINENTAL = "continental"
    QUALIFIER = "qualifier"
    NATIONS = "nations"
    NATIONS_FINALS = "nations_finals"
    FRIENDLY = "friendly"


class MatchStage(str, enum.Enum):
    GROUP = "group"
    R32 = "r32"
    R16 = "r16"
    QF = "qf"
    SF = "sf"
    THIRD = "third"
    FINAL = "final"
    OTHER = "other"


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    home_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    away_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    kickoff: Mapped[datetime] = mapped_column(DateTime, index=True)
    match_type: Mapped[MatchType] = mapped_column(Enum(MatchType), default=MatchType.WORLDCUP)
    stage: Mapped[MatchStage] = mapped_column(Enum(MatchStage), default=MatchStage.GROUP)
    group: Mapped[str | None] = mapped_column(String(1), nullable=True, index=True)
    home_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_finished: Mapped[bool] = mapped_column(default=False)
    venue: Mapped[str | None] = mapped_column(String(64), nullable=True)

    home_team: Mapped[Team] = relationship(Team, foreign_keys=[home_team_id])
    away_team: Mapped[Team] = relationship(Team, foreign_keys=[away_team_id])
