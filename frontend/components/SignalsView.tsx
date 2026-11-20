"use client";

import {
  BarChart3,
  BookOpen,
  Briefcase,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  ExternalLink,
  GraduationCap,
  Layers,
  Newspaper,
  Plus,
  RefreshCw,
  Rss,
  Sparkles,
  Target,
  Trash2,
  TrendingUp,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { SentimentDonut } from "@/components/SentimentCharts";
import { ApiError, api, safeHref } from "@/lib/api";
import { SAMPLE_INTERESTS, SENTIMENT_ORDER, SENTIMENT_STYLE, SIGNALS_POLL_MS, waitLabel } from "@/lib/format";
import type {
  InterestAnalysis,
  InterestCluster,
  Persona,
  QuizResult,
  SignalInbox,
  SignalMessage,
  StoryExplainer,
  StoryTask,
  SubscribeResult,
} from "@/lib/types";

type Tab = "stories" | "sentiment" | "topics";
type SortKey = "sentiment_score" | "relevance_score";

const TABS: { id: Tab; label: string; icon: typeof BookOpen }[] = [
  { id: "stories", label: "Stories", icon: BookOpen },
  { id: "sentiment", label: "Sentiment", icon: BarChart3 },
  { id: "topics", label: "Topics", icon: Layers },
];

const FLOW = [
  { title: "You add a topic", detail: "A name and an RSS link" },
  { title: "We fetch it", detail: "Now, then every 8 hours" },
  { title: "We keep what fits", detail: "Off-topic stories are dropped" },
  { title: "We read the tone", detail: "Positive, watchful, critical" },
  { title: "We group it", detail: "Smaller topics inside your interest" },
];

export function SignalsView({ persona, onChanged, onOpenSprint }: { persona: Persona; onChanged: () => void; onOpenSprint: (id: number) => void }) {
  const [inbox, setInbox] = useState<SignalInbox | null>(null);
  const [analysis, setAnalysis] = useState<InterestAnalysis | null>(null);
  const [topicId, setTopicId] = useState<number | null>(null);
  const [tab, setTab] = useState<Tab>("stories");
  const [index, setIndex] = useState(0);
  const [adding, setAdding] = useState(false);
  const [topic, setTopic] = useState("Machine Learning");
  const [url, setUrl] = useState(SAMPLE_INTERESTS[0].url);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [version, setVersion] = useState(0);

  const load = useCallback(async () => {
    const data = await api<SignalInbox>("/api/v1/signals", persona);
    setInbox(data);
    setTopicId((current) => (current && data.feeds.some((feed) => feed.id === current) ? current : data.feeds[0]?.id ?? null));
    setVersion((value) => value + 1);
  }, [persona]);

  useEffect(() => {
    load().catch((reason: Error) => setError(reason.message));
    const timer = window.setInterval(() => {
      if (document.visibilityState === "visible") load().catch(() => undefined);
    }, SIGNALS_POLL_MS);
    return () => window.clearInterval(timer);
  }, [load]);

  useEffect(() => {
    if (topicId === null) {
      setAnalysis(null);
      return;
    }
    let ignore = false;
    api<InterestAnalysis>(`/api/v1/signals/feeds/${topicId}/analysis`, persona)
      .then((data) => {
        if (!ignore) setAnalysis(data);
      })
      .catch(() => {
        if (!ignore) setAnalysis(null);
      });
    return () => {
      ignore = true;
    };
  }, [topicId, persona, version]);

  useEffect(() => {
    setIndex(0);
  }, [topicId]);

  const stories = useMemo(() => {
    if (!inbox || topicId === null) return [];
    return inbox.messages.filter((message) => message.subscription_id === topicId);
  }, [inbox, topicId]);

  const feed = inbox?.feeds.find((item) => item.id === topicId) ?? null;
  const report = analysis && analysis.feed.id === topicId ? analysis : null;
  const story = stories[Math.min(index, Math.max(0, stories.length - 1))] ?? null;

  async function addInterest(nextTopic: string, nextUrl: string) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const result = await api<SubscribeResult>("/api/v1/signals/feeds", persona, {
        method: "POST",
        body: JSON.stringify({ url: nextUrl, label: nextTopic }),
      });
      setNotice(
        `Done. ${nextTopic} kept ${result.kept} ${result.kept === 1 ? "story" : "stories"}${result.held ? `, skipped ${result.held} off-topic` : ""}${
          result.fused ? `, and merged ${result.fused} repeat${result.fused === 1 ? "" : "s"} into stories you already had` : ""
        }.`,
      );
      await load();
      setTopicId(result.feed.id);
      setTab("stories");
      setAdding(false);
      onChanged();
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : "That feed could not be read";
      if (reason instanceof ApiError && reason.status === 409) setNotice(message);
      else setError(message);
    } finally {
      setBusy(false);
    }
  }

  async function removeInterest(id: number) {
    if (!window.confirm("Remove this interest and its saved stories?")) return;
    try {
      await api(`/api/v1/signals/feeds/${id}`, persona, { method: "DELETE" });
      setTopicId(null);
      await load();
      onChanged();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not remove that interest");
    }
  }

  async function openStory(id: number) {
    const position = stories.findIndex((message) => message.id === id);
    if (position < 0) return;
    setIndex(position);
    setTab("stories");
    const message = stories[position];
    if (message.is_read) return;
    await api(`/api/v1/signals/messages/${message.id}/read`, persona, { method: "PATCH" });
    setInbox((current) =>
      current ? { ...current, messages: current.messages.map((item) => (item.id === message.id ? { ...item, is_read: true } : item)) } : current,
    );
    onChanged();
  }

  if (!inbox && !error) {
    return <div className="grid h-full place-items-center text-sm text-slate-500">Getting your reading ready…</div>;
  }

  return (
    <div className="h-full overflow-auto bg-[#F7F4EF]">
      <div className="mx-auto max-w-6xl px-5 py-6">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-copper">My interests</p>
            <h1 className="mt-1 text-[1.9rem] leading-tight text-ink">Follow what you care about</h1>
            <p className="mt-1 max-w-xl text-sm leading-6 text-slate-500">
              Add a topic with an RSS link. We save the stories that fit, then show you how they feel and what they are about.
            </p>
          </div>
          <button
            onClick={() => setAdding((open) => !open)}
            className="inline-flex items-center gap-1.5 rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white transition hover:bg-black"
          >
            <Plus size={15} /> Add interest
          </button>
        </div>

        <ol className="mt-5 grid gap-2 sm:grid-cols-5">
          {FLOW.map((step, position) => (
            <li key={step.title} className="rounded-2xl border border-line bg-white px-3 py-2.5">
              <p className="flex items-center gap-2 text-xs font-semibold text-ink">
                <span className="grid h-5 w-5 place-items-center rounded-full bg-[#F4E6CF] text-[10px] text-copper">{position + 1}</span>
                {step.title}
              </p>
              <p className="mt-1 text-[11px] text-slate-500">{step.detail}</p>
            </li>
          ))}
        </ol>

        {adding && (
          <AddInterestForm
            busy={busy}
            topic={topic}
            url={url}
            onTopic={setTopic}
            onUrl={setUrl}
            onCancel={() => setAdding(false)}
            onSubmit={() => void addInterest(topic.trim(), url.trim())}
          />
        )}

        {notice && <p className="mt-4 rounded-2xl bg-[#E7F3EF] px-4 py-2.5 text-sm text-brand">{notice}</p>}
        {error && <p className="mt-4 rounded-2xl bg-rose-50 px-4 py-2.5 text-sm text-rose-700">{error}</p>}

        <div className="mt-6 grid gap-5 lg:grid-cols-[240px_minmax(0,1fr)]">
          <aside className="min-w-0">
            <p className="mb-2 px-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">Your topics</p>
            <div className="flex gap-2 overflow-auto pb-1 lg:block lg:space-y-1.5" role="tablist" aria-label="Interests">
              {(inbox?.feeds ?? []).map((item) => {
                const count = inbox?.messages.filter((message) => message.subscription_id === item.id).length ?? 0;
                const unread = inbox?.messages.filter((message) => message.subscription_id === item.id && !message.is_read).length ?? 0;
                const active = item.id === topicId;
                return (
                  <button
                    key={item.id}
                    role="tab"
                    aria-selected={active}
                    onClick={() => setTopicId(item.id)}
                    className={`flex w-60 shrink-0 items-center justify-between gap-3 rounded-2xl px-3 py-2.5 text-left transition lg:w-full ${
                      active ? "bg-ink text-white shadow-lift" : "bg-white text-ink hover:-translate-y-0.5 hover:shadow-card"
                    }`}
                  >
                    <span className="min-w-0">
                      <span className="block truncate text-sm font-semibold">{item.label}</span>
                      <span className={`text-[11px] ${active ? "text-white/60" : "text-slate-400"}`}>{count} saved</span>
                    </span>
                    {unread > 0 && <span className="mono rounded-full bg-copper px-1.5 py-0.5 text-[10px] font-semibold text-white">{unread}</span>}
                  </button>
                );
              })}
              {(inbox?.feeds.length ?? 0) === 0 && (
                <p className="rounded-2xl border border-dashed border-line bg-white px-3 py-4 text-sm text-slate-500">No topics yet. Try adding Machine Learning.</p>
              )}
            </div>
          </aside>

          <section className="min-w-0">
            {feed ? (
              <>
                <div className="rounded-3xl border border-line bg-white px-5 py-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <h2 className="text-2xl leading-tight text-ink">{feed.label}</h2>
                      <p className="mt-1 text-xs text-slate-500">
                        {stories.length} saved · checked {feed.items_seen} last time, kept {feed.items_kept} · next check in {waitLabel(feed.next_poll_at)}
                      </p>
                      <p className="mono mt-1 truncate text-[11px] text-slate-400">{feed.url}</p>
                      {feed.last_status === "error" && feed.last_error && (
                        <p className="mt-2 rounded-xl bg-rose-50 px-3 py-1.5 text-xs text-rose-800">Last check failed: {feed.last_error}</p>
                      )}
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => void addInterest(feed.label, feed.url)}
                        disabled={busy}
                        className="inline-flex items-center gap-1 rounded-full border border-line px-3 py-1.5 text-xs text-slate-600 hover:text-brand disabled:opacity-50"
                      >
                        <RefreshCw size={13} className={busy ? "animate-spin" : ""} /> Check now
                      </button>
                      <button onClick={() => void removeInterest(feed.id)} className="inline-flex items-center gap-1 rounded-full border border-line px-3 py-1.5 text-xs text-slate-500 hover:text-rose-700">
                        <Trash2 size={13} /> Remove
                      </button>
                    </div>
                  </div>
                  <div className="mt-4 flex gap-1 rounded-full bg-[#F3EEE6] p-1" role="tablist" aria-label="Interest views">
                    {TABS.map((item) => {
                      const Icon = item.icon;
                      const active = tab === item.id;
                      return (
                        <button
                          key={item.id}
                          role="tab"
                          aria-selected={active}
                          onClick={() => setTab(item.id)}
                          className={`inline-flex flex-1 items-center justify-center gap-1.5 rounded-full px-3 py-2 text-sm font-semibold transition ${
                            active ? "bg-white text-ink shadow-card" : "text-slate-500 hover:text-ink"
                          }`}
                        >
                          <Icon size={15} /> {item.label}
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div className="mt-4">
                  {tab === "stories" &&
                    (story ? (
                      <Article
                        message={story}
                        persona={persona}
                        position={stories.indexOf(story) + 1}
                        total={stories.length}
                        onPrevious={() => void openStory(stories[Math.max(0, stories.indexOf(story) - 1)].id)}
                        onNext={() => void openStory(stories[Math.min(stories.length - 1, stories.indexOf(story) + 1)].id)}
                        onUpdated={async () => {
                          await load();
                          onChanged();
                        }}
                        onOpenSprint={onOpenSprint}
                      />
                    ) : (
                      <Empty text="Nothing saved for this topic yet. We will check again at the next fetch." />
                    ))}
                  {tab === "sentiment" && (report ? <SentimentTab analysis={report} onOpen={openStory} /> : <Empty text="Reading the tone…" />)}
                  {tab === "topics" && (report ? <TopicsTab analysis={report} onOpen={openStory} /> : <Empty text="Grouping the stories…" />)}
                </div>
              </>
            ) : (
              <Empty text="Pick a topic on the left, or add your first one." />
            )}
          </section>
        </div>
      </div>
    </div>
  );
}

function AddInterestForm({
  busy,
  topic,
  url,
  onTopic,
  onUrl,
  onCancel,
  onSubmit,
}: {
  busy: boolean;
  topic: string;
  url: string;
  onTopic: (value: string) => void;
  onUrl: (value: string) => void;
  onCancel: () => void;
  onSubmit: () => void;
}) {
  return (
    <form
      className="mt-5 rounded-3xl border border-line bg-white p-5 shadow-card"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      <h2 className="text-lg text-ink">Add an interest</h2>
      <p className="mt-0.5 text-sm text-slate-500">Quick starts are labeled sample stories. A pasted public RSS link is a live feed.</p>
      <div className="mt-3 flex flex-wrap gap-2">
        {SAMPLE_INTERESTS.map((item) => (
          <button
            key={item.topic}
            type="button"
            onClick={() => {
              onTopic(item.topic);
              onUrl(item.url);
            }}
            className={`rounded-2xl border px-3 py-2 text-left transition ${topic === item.topic ? "border-brand bg-[#E7F3EF]" : "border-line bg-[#FBF9F5] hover:border-slate-300"}`}
          >
            <span className="block text-sm font-semibold text-ink">{item.topic}</span>
            <span className="text-[11px] text-slate-500">{item.detail}</span>
          </button>
        ))}
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-[220px_1fr]">
        <label htmlFor="interest-topic" className="text-xs font-medium text-slate-500">
          Topic name
          <input id="interest-topic" className="field mt-1" value={topic} onChange={(event) => onTopic(event.target.value)} placeholder="Machine Learning" required minLength={2} />
        </label>
        <label htmlFor="interest-url" className="text-xs font-medium text-slate-500">
          RSS link
          <input id="interest-url" className="field mt-1" value={url} onChange={(event) => onUrl(event.target.value)} placeholder="https://news.google.com/rss/search?q=machine+learning" required />
        </label>
      </div>
      <div className="mt-4 flex justify-end gap-2">
        <button type="button" onClick={onCancel} className="rounded-full border border-line px-4 py-2 text-sm">
          Cancel
        </button>
        <button disabled={busy} className="inline-flex items-center gap-2 rounded-full bg-brand px-4 py-2 text-sm font-semibold text-white disabled:opacity-60">
          <Rss size={14} /> {busy ? "Fetching…" : "Fetch and save"}
        </button>
      </div>
    </form>
  );
}

const BADGE_STYLE: Record<string, { icon: typeof Target; className: string }> = {
  task: { icon: ClipboardList, className: "bg-ink text-white" },
  ticket: { icon: Target, className: "bg-[#E7F3EF] text-brand" },
  gap: { icon: TrendingUp, className: "bg-[#F4E6CF] text-[#8A4A1C]" },
  placement: { icon: Briefcase, className: "bg-sky-50 text-sky-800" },
  skill: { icon: Sparkles, className: "bg-[#F3EEE6] text-slate-700" },
};

function Article({
  message,
  persona,
  position,
  total,
  onPrevious,
  onNext,
  onUpdated,
  onOpenSprint,
}: {
  message: SignalMessage;
  persona: Persona;
  position: number;
  total: number;
  onPrevious: () => void;
  onNext: () => void;
  onUpdated: () => Promise<void>;
  onOpenSprint: (id: number) => void;
}) {
  const tone = SENTIMENT_STYLE[message.sentiment] ?? SENTIMENT_STYLE.Neutral;
  const [showSources, setShowSources] = useState(false);
  const [quizOpen, setQuizOpen] = useState(false);
  const [task, setTask] = useState<StoryTask | null>(null);
  const [taskBusy, setTaskBusy] = useState(false);
  const [taskError, setTaskError] = useState("");
  const taskBadge = message.badges.find((badge) => badge.kind === "task");
  const reasons = message.badges.filter((badge) => badge.kind !== "task");

  useEffect(() => {
    setShowSources(false);
    setQuizOpen(false);
    setTask(null);
    setTaskError("");
  }, [message.id]);

  async function makeTask() {
    setTaskBusy(true);
    setTaskError("");
    try {
      const result = await api<StoryTask>(`/api/v1/signals/messages/${message.id}/task`, persona, { method: "POST" });
      setTask(result);
      await onUpdated();
    } catch (reason) {
      setTaskError(reason instanceof Error ? reason.message : "Could not create the task");
    } finally {
      setTaskBusy(false);
    }
  }

  return (
    <article className="rounded-3xl border border-line bg-white p-6 shadow-card">
      <div className="flex items-center justify-between gap-3">
        <p className="mono text-[11px] text-slate-400">
          Story {position} of {total}
        </p>
        <div className="flex items-center gap-2">
          {message.sources.length > 1 && (
            <button
              onClick={() => setShowSources((open) => !open)}
              aria-expanded={showSources}
              className="inline-flex items-center gap-1 rounded-full bg-[#E7F3EF] px-2.5 py-1 text-[11px] font-semibold text-brand"
            >
              <Newspaper size={12} /> Reported by {message.sources.length} sources
            </button>
          )}
          <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${tone.wash} ${tone.text}`}>{message.sentiment}</span>
        </div>
      </div>
      <h3 className="display mt-3 text-[1.65rem] leading-tight text-ink">{message.title}</h3>
      {message.sample && (
        <p className="mt-2 rounded-xl bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-900">
          Sample story. The link is a reference document, not a news article about this headline.
        </p>
      )}
      <p className="mt-2 text-sm text-slate-500">
        {message.source}
        {message.published_at ? ` · ${message.published_at}` : ""}
      </p>
      {showSources && (
        <ul className="mt-3 space-y-1 rounded-2xl border border-line bg-[#FBF9F5] px-4 py-3 text-sm">
          {message.sources.map((link) => (
            <li key={`${link.source}-${link.url}`} className="flex items-center justify-between gap-3">
              <span className="font-medium text-ink">{link.source}</span>
              {safeHref(link.url) ? (
                <a href={safeHref(link.url)} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-xs text-brand">
                  Open <ExternalLink size={12} />
                </a>
              ) : (
                <span className="text-xs text-slate-400">Sample story</span>
              )}
            </li>
          ))}
        </ul>
      )}

      <div className="mt-4">
        <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">Why this matters for your skill graph</p>
        {reasons.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-2">
            {reasons.map((badge) => {
              const style = BADGE_STYLE[badge.kind] ?? BADGE_STYLE.skill;
              const Icon = style.icon;
              return (
                <span key={badge.label} title={badge.detail} className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ${style.className}`}>
                  <Icon size={13} /> {badge.label}
                </span>
              );
            })}
          </div>
        )}
        <p className="mt-1.5 text-xs leading-5 text-slate-500">{message.relevance_reason}</p>
      </div>

      <div className="mt-5 rounded-2xl bg-[#F7F4EF] px-4 py-4">
        <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-copper">{message.brief_source === "gemini" ? "Gemini summary" : "Quick summary"}</p>
        <p className="mt-2 text-[15px] leading-7 text-ink">{message.brief || message.summary}</p>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-2">
        {task || taskBadge ? (
          <button
            onClick={() => task && onOpenSprint(task.sprint.id)}
            disabled={!task}
            className="inline-flex items-center gap-1.5 rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white disabled:cursor-default"
          >
            <ClipboardList size={15} /> {task ? `Added ${task.lwi.ticket_code} to Backlog · open board` : taskBadge?.label}
          </button>
        ) : (
          <button
            onClick={() => void makeTask()}
            disabled={taskBusy}
            className="inline-flex items-center gap-1.5 rounded-full bg-brand px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
          >
            <ClipboardList size={15} /> {taskBusy ? "Planning the lab…" : "Turn into sprint task"}
          </button>
        )}
        <button
          onClick={() => setQuizOpen((open) => !open)}
          aria-expanded={quizOpen}
          className={`inline-flex items-center gap-1.5 rounded-full border px-4 py-2 text-sm font-semibold transition ${
            quizOpen ? "border-ink bg-[#F3EEE6] text-ink" : "border-line text-slate-700 hover:border-slate-300"
          }`}
        >
          <GraduationCap size={15} /> {message.quiz_passed ? "Quiz passed · review" : "Explain & quiz me"}
        </button>
      </div>
      {task && (
        <p className="mt-2 text-xs text-slate-500">
          {task.lwi.ticket_code} · {task.lwi.title} · {task.lwi.skill_tag} · in “{task.sprint.title}”
          {task.transport === "gemini" ? " · planned by Gemini" : ""}
        </p>
      )}
      {taskError && <p className="mt-2 text-xs text-rose-700">{taskError}</p>}
      {quizOpen && <QuizDrawer key={message.id} messageId={message.id} persona={persona} onPassed={onUpdated} />}

      <div className="mt-4 rounded-2xl border border-line px-4 py-3">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">How it reads</p>
        <p className="mt-1 text-sm leading-6 text-slate-700">{message.sentiment_reason}</p>
      </div>
      <div className="mt-6 flex items-center justify-between gap-3">
        <button onClick={onPrevious} disabled={position === 1} className="inline-flex items-center gap-1 rounded-full border border-line px-3 py-1.5 text-sm disabled:opacity-40">
          <ChevronLeft size={14} /> Previous
        </button>
        {safeHref(message.url) ? (
          <a href={safeHref(message.url)} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-sm font-semibold text-brand">
            {message.sample ? "Open reference" : "Read the original"} <ExternalLink size={14} />
          </a>
        ) : (
          <span className="text-sm text-slate-400">Original link unavailable</span>
        )}
        <button onClick={onNext} disabled={position === total} className="inline-flex items-center gap-1 rounded-full bg-ink px-3 py-1.5 text-sm text-white disabled:opacity-40">
          Next <ChevronRight size={14} />
        </button>
      </div>
    </article>
  );
}

