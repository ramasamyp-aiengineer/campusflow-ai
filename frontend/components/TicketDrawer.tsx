import { Lock, X } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";

import { COLUMNS, CHEAT_DRAFT, STRONG_DRAFT, THIN_DRAFT } from "@/lib/format";
import type { AIAction, LWIDetail, Status } from "@/lib/types";

export function TicketDrawer({
  detail,
  result,
  busy,
  onClose,
  onMove,
  onUnblock,
  onEvaluate,
}: {
  detail: LWIDetail;
  result: AIAction | null;
  busy: boolean;
  onClose: () => void;
  onMove: (id: number, status: Status) => void;
  onUnblock: (message: string) => void;
  onEvaluate: (submission: string) => void;
}) {
  const [tab, setTab] = useState<"brief" | "unblock" | "rubric" | "deps">("brief");
  const [message, setMessage] = useState("I can't tell which join keeps a faculty row when no student is enrolled.");
  const [submission, setSubmission] = useState(STRONG_DRAFT);
  const score = result?.result.readiness_score;

  useEffect(() => {
    setTab("brief");
  }, [detail.id]);

  return (
    <aside className="flex h-full w-full flex-col border-l border-line bg-white md:w-[420px]">
      <div className="flex items-start justify-between gap-3 border-b border-line px-4 py-3">
        <div>
          <p className="mono text-[11px] text-slate-500">{detail.ticket_code}</p>
          <h2 className="text-base font-semibold leading-5">{detail.title}</h2>
        </div>
        <button onClick={onClose} className="rounded-lg border border-line p-1.5" aria-label="Close ticket">
          <X size={16} />
        </button>
      </div>
      {detail.blocked && (
        <div className="mx-4 mt-3 flex gap-2 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700">
          <Lock size={14} className="mt-0.5 shrink-0" />
          <span>{detail.block_reason}</span>
        </div>
      )}
      <div className="grid grid-cols-4 gap-1 px-4 pt-3">
        {COLUMNS.map((column) => {
          const active = detail.status === column.id;
          const locked =
            (detail.blocked && column.id !== "BACKLOG") || (column.id === "MASTERED" && detail.status !== "AI_REVIEW");
          return (
            <button
              key={column.id}
              disabled={active || locked || busy}
              onClick={() => onMove(detail.id, column.id)}
              className={`rounded-lg px-1 py-1.5 text-[10px] font-semibold ${
                active ? "bg-ink text-white" : "bg-slate-100 text-slate-600 disabled:opacity-40"
              }`}
            >
              {column.label}
            </button>
          );
        })}
      </div>
      <div className="mt-3 flex gap-1 px-4">
        {(
          [
            ["brief", "Brief"],
            ["unblock", "Unblocker"],
            ["rubric", "Rubric"],
            ["deps", "Depends"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={`rounded-full px-3 py-1 text-xs font-medium ${tab === id ? "bg-[#E7F3EF] text-brand" : "text-slate-500"}`}
          >
            {label}
          </button>
        ))}
      </div>
      <div className="min-h-0 flex-1 overflow-auto px-4 py-4">
        {tab === "brief" && (
          <div className="space-y-3 text-sm leading-6 text-slate-700">
            <p>{detail.description}</p>
            <div className="flex flex-wrap gap-2">
              <Chip>{detail.type}</Chip>
              <Chip>{detail.skill_tag}</Chip>
              <Chip>{detail.co_tag}</Chip>
              <Chip>{detail.story_points} story points</Chip>
            </div>
            {detail.prerequisite_title && (
              <p className="rounded-xl bg-canvas px-3 py-2 text-xs text-slate-600">
                Prerequisite: <span className="mono">{detail.prerequisite_code}</span> {detail.prerequisite_title}
              </p>
            )}
          </div>
        )}
        {tab === "unblock" && (
          <div className="space-y-3">
            <p className="text-xs leading-5 text-slate-500">
              The tutor will not write the graded answer. Paste the point where you are stuck, or try the refusal case.
            </p>
            <textarea
              className="field min-h-28 text-sm"
              value={message}
              onChange={(event) => setMessage(event.target.value)}
            />
            <div className="flex flex-wrap gap-2">
              <button
                disabled={busy}
                onClick={() => onUnblock(message)}
                className="rounded-full bg-brand px-3 py-1.5 text-xs font-semibold text-white"
              >
                Ask for a hint
              </button>
              <button
                disabled={busy}
                onClick={() => {
                  setMessage(CHEAT_DRAFT);
                  onUnblock(CHEAT_DRAFT);
                }}
                className="rounded-full border border-line px-3 py-1.5 text-xs font-semibold"
              >
                Try “write the code”
              </button>
            </div>
            <ResultCard result={result} />
          </div>
        )}
        {tab === "rubric" && (
          <div className="space-y-3">
            <ul className="space-y-1 text-xs text-slate-600">
              {detail.rubric_criteria.map((criterion) => (
                <li key={criterion}>· {criterion}</li>
              ))}
            </ul>
            <textarea
              className="field min-h-32 text-sm"
              value={submission}
              onChange={(event) => setSubmission(event.target.value)}
            />
            <div className="flex flex-wrap gap-2">
              <button
                disabled={busy}
                onClick={() => onEvaluate(submission)}
                className="rounded-full bg-brand px-3 py-1.5 text-xs font-semibold text-white"
              >
                Run rubric audit
              </button>
              <button
                className="rounded-full border border-line px-3 py-1.5 text-xs"
                onClick={() => setSubmission(STRONG_DRAFT)}
              >
                Strong draft
              </button>
              <button
                className="rounded-full border border-line px-3 py-1.5 text-xs"
                onClick={() => setSubmission(THIN_DRAFT)}
              >
                Thin draft
              </button>
              <button
                className="rounded-full border border-line px-3 py-1.5 text-xs"
                onClick={() => setSubmission(CHEAT_DRAFT)}
              >
                Direct solution
              </button>
            </div>
            {score !== null && score !== undefined && (
              <div className="flex items-end justify-between rounded-xl bg-canvas px-3 py-3">
                <div>
                  <p className="text-[11px] uppercase tracking-wide text-slate-500">Readiness</p>
                  <p
                    className="mono text-3xl font-semibold"
                    style={{ color: score >= 75 ? "#059669" : score >= 55 ? "#D97706" : "#E11D48" }}
                  >
                    {score}
                  </p>
                </div>
                <p className="max-w-[180px] text-right text-xs text-slate-500">
                  Score updates the skill graph at 70+. Mastery still waits for AI Review.
                </p>
              </div>
            )}
            <ResultCard result={result} />
          </div>
        )}
        {tab === "deps" && (
          <ol className="space-y-2">
            {detail.prerequisite_chain.length === 0 && (
              <li className="text-sm text-slate-500">This ticket has no open prerequisite chain.</li>
            )}
            {detail.prerequisite_chain.map((node, index) => (
              <li key={node.id} className="rounded-xl border border-line px-3 py-2">
                <p className="mono text-[11px] text-slate-500">
                  {index + 1}. {node.ticket_code}
                </p>
                <p className="text-sm font-medium">{node.title}</p>
                <p className="text-[11px] text-slate-500">{node.status.replace(/_/g, " ")}</p>
              </li>
            ))}
            <li className="rounded-xl border border-brand/30 bg-[#E7F3EF] px-3 py-2">
              <p className="mono text-[11px] text-brand">Current · {detail.ticket_code}</p>
              <p className="text-sm font-medium">{detail.title}</p>
            </li>
            {detail.dependents.map((node) => (
              <li key={node.id} className="rounded-xl border border-dashed border-line px-3 py-2">
                <p className="mono text-[11px] text-slate-500">Unlocks {node.ticket_code}</p>
                <p className="text-sm">{node.title}</p>
                {node.blocked && <p className="text-[11px] text-rose-600">Waiting on this ticket</p>}
              </li>
            ))}
          </ol>
        )}
      </div>
    </aside>
  );
}

function Chip({ children }: { children: ReactNode }) {
  return <span className="rounded-md bg-slate-100 px-2 py-1 text-[11px] font-medium text-slate-600">{children}</span>;
}

function ResultCard({ result }: { result: AIAction | null }) {
  if (!result) return null;
  const refused = result.result.refused_direct_solution;
  return (
    <div
      className={`rounded-xl border px-3 py-3 text-sm ${refused ? "border-amber-200 bg-amber-50" : "border-line bg-white"}`}
    >
      <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
        {refused ? "Direct solution refused" : "Guidance"}
      </p>
      <p className="mt-1 font-medium text-ink">{result.result.diagnosed_gap}</p>
      <p className="mt-2 text-slate-700">{result.result.guiding_question}</p>
      {result.result.checks.length > 0 && (
        <ul className="mt-3 space-y-1.5">
          {result.result.checks.map((check) => (
            <li key={check.criterion} className="text-xs">
              <span className={check.passed ? "text-emerald-700" : "text-rose-700"}>
                {check.passed ? "Pass" : "Gap"}
              </span>
              <span className="text-slate-600"> · {check.criterion}</span>
            </li>
          ))}
        </ul>
      )}
      {result.result.actionable_fixes.length > 0 && (
        <ul className="mt-2 list-disc space-y-1 pl-4 text-xs text-slate-600">
          {result.result.actionable_fixes.map((fix) => (
            <li key={fix}>{fix}</li>
          ))}
        </ul>
      )}
      {result.remediation_lwi && (
        <p className="mt-3 rounded-lg bg-white px-2 py-1.5 text-xs text-slate-700">
          Filed <span className="mono">{result.remediation_lwi.ticket_code}</span> · {result.remediation_lwi.title}
        </p>
      )}
      <p className="mt-2 text-[11px] text-slate-500">
        {result.guard.redactions > 0 ? `${result.guard.redactions} identifiers stripped before inference. ` : ""}
        {result.guard.injection_flags.length > 0 ? "Instruction override neutralized. " : ""}
        Output matched the response schema.
      </p>
    </div>
  );
}
