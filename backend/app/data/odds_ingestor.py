"""Pull 1X2 odds for upcoming WM matches.

Primary source: The Odds API (https://the-odds-api.com/) — free tier 500
requests/month. Sport key 'soccer_fifa_world_cup'.

Fallback: stub for oddsportal.com scraping (must be implemented carefully
to respect their TOS / rate limits).
"""

from datetime import datetime

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.models.match import Match
from app.models.odds import OddsSnapshot
from app.models.team import Team

ODDS_API_SPORT = "soccer_fifa_world_cup"

# Map The Odds API team names to the canonical DB names.
ODDS_NAME_ALIASES: dict[str, str] = {
    "USA": "United States",
    "South Korea": "Korea Republic",
    "Iran": "IR Iran",
    "Cape Verde": "Cabo Verde",
    "Turkey": "Türkiye",
    "Curacao": "Curaçao",
    "Bosnia & Herzegovina": "Bosnia and Herzegovina",
    "Bosnia and Herzegovina": "Bosnia and Herzegovina",
    "Czechia": "Czech Republic",
}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def _fetch_odds_api() -> list[dict]:
    if not settings.ODDS_API_KEY:
        return []
    url = f"{settings.ODDS_API_BASE}/sports/{ODDS_API_SPORT}/odds"
    params = {
        "apiKey": settings.ODDS_API_KEY,
        "regions": "eu,uk",
        "markets": "h2h",
        "oddsFormat": "decimal",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()


def _find_match(
    db: Session,
    home_name: str,
    away_name: str,
    kickoff: datetime,
) -> tuple[Match | None, bool]:
    """Lookup match by team pair. Returns (match, swapped).

    The Odds API home/away order may differ from our seeded order; we try both.
    `swapped` is True iff the DB stores the teams in the reverse order — the
    caller can then map odds accordingly.
    """
    home_canonical = ODDS_NAME_ALIASES.get(home_name, home_name)
    away_canonical = ODDS_NAME_ALIASES.get(away_name, away_name)

    home = db.execute(
        select(Team).where(Team.name == home_canonical)
    ).scalar_one_or_none()
    away = db.execute(
        select(Team).where(Team.name == away_canonical)
    ).scalar_one_or_none()
    if not home or not away:
        return None, False

    # Restrict to WM-2026 matches (group or KO), otherwise we'd hit historical
    # encounters between the same teams.
    match = db.execute(
        select(Match).where(
            Match.home_team_id == home.id,
            Match.away_team_id == away.id,
            Match.is_finished.is_(False),
        )
    ).scalar_one_or_none()
    if match is not None:
        return match, False

    match = db.execute(
        select(Match).where(
            Match.home_team_id == away.id,
            Match.away_team_id == home.id,
            Match.is_finished.is_(False),
        )
    ).scalar_one_or_none()
    return match, match is not None


async def ingest_odds(db: Session) -> tuple[int, int, list[str]]:
    """Pull odds and persist snapshots.

    Returns (snapshots_inserted, matches_matched, unmatched_event_descriptions).
    """
    events = await _fetch_odds_api()
    now = datetime.utcnow()
    inserted = 0
    matched_ids: set[int] = set()
    unmatched: list[str] = []
    for ev in events:
        kickoff = datetime.fromisoformat(ev["commence_time"].replace("Z", "+00:00"))
        home_name = ev.get("home_team")
        away_name = ev.get("away_team")
        match, swapped = _find_match(db, home_name, away_name, kickoff)
        if not match:
            unmatched.append(f"{home_name} vs {away_name}")
            continue
        matched_ids.add(match.id)
        for bm in ev.get("bookmakers", []):
            book = bm.get("key")
            for market in bm.get("markets", []):
                if market.get("key") != "h2h":
                    continue
                outcomes = {o["name"]: o["price"] for o in market.get("outcomes", [])}
                if not (home_name in outcomes and away_name in outcomes and "Draw" in outcomes):
                    continue
                odds_home_api = outcomes[home_name]
                odds_away_api = outcomes[away_name]
                # If DB stores the pair reversed, swap home/away odds to match DB orientation.
                if swapped:
                    odds_home_api, odds_away_api = odds_away_api, odds_home_api
                db.add(
                    OddsSnapshot(
                        match_id=match.id,
                        bookmaker=book,
                        fetched_at=now,
                        odds_home=odds_home_api,
                        odds_draw=outcomes["Draw"],
                        odds_away=odds_away_api,
                    )
                )
                inserted += 1
    db.commit()
    return inserted, len(matched_ids), unmatched


def ingest_oddsportal_stub(*_args, **_kwargs) -> int:
    """Placeholder for an oddsportal.com scraper.

    Implementation note: parse the JSON encoded in the page's <script> tags
    (oddsportal exposes a base64+xor encoded payload per market). Respect
    rate limits; cache aggressively.
    """
    raise NotImplementedError("oddsportal scraper not implemented")