function QuizDrawer({ messageId, persona, onPassed }: { messageId: number; persona: Persona; onPassed: () => Promise<void> }) {
  const [card, setCard] = useState<StoryExplainer | null>(null);
  const [choice, setChoice] = useState<number | null>(null);
  const [result, setResult] = useState<QuizResult | null>(null);
  const [error, setError] = useState("");
  const [checking, setChecking] = useState(false);

  useEffect(() => {
    let ignore = false;
    api<StoryExplainer>(`/api/v1/signals/messages/${messageId}/explain`, persona, { method: "POST" })
      .then((data) => {
        if (!ignore) setCard(data);
      })
      .catch((reason: Error) => {
        if (!ignore) setError(reason.message);
      });
    return () => {
      ignore = true;
    };
  }, [messageId, persona]);

  async function check() {
    if (choice === null) return;
    setChecking(true);
    setError("");
    try {
      const answer = await api<QuizResult>(`/api/v1/signals/messages/${messageId}/quiz`, persona, {
        method: "POST",
        body: JSON.stringify({ choice }),
      });
      setResult(answer);
      if (answer.correct) await onPassed();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not check that answer");
    } finally {
      setChecking(false);
    }
  }

  if (error && !card) return <p className="mt-3 rounded-2xl bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</p>;
  if (!card) return <p className="mt-3 rounded-2xl border border-line px-4 py-3 text-sm text-slate-500">Writing a 2-minute explainer…</p>;

  const steps = [
    { label: "Core concept", text: card.concept },
    { label: "Real-world use", text: card.use_case },
  ];
  return (
    <section className="mt-3 rounded-3xl border border-ink/15 bg-[#FBF9F5] p-5">
      <div className="flex items-center justify-between gap-2">
        <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-copper">2-minute explainer</p>
        <span className="mono text-[10px] text-slate-400">{card.source === "gemini" ? "by Gemini" : "quick version"}</span>
      </div>
      <ol className="mt-3 space-y-3">
        {steps.map((step, position) => (
          <li key={step.label} className="flex gap-3">
            <span className="mono grid h-6 w-6 shrink-0 place-items-center rounded-full bg-ink text-[11px] text-white">{position + 1}</span>
            <div>
              <p className="text-xs font-semibold text-ink">{step.label}</p>
              <p className="text-sm leading-6 text-slate-700">{step.text}</p>
            </div>
          </li>
        ))}
        <li className="flex gap-3">
          <span className="mono grid h-6 w-6 shrink-0 place-items-center rounded-full bg-brand text-[11px] text-white">3</span>
          <fieldset className="min-w-0 flex-1" disabled={checking || Boolean(result?.correct)}>
            <legend className="text-xs font-semibold text-ink">Quick check</legend>
            <p className="text-sm leading-6 text-slate-700">{card.question}</p>
            <div className="mt-2 space-y-1.5">
              {card.options.map((option, position) => {
                const picked = choice === position;
                const marked = result && picked ? (result.correct ? "border-brand bg-[#E7F3EF]" : "border-rose-300 bg-rose-50") : picked ? "border-ink bg-white" : "border-line bg-white";
                return (
                  <label key={option} className={`flex cursor-pointer items-start gap-2 rounded-xl border px-3 py-2 text-sm transition ${marked}`}>
                    <input
                      type="radio"
                      name={`quiz-${messageId}`}
                      className="mt-1 accent-[#0E7C66]"
                      checked={picked}
                      onChange={() => {
                        setChoice(position);
                        setResult(null);
                      }}
                    />
                    <span>{option}</span>
                  </label>
                );
              })}
            </div>
          </fieldset>
        </li>
      </ol>
      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
        {result ? (
          <p className={`text-sm ${result.correct ? "text-brand" : "text-rose-700"}`}>
            {result.correct ? "Correct. " : "Not quite. Try another option. "}
            {result.correct && result.why}
            {result.correct && result.xp_awarded > 0 && result.skill && ` +${result.xp_awarded} XP to ${result.skill} (now ${result.skill_score}).`}
            {result.correct && result.already_passed && " XP was already counted for this story."}
            {result.correct &&
              result.skill_score === null &&
              (result.skill
                ? ` ${result.skill} is not on your skill graph yet. Finish a lab task on it to start that node.`
                : " This story has no linked skill, so no XP this time.")}
          </p>
        ) : (
          <p className="text-xs text-slate-500">{card.quiz_passed ? "You passed this one before. Answer again to review." : "A correct answer adds XP to the linked skill."}</p>
        )}
        {!result?.correct && (
          <button
            onClick={() => void check()}
            disabled={choice === null || checking}
            className="rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"
          >
            {checking ? "Checking…" : "Check answer"}
          </button>
        )}
      </div>
      {error && <p className="mt-2 text-xs text-rose-700">{error}</p>}
    </section>
  );
}

