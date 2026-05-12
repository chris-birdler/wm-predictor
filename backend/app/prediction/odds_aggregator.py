"""Aggregate 1X2 odds across bookmakers into fair (overround-free) probabilities."""

from dataclasses import dataclass
from statistics import mean

from app.models.odds import OddsSnapshot


BOOKMAKER_WEIGHTS: dict[str, float] = {
    "pinnacle": 2.0,
    "bet365": 1.2,
    "bwin": 1.0,
    "williamhill": 1.0,
    "marathonbet": 1.0,
    "unibet": 0.9,
    "tipico": 0.9,
}
DEFAULT_BOOKMAKER_WEIGHT = 0.8


@dataclass
class FairProbs:
    p_home: float
    p_draw: float
    p_away: float
    n_books: int


def remove_overround(odds_home: float, odds_draw: float, odds_away: float) -> tuple[float, float, float]:
    """Convert decimal odds to probabilities and normalize away the bookmaker margin."""
    raw = (1.0 / odds_home, 1.0 / odds_draw, 1.0 / odds_away)
    s = sum(raw)
    return (raw[0] / s, raw[1] / s, raw[2] / s)


def aggregate(snapshots: list[OddsSnapshot]) -> FairProbs | None:
    if not snapshots:
        return None

    ph, pd, pa, weights = [], [], [], []
    for snap in snapshots:
        h, d, a = remove_overround(snap.odds_home, snap.odds_draw, snap.odds_away)
        w = BOOKMAKER_WEIGHTS.get(snap.bookmaker.lower(), DEFAULT_BOOKMAKER_WEIGHT)
        ph.append(h * w)
        pd.append(d * w)
        pa.append(a * w)
        weights.append(w)

    total = sum(weights)
    return FairProbs(
        p_home=sum(ph) / total,
        p_draw=sum(pd) / total,
        p_away=sum(pa) / total,
        n_books=len(snapshots),
    )
