// FIFA 3-letter code -> ISO 3166-1 alpha-2 mapping for the 48 WC 2026 teams.
// Used to render flag emojis. Codes that don't map (e.g. England / Wales /
// Northern Ireland which have no unicode flag) fall back to the FIFA code.
const FIFA_TO_ISO2: Record<string, string> = {
  // Hosts
  USA: "US", CAN: "CA", MEX: "MX",
  // CONMEBOL
  ARG: "AR", BRA: "BR", URU: "UY", COL: "CO", ECU: "EC", PAR: "PY",
  // UEFA
  ESP: "ES", FRA: "FR", ENG: "GB", POR: "PT", GER: "DE", NED: "NL",
  CRO: "HR", SUI: "CH", DEN: "DK", BEL: "BE", AUT: "AT", NOR: "NO",
  TUR: "TR", POL: "PL", SCO: "GB", ITA: "IT", CZE: "CZ", BIH: "BA",
  // CAF
  MAR: "MA", SEN: "SN", EGY: "EG", ALG: "DZ", TUN: "TN", NGA: "NG",
  CMR: "CM", CIV: "CI", GHA: "GH", RSA: "ZA", MLI: "ML", CPV: "CV",
  // AFC
  JPN: "JP", KOR: "KR", IRN: "IR", AUS: "AU", KSA: "SA", QAT: "QA",
  IRQ: "IQ", UZB: "UZ", JOR: "JO",
  // CONCACAF
  PAN: "PA", JAM: "JM", CRC: "CR", HON: "HN", HAI: "HT",
  // OFC
  NZL: "NZ",
};

const SPECIAL: Record<string, string> = {
  ENG: "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
  SCO: "🏴󠁧󠁢󠁳󠁣󠁴󠁿",
  WAL: "🏴󠁧󠁢󠁷󠁬󠁳󠁿",
};

export function flagEmoji(fifaCode: string): string {
  if (SPECIAL[fifaCode]) return SPECIAL[fifaCode];
  const iso = FIFA_TO_ISO2[fifaCode];
  if (!iso) return "";
  return iso
    .toUpperCase()
    .split("")
    .map((c) => String.fromCodePoint(0x1f1e6 - 65 + c.charCodeAt(0)))
    .join("");
}
