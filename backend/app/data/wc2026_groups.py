"""FIFA WM 2026 — Final Draw (Las Vegas, 2025-12-05).

48 Teams, 12 Gruppen (A–L). Top 2 + 8 beste Gruppendritte -> Round of 32.

Initial-Elo-Werte sind grobe Schaetzungen auf Basis World-Football-Elo-Niveau
Mitte 2026. Sie dienen als Startpunkt: sobald `app/data/historical_ingestor.py`
laeuft, werden die Werte chronologisch aus echten Resultaten neu berechnet.

Team-Namen folgen der FIFA-Schreibweise (Korea Republic, Türkiye, Cabo Verde).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SeededTeam:
    name: str
    fifa_code: str
    confederation: str
    initial_elo: float
    is_host: bool = False


HOSTS_2026 = {"USA", "CAN", "MEX"}


# Actual WC 2026 Final Draw (groups A..L). Order within each group is irrelevant.
TEAMS_BY_GROUP: dict[str, list[SeededTeam]] = {
    "A": [
        SeededTeam("Mexico", "MEX", "CONCACAF", 1830, is_host=True),
        SeededTeam("South Africa", "RSA", "CAF", 1700),
        SeededTeam("Korea Republic", "KOR", "AFC", 1800),
        SeededTeam("Czech Republic", "CZE", "UEFA", 1750),
    ],
    "B": [
        SeededTeam("Canada", "CAN", "CONCACAF", 1780, is_host=True),
        SeededTeam("Bosnia and Herzegovina", "BIH", "UEFA", 1730),
        SeededTeam("Qatar", "QAT", "AFC", 1680),
        SeededTeam("Switzerland", "SUI", "UEFA", 1870),
    ],
    "C": [
        SeededTeam("Brazil", "BRA", "CONMEBOL", 2080),
        SeededTeam("Morocco", "MAR", "CAF", 1850),
        SeededTeam("Haiti", "HAI", "CONCACAF", 1500),
        SeededTeam("Scotland", "SCO", "UEFA", 1770),
    ],
    "D": [
        SeededTeam("United States", "USA", "CONCACAF", 1850, is_host=True),
        SeededTeam("Paraguay", "PAR", "CONMEBOL", 1750),
        SeededTeam("Australia", "AUS", "AFC", 1780),
        SeededTeam("Türkiye", "TUR", "UEFA", 1820),
    ],
    "E": [
        SeededTeam("Germany", "GER", "UEFA", 1980),
        SeededTeam("Curaçao", "CUW", "CONCACAF", 1550),
        SeededTeam("Ivory Coast", "CIV", "CAF", 1780),
        SeededTeam("Ecuador", "ECU", "CONMEBOL", 1810),
    ],
    "F": [
        SeededTeam("Netherlands", "NED", "UEFA", 1970),
        SeededTeam("Japan", "JPN", "AFC", 1830),
        SeededTeam("Sweden", "SWE", "UEFA", 1820),
        SeededTeam("Tunisia", "TUN", "CAF", 1730),
    ],
    "G": [
        SeededTeam("Belgium", "BEL", "UEFA", 1940),
        SeededTeam("Egypt", "EGY", "CAF", 1780),
        SeededTeam("IR Iran", "IRN", "AFC", 1790),
        SeededTeam("New Zealand", "NZL", "OFC", 1620),
    ],
    "H": [
        SeededTeam("Spain", "ESP", "UEFA", 2050),
        SeededTeam("Cabo Verde", "CPV", "CAF", 1640),
        SeededTeam("Saudi Arabia", "KSA", "AFC", 1700),
        SeededTeam("Uruguay", "URU", "CONMEBOL", 1900),
    ],
    "I": [
        SeededTeam("France", "FRA", "UEFA", 2070),
        SeededTeam("Senegal", "SEN", "CAF", 1820),
        SeededTeam("Iraq", "IRQ", "AFC", 1650),
        SeededTeam("Norway", "NOR", "UEFA", 1830),
    ],
    "J": [
        SeededTeam("Argentina", "ARG", "CONMEBOL", 2150),
        SeededTeam("Algeria", "ALG", "CAF", 1770),
        SeededTeam("Austria", "AUT", "UEFA", 1830),
        SeededTeam("Jordan", "JOR", "AFC", 1610),
    ],
    "K": [
        SeededTeam("Portugal", "POR", "UEFA", 2010),
        SeededTeam("DR Congo", "COD", "CAF", 1700),
        SeededTeam("Uzbekistan", "UZB", "AFC", 1660),
        SeededTeam("Colombia", "COL", "CONMEBOL", 1890),
    ],
    "L": [
        SeededTeam("England", "ENG", "UEFA", 2030),
        SeededTeam("Croatia", "CRO", "UEFA", 1920),
        SeededTeam("Ghana", "GHA", "CAF", 1720),
        SeededTeam("Panama", "PAN", "CONCACAF", 1670),
    ],
}


def all_teams() -> list[SeededTeam]:
    return [t for teams in TEAMS_BY_GROUP.values() for t in teams]
