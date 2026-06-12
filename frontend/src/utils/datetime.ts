// Kickoffs come from the API as naive UTC (e.g. "2026-06-11T19:00:00", no zone).
// Append "Z" when no zone is present so the string parses as UTC, then render in
// Vienna time regardless of the viewer's own timezone.
const VIENNA_TZ = "Europe/Vienna";

export function formatKickoff(kickoff: string): string {
  const hasZone = /[zZ]|[+-]\d{2}:?\d{2}$/.test(kickoff);
  const iso = hasZone ? kickoff : `${kickoff}Z`;
  return new Date(iso).toLocaleString("en-US", {
    timeZone: VIENNA_TZ,
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}
