"""Manually-curated real WC 2026 results.

The martj42 results CSV (see app.data.apply_results) is the automatic source,
but it lags real kickoffs by up to a day or two — the fixture rows appear with
empty score columns until a maintainer fills them in. This module bridges that
gap: results entered here are applied to the seeded fixtures immediately, so the
site shows the real scoreline (and standings / Monte-Carlo honour it) the moment
a match finishes, without waiting for the upstream dataset.

Entries are keyed by team name **as stored in the DB** (see app.data.seed), with
the scoreline oriented home-vs-away as the match was actually played. Order in
the list does not matter; each team pair meets once in the group stage. Once the
CSV catches up with the same score it becomes a harmless no-op, so entries can be
left in place (or pruned) safely.

    (home_team, away_team, home_score, away_score)
"""

MANUAL_RESULTS: list[tuple[str, str, int, int]] = [
    # Matchday 1 — 11 Jun 2026 (Group A openers). CSV not yet updated upstream.
    ("Mexico", "South Africa", 2, 0),
    ("Korea Republic", "Czech Republic", 2, 1),
]
