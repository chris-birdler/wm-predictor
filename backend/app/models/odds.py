from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column


from app.db import Base


class OddsSnapshot(Base):
    """One snapshot from one bookmaker for one match (1X2 market)."""

    __tablename__ = "odds_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), index=True)
    bookmaker: Mapped[str] = mapped_column(String(32), index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    odds_home: Mapped[float] = mapped_column(Float)
    odds_draw: Mapped[float] = mapped_column(Float)
    odds_away: Mapped[float] = mapped_column(Float)
