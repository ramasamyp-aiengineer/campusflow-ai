import { ArrowRight, BookOpen, Briefcase, Lock, Rss, Sparkles, Target } from "lucide-react";

import { Ring } from "@/components/Ring";
import { SentimentDonut } from "@/components/SentimentCharts";
import { SENTIMENT_STYLE, scoreColor, waitLabel } from "@/lib/format";
import type { Dashboard, View } from "@/lib/types";

const ACTION_ICON: Record<string, typeof Lock> = {
  unblock: Lock,
  review: Sparkles,
  read: Rss,
  follow: Rss,
  skill: Target,
  placement: Briefcase,
};

const PIPELINE = [
  { key: "backlog", label: "Backlog", color: "#B9AE9F" },
  { key: "in_progress", label: "In progress", color: "#0E7C66" },
  { key: "ai_review", label: "AI review", color: "#C47B12" },
  { key: "mastered", label: "Mastered", color: "#0F7A4A" },
] as const;

const ACTIVITY_LABEL: Record<string, string> = {
  "lwi.status": "Moved a ticket",
  "lwi.create": "Added a ticket",
  "lwi.unblock": "Asked the Socratic unblocker",
  "lwi.evaluate": "Submitted for review",
  "sprint.generate": "Built a sprint from a syllabus",
  "placement.analyze": "Matched a job description",
  "signals.subscribe": "Fetched an interest",
  "signals.briefing": "Ran the campus briefing",
  "signals.remove": "Removed an interest",
  "signals.task": "Turned a story into a lab task",
  "signals.quiz": "Passed a story quiz",
  "security.preview": "Previewed a redaction",
};

function greeting(): string {
  const hour = new Date().getHours();
  if (hour < 5) return "Hello";
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}

