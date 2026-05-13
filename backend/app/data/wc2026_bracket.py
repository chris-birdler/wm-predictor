"""FIFA 2026 R32 → Final bracket structure.

Source: en.wikipedia.org/wiki/2026_FIFA_World_Cup_knockout_stage
       (Annex C of FIFA tournament regulations)

R32 has 16 fixtures numbered 73-88. Eight are fixed (winner-vs-runner-up or
runner-up-vs-runner-up across groups), the other eight pit a group winner
against a third-placed team. WHICH third goes to which slot depends on
which 8 of the 12 third-placed teams qualify — a 495-row cascade table
in `wc2026_r32_cascade.json`.

Subsequent KO rounds (R16 = 89-96, QF = 97-100, SF = 101-102, Final = 104)
follow a fixed bracket; each match maps to the two prior matches whose
winners feed into it via KO_PROGRESSION.
"""

import json
from pathlib import Path

# (slot_a, slot_b, fifa_match_no) — slot is e.g. "1A" (winner of A) or "2C" (runner-up of C).
R32_FIXED: list[tuple[str, str, int]] = [
    ("2A", "2B", 73),
    ("1F", "2C", 75),
    ("1C", "2F", 76),
    ("2E", "2I", 78),
    ("2K", "2L", 83),
    ("1H", "2J", 84),
    ("1J", "2H", 86),
    ("2D", "2G", 88),
]

# Group winners that face a third-placed team (fixa_match_no -> winner_slot).
R32_THIRDS: dict[int, str] = {
    74: "1E", 77: "1I", 79: "1A", 80: "1L",
    81: "1D", 82: "1G", 85: "1B", 87: "1K",
}

_CASCADE_PATH = Path(__file__).parent / "wc2026_r32_cascade.json"
THIRDS_CASCADE: dict[str, dict[str, str]] = json.loads(_CASCADE_PATH.read_text())
# {qualifying_groups_sorted: {winner_slot: third_group_letter}}
# e.g. THIRDS_CASCADE["EFGHIJKL"]["1A"] == "E" → 1A plays 3E

# Each KO match (R16+) takes the winners of two prior matches.
KO_PROGRESSION: dict[int, tuple[int, int]] = {
    89: (74, 77), 90: (73, 75), 91: (76, 78), 92: (79, 80),
    93: (83, 84), 94: (81, 82), 95: (86, 88), 96: (85, 87),
    97: (89, 90), 98: (93, 94), 99: (91, 92), 100: (95, 96),
    101: (97, 98), 102: (99, 100),
    104: (101, 102),
}

R32_MATCHES = list(range(73, 89))                # 73..88
R16_MATCHES = list(range(89, 97))                # 89..96
QF_MATCHES  = list(range(97, 101))               # 97..100
SF_MATCHES  = [101, 102]
THIRD_MATCH = 103                                # 3rd-place playoff (SF losers)
FINAL_MATCH = 104

# Source matches for the 3rd-place playoff (semifinal losers).
THIRD_FROM_LOSERS: tuple[int, int] = (101, 102)

KO_STAGE_MATCHES: dict[str, list[int]] = {
    "r32":   R32_MATCHES,
    "r16":   R16_MATCHES,
    "qf":    QF_MATCHES,
    "sf":    SF_MATCHES,
    "third": [THIRD_MATCH],
    "final": [FINAL_MATCH],
}

# When a team WINS a match in this list, what stage do we label them as having reached?
# r32 winners reach r16, r16 winners reach qf, etc.
WINNER_STAGE: dict[int, str] = {}
for m in R32_MATCHES: WINNER_STAGE[m] = "r16"
for m in R16_MATCHES: WINNER_STAGE[m] = "qf"
for m in QF_MATCHES:  WINNER_STAGE[m] = "sf"
for m in SF_MATCHES:  WINNER_STAGE[m] = "final"
WINNER_STAGE[FINAL_MATCH] = "winner"


def _resolve_slot(slot: str, top1: dict[str, int], top2: dict[str, int]) -> int:
    rank, group = slot[0], slot[1]
    if rank == "1":
        return top1[group]
    if rank == "2":
        return top2[group]
    raise ValueError(f"bad slot: {slot}")


def assemble_r32(
    top1: dict[str, int],
    top2: dict[str, int],
    thirds: dict[str, int],
) -> list[tuple[int, int, int]]:
    """Build all 16 R32 fixtures from group standings.

    top1/top2: {group_letter: team_id} (12 entries each)
    thirds:    {group_letter: team_id} of the 8 best third-placed teams
    Returns:   [(fifa_match_no, home_team_id, away_team_id), ...] sorted by match_no.
    """
    if len(thirds) != 8:
        raise ValueError(f"need exactly 8 best thirds, got {len(thirds)}")
    third_key = "".join(sorted(thirds.keys()))
    cascade_row = THIRDS_CASCADE.get(third_key)
    if cascade_row is None:
        raise ValueError(f"third combination {third_key} not in cascade table")

    fixtures: list[tuple[int, int, int]] = []
    for slot_a, slot_b, match_no in R32_FIXED:
        a = _resolve_slot(slot_a, top1, top2)
        b = _resolve_slot(slot_b, top1, top2)
        fixtures.append((match_no, a, b))
    for match_no, winner_slot in R32_THIRDS.items():
        a = _resolve_slot(winner_slot, top1, top2)
        third_group = cascade_row[winner_slot]
        b = thirds[third_group]
        fixtures.append((match_no, a, b))
    fixtures.sort(key=lambda t: t[0])
    return fixtures
