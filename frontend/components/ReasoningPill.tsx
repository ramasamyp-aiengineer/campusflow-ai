import { Check } from "lucide-react";

import type { AIJob } from "@/lib/types";

export function ReasoningPill({ job }: { job: AIJob }) {
  return (
    <div className="pointer-events-none fixed bottom-5 left-1/2 z-50 w-[min(560px,calc(100%-2rem))] -translate-x-1/2">
      <div className="rounded-2xl border border-line bg-white px-4 py-3 shadow-lift">
        <div className="mb-2 flex items-center justify-between gap-3">
          <p className="text-sm font-semibold text-ink">{job.title}</p>
          <span className="mono text-[11px] text-slate-500">{job.done ? "Done" : "Live"}</span>
        </div>
        <ol className="grid gap-2 sm:grid-cols-3">
          {job.steps.map((step, index) => {
            const complete = job.done || index < job.active;
            const current = !job.done && index === job.active;
            return (
              <li key={step} className="flex items-center gap-2 text-xs text-slate-600">
                <span
                  className={`grid h-5 w-5 shrink-0 place-items-center rounded-full border ${
                    complete
                      ? "border-emerald-600 bg-emerald-600 text-white"
                      : current
                        ? "border-brand text-brand"
                        : "border-slate-200 text-slate-400"
                  }`}
                >
                  {complete ? <Check size={12} /> : <span className="mono text-[10px]">{index + 1}</span>}
                </span>
                <span className={current ? "font-semibold text-ink" : ""}>{step}</span>
              </li>
            );
          })}
        </ol>
        {job.foot && <p className="mt-2 text-[11px] text-slate-500">{job.foot}</p>}
      </div>
    </div>
  );
}