function when(iso: string): string {
  const minutes = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (Number.isNaN(minutes)) return "";
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

export function DashboardView({
  data,
  onNavigate,
  onOpenSprint,
  onOpenTopics,
}: {
  data: Dashboard | null;
  onNavigate: (view: View) => void;
  onOpenSprint: (id: number) => void;
  onOpenTopics: () => void;
}) {
  if (!data)
    return <div className="grid h-full place-items-center text-sm text-slate-500">Pulling your record together…</div>;
  const { tickets, interests, skills } = data;
  const firstName = data.student.name.split(" ")[0];

  return (
    <div className="h-full overflow-auto bg-[#F7F4EF]">
      <div className="mx-auto max-w-6xl px-5 py-6">
        <header className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-copper">Dashboard</p>
            <h1 className="mt-1 text-[2rem] leading-tight text-ink">
              {greeting()}, {firstName}
            </h1>
            <p className="mt-1 text-sm text-slate-500">
              {data.student.program} · Semester {data.student.semester} · CGPA {data.student.cgpa.toFixed(1)} ·{" "}
              <span className="mono">{data.student.anon_token}</span>
            </p>
          </div>
          <span
            className={`rounded-full px-3 py-1.5 text-xs font-semibold ${
              data.shortlist_ready ? "bg-[#E7F3EF] text-brand" : "bg-amber-50 text-amber-800"
            }`}
          >
            {data.shortlist_ready
              ? "Shortlist ready"
              : `${data.shortlist_bar - data.verified_skill_score} points from the shortlist bar`}
          </span>
        </header>

        <section className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Semester progress" hint="Story points mastered">
            <Ring value={data.semester_progress} size={58} color="#C46B2C" track="#F3EEE6" />
          </StatCard>
          <StatCard label="Verified skill" hint={`${skills.count} skills with evidence`}>
            <Ring
              value={data.verified_skill_score}
              size={58}
              color={scoreColor(data.verified_skill_score)}
              track="#F3EEE6"
            />
          </StatCard>
          <StatCard label="Tickets mastered" hint={`${tickets.points_mastered} of ${tickets.points_total} points`}>
            <p className="mono text-2xl font-semibold text-ink">
              {tickets.mastered}
              <span className="text-base text-slate-400">/{tickets.total}</span>
            </p>
          </StatCard>
          <StatCard label="Unread reading" hint={`${interests.saved} saved across ${interests.topics} topics`}>
            <p className="mono text-2xl font-semibold text-ink">{interests.unread}</p>
          </StatCard>
        </section>

        <div className="mt-5 grid gap-5 lg:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)]">
          <div className="space-y-5">
            <Panel title="Up next" note="Picked from your board, skills and reading">
              {data.next_actions.length === 0 ? (
                <p className="text-sm text-slate-500">Nothing urgent. Nice work.</p>
              ) : (
                <ul className="space-y-2">
                  {data.next_actions.map((action) => {
                    const Icon = ACTION_ICON[action.kind] ?? Sparkles;
                    return (
                      <li key={action.kind}>
                        <button
                          onClick={() => onNavigate(action.view)}
                          className="group flex w-full items-center gap-3 rounded-2xl border border-line bg-[#FBF9F5] px-3 py-3 text-left transition hover:-translate-y-0.5 hover:bg-white hover:shadow-card"
                        >
                          <span
                            className={`grid h-9 w-9 shrink-0 place-items-center rounded-xl ${action.kind === "unblock" ? "bg-rose-50 text-rose-700" : "bg-[#F4E6CF] text-copper"}`}
                          >
                            <Icon size={16} />
                          </span>
                          <span className="min-w-0 flex-1">
                            <span className="block text-sm font-semibold text-ink">{action.title}</span>
                            <span className="block text-xs text-slate-500">{action.detail}</span>
                          </span>
                          <ArrowRight
                            size={16}
                            className="text-slate-300 transition group-hover:translate-x-0.5 group-hover:text-ink"
                          />
                        </button>
                      </li>
                    );
                  })}
                </ul>
              )}
            </Panel>

            <Panel
              title="Ticket pipeline"
              note={tickets.blocked ? `${tickets.blocked} blocked by a prerequisite` : "Nothing blocked"}
            >
              <div className="flex h-3 overflow-hidden rounded-full bg-[#F3EEE6]">
                {PIPELINE.map((stage) => {
                  const count = tickets[stage.key];
                  if (!count || !tickets.total) return null;
                  return (
                    <div
                      key={stage.key}
                      title={`${stage.label} ${count}`}
                      style={{ width: `${(count / tickets.total) * 100}%`, background: stage.color }}
                    />
                  );
                })}
              </div>
              <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
                {PIPELINE.map((stage) => (
                  <button
                    key={stage.key}
                    onClick={() => onNavigate("board")}
                    className="rounded-xl px-2 py-1.5 text-left hover:bg-[#FBF9F5]"
                  >
                    <span className="flex items-center gap-1.5 text-[11px] text-slate-500">
                      <span className="h-2 w-2 rounded-full" style={{ background: stage.color }} />
                      {stage.label}
                    </span>
                    <span className="mono text-lg font-semibold text-ink">{tickets[stage.key]}</span>
                  </button>
                ))}
              </div>
            </Panel>

            <Panel title="Courses" note={`${data.sprints.length} active`}>
              <ul className="divide-y divide-line">
                {data.sprints.map((sprint) => (
                  <li key={sprint.id}>
                    <button
                      onClick={() => onOpenSprint(sprint.id)}
                      className="flex w-full items-center gap-3 py-2.5 text-left hover:text-brand"
                    >
                      <span className="mono w-14 shrink-0 text-[11px] text-copper">{sprint.course_code}</span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm font-medium">{sprint.title}</span>
                        <span className="mt-1 block h-1.5 overflow-hidden rounded-full bg-[#F3EEE6]">
                          <span
                            className="block h-full rounded-full bg-[#E7B15A]"
                            style={{ width: `${sprint.progress_percent}%` }}
                          />
                        </span>
                      </span>
                      <span className="mono w-16 shrink-0 text-right text-[11px] text-slate-500">
                        {sprint.mastered_count}/{sprint.lwi_count} · {sprint.progress_percent}%
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </Panel>
          </div>

          <div className="space-y-5">
            <Panel
              title="Skills"
              note="Only evidence counts"
              action={{ label: "Open graph", onClick: () => onNavigate("skills") }}
            >
              <ul className="space-y-2.5">
                {skills.top.map((skill) => (
                  <SkillBar key={skill.name} name={skill.name} score={skill.score} />
                ))}
              </ul>
              {skills.weakest && (
                <p className="mt-3 rounded-xl bg-amber-50 px-3 py-2 text-xs text-amber-900">
                  Lowest right now: <span className="font-semibold">{skills.weakest.name}</span> at{" "}
                  {skills.weakest.score}.
                </p>
              )}
            </Panel>

            <Panel
              title="Interests"
              note={interests.next_fetch ? `Next fetch in ${waitLabel(interests.next_fetch)}` : "No topics yet"}
              action={{ label: "Open", onClick: onOpenTopics }}
            >
              {interests.saved ? (
                <>
                  <SentimentDonut counts={interests.sentiments} caption="Tone of your reading" />
                  <ul className="mt-4 space-y-2">
                    {interests.latest.map((story) => {
                      const tone = SENTIMENT_STYLE[story.sentiment] ?? SENTIMENT_STYLE.Neutral;
                      return (
                        <li key={story.id}>
                          <button
                            onClick={onOpenTopics}
                            className="flex w-full items-start gap-2 text-left text-sm hover:text-brand"
                          >
                            <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full" style={{ background: tone.bar }} />
                            <span className="min-w-0">
                              <span className={`block leading-5 ${story.is_read ? "" : "font-semibold"}`}>
                                {story.title}
                              </span>
                              <span className="text-[11px] text-slate-400">{story.topic}</span>
                            </span>
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                </>
              ) : (
                <button
                  onClick={onOpenTopics}
                  className="inline-flex items-center gap-2 text-sm font-semibold text-brand"
                >
                  <BookOpen size={14} /> Follow your first topic
                </button>
              )}
            </Panel>

            <Panel title="Recent activity" note="From the audit log">
              {data.activity.length === 0 ? (
                <p className="text-sm text-slate-500">No activity yet.</p>
              ) : (
                <ol className="space-y-3">
                  {data.activity.map((event, position) => (
                    <li key={`${event.created_at}-${position}`} className="flex gap-3">
                      <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-copper" />
                      <span className="min-w-0 flex-1">
                        <span className="flex items-baseline justify-between gap-2">
                          <span className="text-sm font-medium text-ink">
                            {ACTIVITY_LABEL[event.action] ?? event.action}
                          </span>
                          <span className="shrink-0 text-[11px] text-slate-400">{when(event.created_at)}</span>
                        </span>
                        <span className="mono block truncate text-[11px] text-slate-500">{event.detail}</span>
                      </span>
                    </li>
                  ))}
                </ol>
              )}
            </Panel>
          </div>
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, hint, children }: { label: string; hint: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-3xl border border-line bg-white px-4 py-4">
      <div>
        <p className="text-sm font-semibold text-ink">{label}</p>
        <p className="mt-0.5 text-[11px] text-slate-500">{hint}</p>
      </div>
      {children}
    </div>
  );
}

function Panel({
  title,
  note,
  action,
  children,
}: {
  title: string;
  note?: string;
  action?: { label: string; onClick: () => void };
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-3xl border border-line bg-white p-5">
      <div className="mb-3 flex items-baseline justify-between gap-3">
        <h2 className="text-lg leading-none text-ink">{title}</h2>
        <div className="flex items-baseline gap-3">
          {note && <p className="text-[11px] text-slate-400">{note}</p>}
          {action && (
            <button onClick={action.onClick} className="text-xs font-semibold text-brand">
              {action.label}
            </button>
          )}
        </div>
      </div>
      {children}
    </section>
  );
}

function SkillBar({ name, score }: { name: string; score: number }) {
  return (
    <li>
      <div className="mb-1 flex items-baseline justify-between text-sm">
        <span className="font-medium text-ink">{name}</span>
        <span className="mono text-xs" style={{ color: scoreColor(score) }}>
          {score}
        </span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-[#F3EEE6]">
        <div className="h-full rounded-full" style={{ width: `${score}%`, background: scoreColor(score) }} />
      </div>
    </li>
  );
}
