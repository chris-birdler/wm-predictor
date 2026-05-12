"""Load historical international match results.

Source: github.com/martj42/international_results — CSV with all international
matches since 1872, updated daily. Columns:
date, home_team, away_team, home_score, away_score, tournament, city, country, neutral.
"""

from datetime import date, datetime

import httpx
import pandas as pd
from sqlalchemy.orm import Session

from app.data.confederations import confederation_of
from app.models.match import Match, MatchStage, MatchType
from app.models.team import Team
from app.prediction.elo import update_ratings

RESULTS_URL = (
    "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"
)

# Map CSV team names to canonical names already present in the seeded DB.
# Without this, "Turkey" would create a new Team row and collide on the
# fifa_code 'TUR' (already taken by the seeded "Türkiye").
NAME_ALIASES: dict[str, str] = {
    "Turkey": "Türkiye",
    "Cape Verde": "Cabo Verde",
    "Cape Verde Islands": "Cabo Verde",
    "South Korea": "Korea Republic",
    "Iran": "IR Iran",
    "Republic of Ireland": "Ireland",
    "United States Virgin Islands": "US Virgin Islands",
    "Czechia": "Czech Republic",
    "Curacao": "Curaçao",
    "DR Congo": "DR Congo",
}


# UEFA Nations League finals tournament windows (4-team mini-tournament).
# eloratings.net applies K=50 to these matches vs K=40 for group stage.
# Source data doesn't tag these separately, so detect by date window.
_NATIONS_FINALS_WINDOWS: tuple[tuple[date, date], ...] = (
    (date(2019, 6, 5), date(2019, 6, 9)),     # Portugal
    (date(2021, 10, 6), date(2021, 10, 10)),  # Italy
    (date(2023, 6, 14), date(2023, 6, 18)),   # Netherlands
    (date(2025, 6, 4), date(2025, 6, 8)),     # Germany
)


def _is_nations_finals(match_date: date) -> bool:
    return any(start <= match_date <= end for start, end in _NATIONS_FINALS_WINDOWS)


def _classify_tournament(name: str, match_date: date) -> MatchType:
    lower = name.lower()
    # Qualifiers first — otherwise "FIFA World Cup qualification" hits the WC
    # branch and gets K=60 instead of K=40.
    if "qualification" in lower or "qualifier" in lower:
        return MatchType.QUALIFIER
    # Nations League before continental keywords — otherwise "CONCACAF Nations
    # League" matches the CONCACAF continental keyword.
    if "nations league" in lower:
        return MatchType.NATIONS_FINALS if _is_nations_finals(match_date) else MatchType.NATIONS
    if "world cup" in lower:
        # Non-FIFA imitations (Viva World Cup, CONIFA) — treat as friendly-grade.
        return MatchType.WORLDCUP if "fifa" in lower else MatchType.FRIENDLY
    # Specific continental finals tournaments. "copa" covers Copa América
    # (accent-safe); "african cup" matches "African Cup of Nations".
    if any(k in lower for k in (
        "euro",
        "copa",
        "african cup",
        "asian cup",
        "gold cup",
        "concacaf championship",
        "oceania nations cup",
        "confederations cup",
    )):
        return MatchType.CONTINENTAL
    return MatchType.FRIENDLY


def fetch_results_csv() -> pd.DataFrame:
    resp = httpx.get(RESULTS_URL, timeout=60)
    resp.raise_for_status()
    from io import StringIO
    return pd.read_csv(StringIO(resp.text))


def ingest_historical(db: Session, since_year: int = 1990) -> tuple[int, int]:
    """Load matches and update Elo ratings chronologically.

    Returns (matches_loaded, teams_touched).
    """
    df = fetch_results_csv()
    df["date"] = pd.to_datetime(df["date"])
    df = df[df["date"].dt.year >= since_year].copy()
    df = df.dropna(subset=["home_score", "away_score"])
    df = df.sort_values("date")

    team_cache: dict[str, Team] = {}
    used_codes: set[str] = {t.fifa_code for t in db.query(Team).all()}
    existing_keys: set[tuple[int, int, str]] = {
        (m.home_team_id, m.away_team_id, m.kickoff.date().isoformat())
        for m in db.query(Match).filter(Match.is_finished.is_(True)).all()
    }
    matches_added = 0

    def _unique_code(base: str) -> str:
        candidate = base[:3].upper()
        if candidate not in used_codes:
            used_codes.add(candidate)
            return candidate
        for i in range(2, 10):
            alt = f"{base[:2].upper()}{i}"
            if alt not in used_codes:
                used_codes.add(alt)
                return alt
        # Fallback: deterministic hash-derived 3-char code
        import hashlib
        h = hashlib.md5(base.encode()).hexdigest()[:3].upper()
        used_codes.add(h)
        return h

    def _get_team(name: str) -> Team:
        canonical = NAME_ALIASES.get(name, name)
        if canonical in team_cache:
            return team_cache[canonical]
        team = db.query(Team).filter(Team.name == canonical).first()
        if not team:
            team = Team(
                name=canonical,
                fifa_code=_unique_code(canonical),
                confederation=confederation_of(canonical),
                elo=1500.0,
            )
            db.add(team)
            db.flush()
        elif team.confederation in ("UNKNOWN", None, ""):
            team.confederation = confederation_of(canonical)
        team_cache[canonical] = team
        return team

    for _, row in df.iterrows():
        home = _get_team(row["home_team"])
        away = _get_team(row["away_team"])
        kickoff = row["date"].to_pydatetime()
        mt = _classify_tournament(row["tournament"], kickoff.date())
        neutral = bool(row.get("neutral", False))

        key = (home.id, away.id, kickoff.date().isoformat())
        if key in existing_keys:
            continue
        existing_keys.add(key)

        m = Match(
            home_team_id=home.id,
            away_team_id=away.id,
            kickoff=kickoff,
            match_type=mt,
            stage=MatchStage.OTHER,
            home_score=int(row["home_score"]),
            away_score=int(row["away_score"]),
            is_finished=True,
            venue=row.get("city"),
        )
        db.add(m)

        new_h, new_a = update_ratings(
            home.elo, away.elo,
            int(row["home_score"]), int(row["away_score"]),
            mt, neutral=neutral,
            home_confed=home.confederation,
            away_confed=away.confederation,
        )
        home.elo = new_h
        away.elo = new_a
        matches_added += 1

        if matches_added % 500 == 0:
            db.commit()

    db.commit()
    return matches_added, len(team_cache)