function SentimentTab({ analysis, onOpen }: { analysis: InterestAnalysis; onOpen: (id: number) => void }) {
  const [sort, setSort] = useState<SortKey>("sentiment_score");
  const [filter, setFilter] = useState("All");
  const rows = useMemo(
    () => analysis.rows.filter((row) => filter === "All" || row.sentiment === filter).sort((a, b) => b[sort] - a[sort]),
    [analysis.rows, filter, sort],
  );
  if (analysis.total === 0) return <Empty text="No stories yet, so there is no tone to show." />;
  const mood = analysis.average_sentiment > 15 ? "mostly upbeat" : analysis.average_sentiment < -15 ? "mostly worried" : "mixed";

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {SENTIMENT_ORDER.map((label) => {
          const count = analysis.sentiments[label] ?? 0;
          const share = Math.round((count / analysis.total) * 100);
          const tone = SENTIMENT_STYLE[label];
          return (
            <button
              key={label}
              onClick={() => setFilter(filter === label ? "All" : label)}
              className={`rounded-2xl border bg-white px-4 py-3 text-left transition hover:shadow-card ${filter === label ? "border-ink" : "border-line"}`}
            >
              <p className={`text-xs font-semibold ${tone.text}`}>{label}</p>
              <p className="mono mt-1 text-2xl font-semibold text-ink">{count}</p>
              <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-[#F3EEE6]">
                <div className="h-full rounded-full" style={{ width: `${share}%`, background: tone.bar }} />
              </div>
              <p className="mt-1 text-[11px] text-slate-400">{share}% of stories</p>
            </button>
          );
        })}
      </div>

      <div className="grid gap-4 rounded-3xl border border-line bg-white p-5 md:grid-cols-[280px_1fr]">
        <SentimentDonut counts={analysis.sentiments} caption="Tone of this topic" />
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">Overall</p>
          <p className="mt-1 text-lg text-ink">This topic reads {mood}.</p>
          <ScoreMeter value={analysis.average_sentiment} />
          <p className="mt-3 text-xs text-slate-500">
            Average tone {analysis.average_sentiment} on a scale from −100 to 100. Average match with your topic {analysis.average_relevance}.
          </p>
        </div>
      </div>

      <div className="overflow-hidden rounded-3xl border border-line bg-white">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line px-4 py-3">
          <p className="text-sm font-semibold text-ink">
            Every story {filter !== "All" && <span className="font-normal text-slate-500">· showing {filter.toLowerCase()} only</span>}
          </p>
          <div className="flex gap-1 rounded-full bg-[#F3EEE6] p-1 text-xs">
            {(["sentiment_score", "relevance_score"] as SortKey[]).map((key) => (
              <button key={key} onClick={() => setSort(key)} className={`rounded-full px-3 py-1 font-semibold ${sort === key ? "bg-white text-ink shadow-card" : "text-slate-500"}`}>
                {key === "sentiment_score" ? "Sort by tone" : "Sort by match"}
              </button>
            ))}
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="bg-[#FBF9F5] text-[11px] uppercase tracking-wide text-slate-400">
              <tr>
                <th className="px-4 py-2.5 font-semibold">Story</th>
                <th className="px-4 py-2.5 font-semibold">Topic</th>
                <th className="px-4 py-2.5 font-semibold">Tone</th>
                <th className="px-4 py-2.5 font-semibold">Score</th>
                <th className="px-4 py-2.5 font-semibold">Match</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => {
                const tone = SENTIMENT_STYLE[row.sentiment] ?? SENTIMENT_STYLE.Neutral;
                return (
                  <tr key={row.id} onClick={() => onOpen(row.id)} className="cursor-pointer border-t border-line transition hover:bg-[#FBF9F5]">
                    <td className="px-4 py-3">
                      <p className={`leading-5 text-ink ${row.is_read ? "" : "font-semibold"}`}>{row.title}</p>
                      <p className="text-[11px] text-slate-400">{row.source}</p>
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-600">{row.topic}</td>
                    <td className="px-4 py-3">
                      <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${tone.wash} ${tone.text}`}>{row.sentiment}</span>
                    </td>
                    <td className="px-4 py-3">
                      <ScoreMeter value={row.sentiment_score} compact />
                    </td>
                    <td className="mono px-4 py-3 text-xs text-slate-600">{row.relevance_score}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function TopicsTab({ analysis, onOpen }: { analysis: InterestAnalysis; onOpen: (id: number) => void }) {
  if (analysis.total === 0) return <Empty text="No stories yet, so there is nothing to group." />;
  const titles = new Map(analysis.rows.map((row) => [row.id, row]));
  return (
    <div className="space-y-4">
      <div className="rounded-3xl border border-line bg-white p-5">
        <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">How the stories group</p>
        <p className="mt-1 text-sm text-slate-600">
          {analysis.clusters.length} {analysis.clusters.length === 1 ? "group" : "groups"} inside this interest. Each bar shows how many stories it holds and their tone.
        </p>
        <div className="mt-4 space-y-3">
          {analysis.clusters.map((cluster) => (
            <ClusterRow key={cluster.label} cluster={cluster} total={analysis.total} />
          ))}
        </div>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        {analysis.clusters.map((cluster) => {
          const tone = SENTIMENT_STYLE[cluster.dominant_sentiment] ?? SENTIMENT_STYLE.Neutral;
          return (
            <article key={cluster.label} className="rounded-3xl border border-line bg-white p-5">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="text-lg leading-tight text-ink">{cluster.label}</h3>
                  <p className="mt-0.5 text-xs text-slate-500">
                    {cluster.count} {cluster.count === 1 ? "story" : "stories"} · average tone {cluster.average_sentiment}
                  </p>
                </div>
                <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${tone.wash} ${tone.text}`}>{cluster.dominant_sentiment}</span>
              </div>
              <div className="mt-3 flex flex-wrap gap-1.5">
                {cluster.keywords.map((word) => (
                  <span key={word} className="rounded-full bg-[#F3EEE6] px-2 py-0.5 text-[11px] text-slate-600">
                    {word}
                  </span>
                ))}
              </div>
              <ul className="mt-4 divide-y divide-line">
                {cluster.story_ids.map((id) => {
                  const row = titles.get(id);
                  if (!row) return null;
                  const rowTone = SENTIMENT_STYLE[row.sentiment] ?? SENTIMENT_STYLE.Neutral;
                  return (
                    <li key={id}>
                      <button onClick={() => onOpen(id)} className="flex w-full items-start gap-2 py-2.5 text-left text-sm hover:text-brand">
                        <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full" style={{ background: rowTone.bar }} />
                        <span className="leading-5">{row.title}</span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            </article>
          );
        })}
      </div>
    </div>
  );
}

function ClusterRow({ cluster, total }: { cluster: InterestCluster; total: number }) {
  return (
    <div>
      <div className="mb-1 flex items-baseline justify-between gap-2 text-sm">
        <span className="font-medium text-ink">{cluster.label}</span>
        <span className="mono text-[11px] text-slate-400">
          {cluster.count} · {Math.round((cluster.count / total) * 100)}%
        </span>
      </div>
      <div className="flex h-3 overflow-hidden rounded-full bg-[#F3EEE6]" style={{ width: `${Math.max(14, (cluster.count / total) * 100)}%` }}>
        {SENTIMENT_ORDER.map((label) => {
          const count = cluster.sentiments[label] ?? 0;
          if (!count) return null;
          return <div key={label} title={`${label} ${count}`} style={{ width: `${(count / cluster.count) * 100}%`, background: SENTIMENT_STYLE[label].bar }} />;
        })}
      </div>
    </div>
  );
}

function ScoreMeter({ value, compact = false }: { value: number; compact?: boolean }) {
  const clamped = Math.max(-100, Math.min(100, value));
  const color = clamped > 15 ? SENTIMENT_STYLE.Positive.bar : clamped < -15 ? SENTIMENT_STYLE.Critical.bar : SENTIMENT_STYLE.Watchful.bar;
  const width = Math.abs(clamped) / 2;
  return (
    <div className={`flex items-center gap-2 ${compact ? "" : "mt-3"}`}>
      <div className={`relative overflow-hidden rounded-full bg-[#F3EEE6] ${compact ? "h-1.5 w-24" : "h-2.5 w-full"}`}>
        <div className="absolute inset-y-0 left-1/2 w-px bg-slate-300" />
        <div className="absolute inset-y-0 rounded-full" style={{ background: color, width: `${width}%`, left: clamped >= 0 ? "50%" : `${50 - width}%` }} />
      </div>
      <span className="mono w-9 text-right text-[11px] text-slate-500">{clamped}</span>
    </div>
  );
}

function Empty({ text }: { text: string }) {
  return <p className="rounded-3xl border border-dashed border-line bg-white px-5 py-12 text-center text-sm text-slate-500">{text}</p>;
}
