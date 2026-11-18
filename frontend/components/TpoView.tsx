import { useMemo, useState } from "react";

import { DriftRadar } from "@/components/DriftRadar";
import type { Persona, ReadinessMatrix } from "@/lib/types";

export function TpoView({ matrix, persona }: { matrix: ReadinessMatrix | null; persona: Persona }) {
  const [minimum, setMinimum] = useState(70);
  const [onlyShortlist, setOnlyShortlist] = useState(false);
  const rows = useMemo(() => {
    if (!matrix) return [];
    return matrix.rows.filter((row) => row.verified_skill_score >= minimum && (!onlyShortlist || row.shortlist));
  }, [matrix, minimum, onlyShortlist]);

  if (!matrix) return <div className="grid h-full place-items-center text-sm text-slate-500">Loading readiness…</div>;
  const mismatch = matrix.rows.filter((row) => row.cgpa >= 9 && row.verified_skill_score < 55);

  return (
    <div className="h-full overflow-auto px-5 py-5">
      <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Training and placement</p>
      <h1 className="text-xl font-semibold">Recruiter readiness</h1>
      <p className="mb-4 text-sm text-slate-500">Shortlist from verified skill evidence. CGPA stays visible so a high grade without proof is obvious.</p>
      {mismatch.length > 0 && (
        <div className="mb-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          {mismatch.map((row) => row.name).join(", ")} would clear a CGPA screen and miss a verified-skill screen.
        </div>
      )}
      <DriftRadar persona={persona} />
      <div className="mb-4 flex flex-wrap items-center gap-4">
        <label className="text-sm text-slate-600">
          Minimum verified score
          <input
            type="range"
            min={0}
            max={100}
            value={minimum}
            onChange={(event) => setMinimum(Number(event.target.value))}
            className="ml-3 align-middle"
          />
          <span className="mono ml-2">{minimum}</span>
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={onlyShortlist} onChange={(event) => setOnlyShortlist(event.target.checked)} />
          Shortlist bar (70+)
        </label>
        <span className="text-xs text-slate-500">{rows.length} students visible</span>
      </div>
      <div className="surface overflow-auto">
        <table className="w-full min-w-[820px] text-left text-sm">
          <thead className="border-b border-line text-[11px] uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3 font-medium">Student</th>
              <th className="px-4 py-3 font-medium">CGPA</th>
              <th className="px-4 py-3 font-medium">Verified skill</th>
              <th className="px-4 py-3 font-medium">Evidence</th>
              <th className="px-4 py-3 font-medium">Top skills</th>
              <th className="px-4 py-3 font-medium">Drive</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id} className="border-t border-line">
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <span className="grid h-8 w-8 place-items-center rounded-full bg-slate-100 text-[11px] font-semibold">{row.avatar_initials}</span>
                    <div>
                      <p className="font-medium">{row.name}</p>
                      <p className="text-[11px] text-slate-400">{row.program}</p>
                    </div>
                  </div>
                </td>
                <td className="mono px-4 py-3">{row.cgpa.toFixed(1)}</td>
                <td className="px-4 py-3">
                  <span className="mono font-semibold" style={{ color: row.verified_skill_score >= 70 ? "#059669" : "#E11D48" }}>
                    {row.verified_skill_score}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <p className="mono text-[11px] text-slate-500">{row.verified_lwi_count} links</p>
                  <p className="mono text-[11px] text-slate-400">{row.evidence_hashes[0] ?? "—"}</p>
                </td>
                <td className="px-4 py-3 text-xs text-slate-600">{row.top_skills.join(" · ")}</td>
                <td className="px-4 py-3">
                  <span className={`rounded-full px-2 py-1 text-[11px] font-semibold ${row.shortlist ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-500"}`}>
                    {row.shortlist ? "Shortlist" : "Hold"}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
