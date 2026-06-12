"""Emergency hand-entered WC 2026 results.

apply_results() has two automatic sources that need no maintenance:
  1. The Odds API /scores endpoint — completed games appear minutes after full
     time (the timely source).
  2. The martj42 results CSV — authoritative, but lags kickoff by a day or more.

This list is the manual fallback for the rare case both miss a result (e.g. the
Odds API is out of quota and the CSV hasn't published yet). It is applied last,
so an entry here wins on conflict. Normally it stays empty.

Entries are keyed by team name **as stored in the DB** (see app.data.seed), the
scoreline oriented home-vs-away as actually played. Order does not matter; each
pair meets once in the group stage. Once an automatic source carries the same
score the entry becomes a harmless no-op.

    (home_team, away_team, home_score, away_score)
"""

MANUAL_RESULTS: list[tuple[str, str, int, int]] = []
