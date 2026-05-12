"""FIFA member → confederation lookup.

Used by the historical ingestor to set Team.confederation and by elo.k_factor
to apply confederation-specific K-factor multipliers. Names use the canonical
DB form (e.g., "IR Iran", "Korea Republic", "Cabo Verde", "Türkiye").

Confederations:
  UEFA      — Europe
  CONMEBOL  — South America
  CONCACAF  — North & Central America + Caribbean
  CAF       — Africa
  AFC       — Asia + Australia
  OFC       — Oceania
"""

UEFA = {
    "Albania", "Andorra", "Armenia", "Austria", "Azerbaijan", "Belarus", "Belgium",
    "Bosnia and Herzegovina", "Bulgaria", "Croatia", "Cyprus", "Czech Republic",
    "Czechoslovakia", "Denmark", "England", "Estonia", "Faroe Islands", "Finland",
    "France", "Georgia", "Germany", "East Germany", "Gibraltar", "Greece", "Hungary",
    "Iceland", "Ireland", "Israel", "Italy", "Kazakhstan", "Kosovo", "Latvia",
    "Liechtenstein", "Lithuania", "Luxembourg", "Malta", "Moldova", "Monaco",
    "Montenegro", "Netherlands", "North Macedonia", "Northern Ireland", "Norway",
    "Poland", "Portugal", "Romania", "Russia", "San Marino", "Scotland", "Serbia",
    "Serbia and Montenegro", "Slovakia", "Slovenia", "Soviet Union", "Spain",
    "Sweden", "Switzerland", "Türkiye", "Ukraine", "Wales", "Yugoslavia",
}

CONMEBOL = {
    "Argentina", "Bolivia", "Brazil", "Chile", "Colombia", "Ecuador", "Paraguay",
    "Peru", "Uruguay", "Venezuela",
}

CONCACAF = {
    "Anguilla", "Antigua and Barbuda", "Aruba", "Bahamas", "Barbados", "Belize",
    "Bermuda", "Bonaire", "British Virgin Islands", "Canada", "Cayman Islands",
    "Costa Rica", "Cuba", "Curaçao", "Dominica", "Dominican Republic",
    "El Salvador", "French Guiana", "Grenada", "Guadeloupe", "Guatemala", "Guyana",
    "Haiti", "Honduras", "Jamaica", "Martinique", "Mexico", "Montserrat",
    "Nicaragua", "Panama", "Puerto Rico", "Saint Kitts and Nevis", "Saint Lucia",
    "Saint Martin", "Saint Vincent and the Grenadines", "Sint Maarten", "Suriname",
    "Trinidad and Tobago", "Turks and Caicos Islands", "United States",
    "US Virgin Islands",
}

CAF = {
    "Algeria", "Angola", "Benin", "Botswana", "Burkina Faso", "Burundi", "Cabo Verde",
    "Cameroon", "Central African Republic", "Chad", "Comoros", "Congo", "DR Congo",
    "Djibouti", "Egypt", "Equatorial Guinea", "Eritrea", "Eswatini", "Ethiopia",
    "Gabon", "Gambia", "Ghana", "Guinea", "Guinea-Bissau", "Ivory Coast", "Kenya",
    "Lesotho", "Liberia", "Libya", "Madagascar", "Malawi", "Mali", "Mauritania",
    "Mauritius", "Morocco", "Mozambique", "Namibia", "Niger", "Nigeria", "Rwanda",
    "Sao Tome and Principe", "Senegal", "Seychelles", "Sierra Leone", "Somalia",
    "South Africa", "South Sudan", "Sudan", "Tanzania", "Togo", "Tunisia", "Uganda",
    "Zambia", "Zanzibar", "Zimbabwe",
}

AFC = {
    "Afghanistan", "Australia", "Bahrain", "Bangladesh", "Bhutan", "Brunei",
    "Cambodia", "China PR", "China", "Chinese Taipei", "Guam", "Hong Kong", "India",
    "Indonesia", "Iraq", "IR Iran", "Japan", "Jordan", "Korea DPR", "Korea Republic",
    "Kuwait", "Kyrgyzstan", "Laos", "Lebanon", "Macau", "Malaysia", "Maldives",
    "Mongolia", "Myanmar", "Nepal", "Northern Mariana Islands", "Oman", "Pakistan",
    "Palestine", "Philippines", "Qatar", "Saudi Arabia", "Singapore", "Sri Lanka",
    "Syria", "Tajikistan", "Thailand", "Timor-Leste", "Turkmenistan",
    "United Arab Emirates", "Uzbekistan", "Vietnam", "Yemen",
}

OFC = {
    "American Samoa", "Cook Islands", "Fiji", "Kiribati", "New Caledonia",
    "New Zealand", "Niue", "Papua New Guinea", "Samoa", "Solomon Islands", "Tahiti",
    "Tonga", "Tuvalu", "Vanuatu",
}

_LOOKUP: dict[str, str] = {}
for confed, members in (
    ("UEFA", UEFA),
    ("CONMEBOL", CONMEBOL),
    ("CONCACAF", CONCACAF),
    ("CAF", CAF),
    ("AFC", AFC),
    ("OFC", OFC),
):
    for name in members:
        _LOOKUP[name] = confed


def confederation_of(team_name: str) -> str:
    """Return confederation code or 'UNKNOWN' if not classified."""
    return _LOOKUP.get(team_name, "UNKNOWN")


# K-factor multipliers — applied to qualifiers + friendlies, where confederation
# depth varies significantly. WC/Continental/Nations matches stay universal.
#
# Rationale: a team racking up wins against weak co-confederation members in a
# lopsided qualifier should not gain the same Elo as a team grinding through a
# competitive group. UEFA/CONMEBOL are the baseline (deep, competitive); AFC
# and CONCACAF have a wider spread; OFC is dominated by NZ.
CONFED_K_MULT: dict[str, float] = {
    "UEFA": 1.00,
    "CONMEBOL": 1.00,
    "CAF": 0.85,
    "CONCACAF": 0.80,
    "AFC": 0.75,
    "OFC": 0.55,
    "UNKNOWN": 0.85,
}
