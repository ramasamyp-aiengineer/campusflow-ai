import { useState } from "react";

import { Ring } from "@/components/Ring";
import { SAMPLE_JD, scoreColor } from "@/lib/format";
import type { GuardMeta, JDResponse } from "@/lib/types";

export function PlacementView({
  busy,
  onAnalyze,
  onOpenSprint,
}: {
  busy: boolean;
  onAnalyze: (job: string) => Promise<{ result: JDResponse; guard: GuardMeta } | null>;
  onOpenSprint: (id: number) => void;
}) {
  const [job, setJob] = useState(SAMPLE_JD);
  const [result, setResult] = useState<JDResponse | null>(null);

  return (
    <div className="grid h-full min-h-0 gap-4 overflow-auto px-5 py-5 lg:grid-cols-[1.1fr_0.9fr]">
      <section className="surface flex flex-col p-4">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Job description</p>
        <h1 className="mt-1 text-xl font-semibold">Placement copilot</h1>
        <p className="mb-3 mt-1 text-sm text-slate-500">Match the description against verified skills, then drop a 14-day prep sprint on the board.</p>
        <textarea className="field min-h-64 flex-1 text-sm leading-6" value={job} onChange={(event) => setJob(event.target.value)} />
        <div className="mt-3 flex gap-2">
          <button
            disabled={busy}
            onClick={async () => {
              const response = await onAnalyze(job);
              if (response) setResult(response.result);
            }}
            className="rounded-full bg-brand px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
          >
            Analyze and inject sprint
          </button>
          <button onClick={() => setJob(SAMPLE_JD)} className="rounded-full border border-line px-4 py-2 text-sm">
            Sample SDE-1 JD
          </button>
        </div>
      </section>
      <section className="surface p-4">
        {!result && <p className="text-sm text-slate-500">The match, the missing skills, and the prep tickets will land here.</p>}
        {result && (
          <div>
            <div className="flex items-center gap-4">
              <Ring value={result.match_percent} size={84} color={scoreColor(result.match_percent)} />
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">Employability match</p>
                <h2 className="text-lg font-semibold">{result.role_title}</h2>
                <p className="text-sm text-slate-600">{result.summary}</p>
              </div>
            </div>
            <div className="mt-4">
              <p className="text-xs font-semibold text-emerald-700">Already verified</p>
              <div className="mt-1 flex flex-wrap gap-1.5">
                {result.matched_skills.length === 0 && <span className="text-xs text-slate-400">None at the 70 bar</span>}
                {result.matched_skills.map((skill) => (
                  <span key={skill} className="rounded-full bg-emerald-50 px-2 py-1 text-xs text-emerald-700">
                    {skill}
                  </span>
                ))}
              </div>
            </div>
            <div className="mt-3">
              <p className="text-xs font-semibold text-rose-700">Missing from the graph</p>
              <div className="mt-1 flex flex-wrap gap-1.5">
                {result.missing_skills.map((skill) => (
                  <span key={skill} className="rounded-full bg-rose-50 px-2 py-1 text-xs text-rose-700">
                    {skill}
                  </span>
                ))}
              </div>
            </div>
            <button
              onClick={() => onOpenSprint(result.sprint.id)}
              className="mt-4 rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white"
            >
              Open {result.items.length} prep tickets
            </button>
          </div>
        )}
      </section>
    </div>
  );
}
