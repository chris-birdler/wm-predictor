from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    fifa_code: Mapped[str] = mapped_column(String(3), unique=True, index=True)
    confederation: Mapped[str] = mapped_column(String(16))
    group: Mapped[str | None] = mapped_column(String(1), nullable=True, index=True)
    elo: Mapped[float] = mapped_column(Float, default=1500.0)
    is_host: Mapped[bool] = mapped_column(default=False)
