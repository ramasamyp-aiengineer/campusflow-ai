import { useCallback, useEffect, useState } from "react";

import { DriftRadar } from "@/components/DriftRadar";
import { ClusterBars, SentimentDonut, sentimentCounts } from "@/components/SentimentCharts";
import { api } from "@/lib/api";
import type { CohortHealth, Persona, ReviewTicket, SignalPulse } from "@/lib/types";

export function FacultyView({ cohort, persona }: { cohort: CohortHealth | null; persona: Persona }) {
  const [pulse, setPulse] = useState<SignalPulse | null>(null);
  const [queue, setQueue] = useState<ReviewTicket[]>([]);
  const [queueError, setQueueError] = useState("");

  const loadQueue = useCallback(() => {
    api<ReviewTicket[]>("/api/v1/faculty/review-queue", persona)
      .then(setQueue)
      .catch((reason: Error) => setQueueError(reason.message));
  }, [persona]);

  useEffect(() => {
    let ignore = false;
    api<SignalPulse>("/api/v1/signals/pulse", persona)
      .then((data) => {
        if (!ignore) setPulse(data);
      })
      .catch(() => undefined);
    loadQueue();
    return () => {
      ignore = true;
    };
  }, [persona, loadQueue]);

  async function cosign(ticketId: number) {
    setQueueError("");
    try {
      await api(`/api/v1/lwi/${ticketId}/cosign`, persona, { method: "PATCH" });
      setQueue((rows) => rows.filter((row) => row.id !== ticketId));
    } catch (reason) {
      setQueueError(reason instanceof Error ? reason.message : "Could not co-sign that ticket");
    }
  }
  if (!cohort)
    return <div className="grid h-full place-items-center text-sm text-slate-500">Loading cohort health…</div>;
  return (
    <div className="h-full overflow-auto px-5 py-5">
      <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">Faculty command</p>
      <h1 className="text-xl font-semibold tracking-tight">Early-warning radar</h1>
      <p className="mb-4 text-sm text-slate-500">
        A student is at risk when sprint velocity drops more than 35% or more than two core tickets are blocked. Mastery
        is recorded when you co-sign an AI-reviewed ticket.
      </p>
      <section className="surface mb-4 p-4">
        <h2 className="text-sm font-semibold">Awaiting co-sign</h2>
        <p className="mt-1 text-xs text-slate-500">
          These drafts cleared the AI review bar of 75. Co-sign writes the skill graph.
        </p>
        {queueError && <p className="mt-2 text-sm text-rose-700">{queueError}</p>}
        {queue.length === 0 ? (
          <p className="mt-3 text-sm text-slate-500">Nothing is waiting.</p>
        ) : (
          <ul className="mt-3 divide-y divide-line">
            {queue.map((ticket) => (
              <li key={ticket.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                <div>
                  <p className="text-sm font-medium text-ink">
                    {ticket.student_name} · <span className="mono text-xs">{ticket.ticket_code}</span>
                  </p>
                  <p className="text-xs text-slate-500">
                    {ticket.title} · {ticket.skill_tag}
                    {ticket.readiness_score != null ? ` · AI review ${ticket.readiness_score}` : ""}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => void cosign(ticket.id)}
                  className="rounded-full bg-ink px-3 py-1.5 text-xs font-semibold text-white"
                >
                  Co-sign mastery
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
      <DriftRadar persona={persona} />
      {pulse && pulse.clusters.length > 0 && (
        <section className="surface mb-4 grid gap-4 p-4 lg:grid-cols-[280px_1fr]">
          <SentimentDonut
            counts={sentimentCounts(
              pulse.clusters.flatMap((cluster) =>
                Object.entries(cluster.sentiments).flatMap(([sentiment, count]) =>
                  Array.from({ length: count }, () => ({ sentiment })),
                ),
              ),
            )}
            caption="Cohort sentiment, names withheld"
          />
          <div>
            <div className="mb-2 flex items-baseline justify-between">
              <h2 className="text-sm font-semibold">Public topic pulse</h2>
              <p className="text-xs text-slate-500">{pulse.message_count} delivered stories</p>
            </div>
            <ClusterBars clusters={pulse.clusters} />
          </div>
        </section>
      )}
      <div className="mb-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Stat label="Cohort" value={String(cohort.cohort_size)} />
        <Stat label="At risk" value={String(cohort.at_risk_count)} tone="risk" />
        <Stat label="Avg velocity drop" value={`${cohort.avg_velocity_drop}%`} />
        <Stat label="Avg evidence score" value={String(cohort.avg_verified_skill)} />
      </div>
      <div className="surface overflow-auto">
        <table className="w-full min-w-[760px] text-left text-sm">
          <thead className="border-b border-line text-[11px] uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3 font-medium">Student</th>
              <th className="px-4 py-3 font-medium">CGPA</th>
              <th className="px-4 py-3 font-medium">Velocity drop</th>
              <th className="px-4 py-3 font-medium">Blocked core</th>
              <th className="px-4 py-3 font-medium">Evidence</th>
              <th className="px-4 py-3 font-medium">Signal</th>
            </tr>
          </thead>
          <tbody>
            {cohort.students.map((student) => (
              <tr key={student.id} className={`border-t border-line ${student.at_risk ? "bg-rose-50/70" : ""}`}>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <span className="grid h-8 w-8 place-items-center rounded-full bg-ink text-[11px] font-semibold text-white">
                      {student.avatar_initials}
                    </span>
                    <div>
                      <p className="font-medium">{student.name}</p>
                      <p className="mono text-[11px] text-slate-400">{student.anon_token}</p>
                    </div>
                  </div>
                </td>
                <td className="mono px-4 py-3">{student.cgpa.toFixed(1)}</td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <div className="h-1.5 w-24 overflow-hidden rounded-full bg-white">
                      <div
                        className="h-full rounded-full"
                        style={{
                          width: `${Math.min(100, student.velocity_drop_pct)}%`,
                          background: student.velocity_drop_pct > 35 ? "#E11D48" : "#4F46E5",
                        }}
                      />
                    </div>
                    <span className="mono text-xs">{student.velocity_drop_pct.toFixed(0)}%</span>
                  </div>
                </td>
                <td className="mono px-4 py-3">{student.blocked_core}</td>
                <td className="mono px-4 py-3">{student.verified_skill_score}</td>
                <td className="px-4 py-3 text-xs">
                  {student.at_risk ? (
                    <span className="font-medium text-rose-700">{student.risk_reasons.join(" · ")}</span>
                  ) : (
                    <span className="text-emerald-700">
                      On pace{student.top_gap ? ` · gap: ${student.top_gap}` : ""}
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Stat({ label, value, tone }: { label: string; value: string; tone?: "risk" }) {
  return (
    <div className="surface px-4 py-3">
      <p className="text-xs text-slate-500">{label}</p>
      <p className={`mono mt-1 text-2xl font-semibold ${tone === "risk" ? "text-risk" : "text-ink"}`}>{value}</p>
    </div>
  );
}
