import { AlertTriangle, CheckCircle2, Radar, TrendingUp } from "lucide-react";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import type { DriftRadar as DriftData, Persona } from "@/lib/types";

export function DriftRadar({ persona }: { persona: Persona }) {
  const [radar, setRadar] = useState<DriftData | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let ignore = false;
    api<DriftData>("/api/v1/signals/drift", persona)
      .then((data) => {
        if (!ignore) setRadar(data);
      })
      .catch((reason: Error) => {
        if (!ignore) setError(reason.message);
      });
    return () => {
      ignore = true;
    };
  }, [persona]);

  if (error) return <p className="surface mb-4 px-4 py-3 text-sm text-slate-500">Curriculum drift radar is unavailable: {error}</p>;
  if (!radar) return <p className="surface mb-4 px-4 py-3 text-sm text-slate-500">Comparing industry news with the syllabus…</p>;
  if (radar.total_stories === 0) {
    return <p className="surface mb-4 px-4 py-3 text-sm text-slate-500">No student interest stories yet, so there is nothing to compare with the syllabus.</p>;
  }
  const widest = Math.max(1, ...radar.trends.map((trend) => trend.share));

  return (
    <section className="surface mb-4 p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="flex items-center gap-2 text-sm font-semibold">
          <Radar size={16} className="text-copper" /> Curriculum drift radar
        </h2>
        <p className="text-xs text-slate-500">
          {radar.total_stories} stories from {radar.students} {radar.students === 1 ? "student" : "students"}, names withheld
        </p>
      </div>

      {radar.alerts.length > 0 && (
        <ul className="mt-3 space-y-2">
          {radar.alerts.map((alert) => (
            <li
              key={alert.title}
              className={`flex gap-2 rounded-xl border px-3 py-2 text-sm ${
                alert.level === "critical" ? "border-rose-200 bg-rose-50 text-rose-900" : "border-amber-200 bg-amber-50 text-amber-900"
              }`}
            >
              {alert.level === "critical" ? <AlertTriangle size={16} className="mt-0.5 shrink-0" /> : <TrendingUp size={16} className="mt-0.5 shrink-0" />}
              <span>
                <span className="font-semibold">{alert.title}.</span> {alert.detail}
              </span>
            </li>
          ))}
        </ul>
      )}

      <div className="mt-4 grid gap-4 lg:grid-cols-[1fr_260px]">
        <div>
          <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-slate-500">Trending industry skills vs current syllabus</p>
          <div className="space-y-2.5">
            {radar.trends.map((trend) => (
              <div key={trend.term}>
                <div className="mb-1 flex items-center justify-between gap-2 text-sm">
                  <span className="font-medium text-ink">{trend.term}</span>
                  <span className={`inline-flex items-center gap-1 text-[11px] font-semibold ${trend.in_syllabus ? "text-emerald-700" : "text-rose-700"}`}>
                    {trend.in_syllabus ? <CheckCircle2 size={12} /> : <AlertTriangle size={12} />}
                    {trend.in_syllabus ? "In syllabus" : "Not in syllabus"}
                  </span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-[#F3EEE6]">
                  <div
                    className="h-full rounded-full"
                    style={{ width: `${Math.max(6, (trend.share / widest) * 100)}%`, background: trend.in_syllabus ? "#0E7C66" : "#C46B2C" }}
                  />
                </div>
                <p className="mt-0.5 text-[11px] text-slate-500">
                  {trend.stories} {trend.stories === 1 ? "story" : "stories"} · {trend.share}% · {trend.suggestion}
                </p>
              </div>
            ))}
          </div>
        </div>
        <div>
          <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-slate-500">Where the news is</p>
          <ul className="divide-y divide-line text-sm">
            {radar.subtopics.map((topic) => (
              <li key={topic.label} className="flex items-center justify-between gap-2 py-1.5">
                <span className="truncate text-slate-700">{topic.label}</span>
                <span className="mono shrink-0 text-[11px] text-slate-500">
                  {topic.count}
                  {topic.critical > 0 && <span className="ml-1.5 text-rose-700">{topic.critical} critical</span>}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
