import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../api/client";
import { GroupCard } from "../components/GroupCard";

export default function Groups() {
  const teamsQ = useQuery({ queryKey: ["teams-by-group"], queryFn: api.teamsByGroup });
  const matchesQ = useQuery({
    queryKey: ["matches", "group"],
    queryFn: () => api.matches({ stage: "group" }),
  });
  const [busy, setBusy] = useState(false);

  const handleAll = async () => {
    setBusy(true);
    try {
      await api.predictAllGroups();
    } finally {
      setBusy(false);
    }
  };

  if (teamsQ.isLoading || matchesQ.isLoading) return <p>Lade...</p>;
  if (teamsQ.error || matchesQ.error) return <p>Fehler beim Laden.</p>;

  const teams = teamsQ.data!;
  const matchesByGroup: Record<string, typeof matchesQ.data> = {};
  for (const m of matchesQ.data ?? []) {
    if (!m.group) continue;
    (matchesByGroup[m.group] ??= []).push(m);
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Gruppenphase</h1>
        <button
          onClick={handleAll}
          disabled={busy}
          className="rounded bg-accent px-4 py-2 font-semibold text-slate-900 hover:bg-cyan-300 disabled:opacity-50"
        >
          Alle Gruppen vorhersagen
        </button>
      </div>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {Object.entries(teams).map(([letter, ts]) => (
          <GroupCard
            key={letter}
            group={letter}
            teams={ts}
            matches={matchesByGroup[letter] ?? []}
          />
        ))}
      </div>
    </div>
  );
}
