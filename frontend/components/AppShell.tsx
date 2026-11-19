"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";

import { KanbanBoard } from "@/components/KanbanBoard";
import { ReasoningPill } from "@/components/ReasoningPill";
import { Sidebar } from "@/components/Sidebar";
import { TicketDrawer } from "@/components/TicketDrawer";
import { TopBar } from "@/components/TopBar";
import { ApiError, api } from "@/lib/api";
import { BOARD_POLL_MS, SAMPLE_SYLLABUS, guardLine } from "@/lib/format";

const DashboardView = dynamic(() => import("@/components/DashboardView").then((m) => m.DashboardView), {
  loading: () => <PanelLoading label="Dashboard" />,
});
const FacultyView = dynamic(() => import("@/components/FacultyView").then((m) => m.FacultyView), {
  loading: () => <PanelLoading label="Faculty radar" />,
});
const PlacementView = dynamic(() => import("@/components/PlacementView").then((m) => m.PlacementView), {
  loading: () => <PanelLoading label="Placement prep" />,
});
const SecurityView = dynamic(() => import("@/components/SecurityView").then((m) => m.SecurityView), {
  loading: () => <PanelLoading label="Security posture" />,
});
const SignalsView = dynamic(() => import("@/components/SignalsView").then((m) => m.SignalsView), {
  loading: () => <PanelLoading label="Signals" />,
});
const SkillView = dynamic(() => import("@/components/SkillView").then((m) => m.SkillView), {
  loading: () => <PanelLoading label="Skill graph" />,
});
const TpoView = dynamic(() => import("@/components/TpoView").then((m) => m.TpoView), {
  loading: () => <PanelLoading label="Readiness" />,
});

function PanelLoading({ label }: { label: string }) {
  return (
    <div className="grid min-h-[40vh] place-items-center p-8" role="status" aria-live="polite">
      <p className="text-sm text-slate-500">Loading {label}…</p>
    </div>
  );
}
import type {
  AIAction,
  AIJob,
  Bootstrap,
  CohortHealth,
  Dashboard,
  GenerateResponse,
  JDResponse,
  LWI,
  LWIDetail,
  Persona,
  Posture,
  ReadinessMatrix,
  SessionUser,
  SkillGraph,
  Status,
  View,
} from "@/lib/types";

const VIEW_FOR: Record<Persona, View> = {
  student: "dashboard",
  faculty: "faculty",
  tpo: "tpo",
};

export function AppShell({
  user,
  onSignOut,
  onSwitched,
}: {
  user: SessionUser;
  onSignOut: () => void;
  onSwitched: (next: SessionUser) => void;
}) {
  const persona: Persona = user.persona;
  const [view, setView] = useState<View>(VIEW_FOR[user.persona]);
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [boot, setBoot] = useState<Bootstrap | null>(null);
  const [bootError, setBootError] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);
  const [boardKey, setBoardKey] = useState(0);
  const [sprintId, setSprintId] = useState<number | null>(null);
  const [items, setItems] = useState<LWI[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [detail, setDetail] = useState<LWIDetail | null>(null);
  const [action, setAction] = useState<AIAction | null>(null);
  const [skills, setSkills] = useState<SkillGraph | null>(null);
  const [cohort, setCohort] = useState<CohortHealth | null>(null);
  const [readiness, setReadiness] = useState<ReadinessMatrix | null>(null);
  const [query, setQuery] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);
  const [compose, setCompose] = useState(false);
  const [toast, setToast] = useState("");
  const [job, setJob] = useState<AIJob | null>(null);
  const [busy, setBusy] = useState(false);
  const [liveLabel, setLiveLabel] = useState("Watching the campus desk");

  useEffect(() => {
    let ignore = false;
    setBootError("");
    api<Bootstrap>("/api/v1/bootstrap", persona)
      .then((data) => {
        if (ignore) return;
        setBoot(data);
        setSprintId((current) => (current && data.sprints.some((sprint) => sprint.id === current) ? current : data.sprints[0]?.id ?? null));
      })
      .catch((reason: Error) => {
        if (!ignore) setBootError(reason.message || "CampusFlow API is not reachable.");
      });
    return () => {
      ignore = true;
    };
  }, [persona, refreshKey]);

  useEffect(() => {
    if (persona !== "student" || !sprintId) return;
    let ignore = false;
    api<LWI[]>(`/api/v1/sprints/${sprintId}/board`, persona)
      .then((data) => {
        if (!ignore) setItems(data);
      })
      .catch((reason: Error) => setToast(reason.message));
    return () => {
      ignore = true;
    };
  }, [persona, sprintId, boardKey]);

  useEffect(() => {
    if (!selectedId || persona !== "student") {
      setDetail(null);
      return;
    }
    let ignore = false;
    api<LWIDetail>(`/api/v1/lwi/${selectedId}`, persona)
      .then((data) => {
        if (!ignore) setDetail(data);
      })
      .catch(() => {
        if (!ignore) setSelectedId(null);
      });
    return () => {
      ignore = true;
    };
  }, [selectedId, persona, boardKey]);

  useEffect(() => {
    if (view !== "skills" || persona !== "student" || !boot) return;
    let ignore = false;
    api<SkillGraph>(`/api/v1/students/${boot.actor.id}/skill-graph`, persona)
      .then((data) => {
        if (!ignore) setSkills(data);
      })
      .catch((reason: Error) => setToast(reason.message));
    return () => {
      ignore = true;
    };
  }, [view, persona, boot, boardKey]);

  useEffect(() => {
    if (view !== "dashboard" || persona !== "student") return;
    let ignore = false;
    api<Dashboard>("/api/v1/dashboard", persona)
      .then((data) => {
        if (!ignore) setDashboard(data);
      })
      .catch((reason: Error) => {
        if (!ignore) setToast(reason.message);
      });
    return () => {
      ignore = true;
    };
  }, [view, persona, refreshKey]);

  useEffect(() => {
    if (view !== "faculty") return;
    let ignore = false;
    api<CohortHealth>("/api/v1/faculty/cohort-health", persona)
      .then((data) => {
        if (!ignore) setCohort(data);
      })
      .catch((reason: Error) => setToast(reason.message));
    return () => {
      ignore = true;
    };
  }, [view, refreshKey]);

  useEffect(() => {
    if (view !== "tpo") return;
    let ignore = false;
    api<ReadinessMatrix>("/api/v1/tpo/readiness", persona)
      .then((data) => {
        if (!ignore) setReadiness(data);
      })
      .catch((reason: Error) => setToast(reason.message));
    return () => {
      ignore = true;
    };
  }, [view, persona, refreshKey]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      if (document.visibilityState !== "visible") return;
      setRefreshKey((value) => value + 1);
      if (view === "board" || view === "skills" || selectedId !== null) {
        setBoardKey((value) => value + 1);
      }
    }, BOARD_POLL_MS);
    return () => window.clearInterval(timer);
  }, [view, selectedId]);

  useEffect(() => {
    let ignore = false;
    api<Posture>("/api/v1/security/posture", persona)
      .then((data) => {
        if (ignore) return;
        const latest = data.recent_audit[0];
        setLiveLabel(latest ? `${latest.actor_role} · ${latest.action} · ${latest.detail}` : "No campus activity yet");
      })
      .catch(() => {
        if (!ignore) setLiveLabel("Activity feed will reconnect");
      });
    return () => {
      ignore = true;
    };
  }, [persona, refreshKey]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setSelectedId(null);
        setCompose(false);
        setMenuOpen(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(""), 3200);
    return () => window.clearTimeout(timer);
  }, [toast]);

  useEffect(() => {
    if (!job || job.done) return;
    const timer = window.setInterval(() => {
      setJob((current) => {
        if (!current || current.done || current.id !== job.id) return current;
        return { ...current, active: Math.min(current.steps.length - 1, current.active + 1) };
      });
    }, 700);
    return () => window.clearInterval(timer);
  }, [job]);

  async function runAI<T>(title: string, steps: string[], path: string, body: unknown): Promise<T | null> {
    const id = Date.now();
    setBusy(true);
    setJob({ id, title, steps, active: 0, done: false, foot: "" });
    try {
      const result = await api<T>(path, persona, { method: "POST", body: JSON.stringify(body) });
      const guard = (result as { guard?: AIAction["guard"] }).guard;
      setJob((current) => (current && current.id === id ? { ...current, done: true, active: steps.length, foot: guardLine(guard) } : current));
      window.setTimeout(() => setJob((current) => (current?.id === id ? null : current)), 1400);
      return result;
    } catch (reason) {
      setJob((current) => (current?.id === id ? null : current));
      setToast(reason instanceof Error ? reason.message : "The request failed");
      return null;
    } finally {
      setBusy(false);
    }
  }

  async function move(id: number, status: Status) {
    const item = items.find((entry) => entry.id === id);
    if (!item || item.status === status) return;
    try {
      await api(`/api/v1/lwi/${id}/status`, persona, { method: "PATCH", body: JSON.stringify({ status }) });
      setBoardKey((value) => value + 1);
      setRefreshKey((value) => value + 1);
    } catch (reason) {
      setToast(reason instanceof ApiError ? reason.message : "Could not move that ticket");
    }
  }

  if (!boot && !bootError) {
    return (
      <div className="grid h-screen place-items-center">
        <div className="text-center">
          <div className="mx-auto grid h-10 w-10 grid-cols-2 gap-0.5 rounded-xl bg-brand p-2">
            <span className="rounded-[2px] bg-white" />
            <span className="rounded-[2px] bg-white/70" />
            <span className="rounded-[2px] bg-white/70" />
            <span className="rounded-[2px] bg-white" />
          </div>
          <p className="mt-3 text-sm font-semibold">Opening CampusFlow</p>
        </div>
      </div>
    );
  }

  if (!boot) {
    return (
      <div className="grid h-screen place-items-center px-6">
        <div className="surface max-w-md p-6 text-center">
          <h1 className="text-lg font-semibold">API is not reachable</h1>
          <p className="mt-2 text-sm text-slate-600">{bootError}</p>
          <p className="mt-2 text-xs text-slate-500">Start the FastAPI server on port 8000, then retry.</p>
          <button onClick={() => setRefreshKey((value) => value + 1)} className="mt-4 rounded-full bg-brand px-4 py-2 text-sm font-semibold text-white">
            Retry
          </button>
        </div>
      </div>
    );
  }

  const sprint = boot.sprints.find((item) => item.id === sprintId);

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar
        persona={persona}
        view={view}
        sprints={boot.sprints}
        sprintId={sprintId}
        progress={boot.semester_progress}
        unread={boot.signal_unread}
        open={menuOpen}
        onView={setView}
        onSprint={(id) => {
          setSprintId(id);
          setSelectedId(null);
        }}
        onSecurity={() => setView("security")}
        onClose={() => setMenuOpen(false)}
      />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar
          user={user}
          boot={boot}
          query={query}
          liveLabel={liveLabel}
          onQuery={setQuery}
          onSignOut={onSignOut}
          onSwitched={onSwitched}
          onMenu={() => setMenuOpen(true)}
        />
        <div className="flex min-h-0 flex-1">
          <main id="main-content" className="min-w-0 flex-1">
            {view === "dashboard" && (
              <DashboardView
                data={dashboard}
                onNavigate={setView}
                onOpenSprint={(id) => {
                  setSprintId(id);
                  setSelectedId(null);
                  setView("board");
                }}
                onOpenTopics={() => setView("signals")}
              />
            )}
            {view === "board" && (
              <KanbanBoard
                sprint={sprint}
                items={items}
                query={query}
                onOpen={(id) => {
                  setAction(null);
                  setSelectedId(id);
                }}
                onMove={move}
                onGenerate={() => setCompose(true)}
                onCreate={async (payload) => {
                  if (!sprintId) return;
                  await api(`/api/v1/sprints/${sprintId}/tickets`, persona, {
                    method: "POST",
                    body: JSON.stringify(payload),
                  });
                  setBoardKey((value) => value + 1);
                  setRefreshKey((value) => value + 1);
                  setToast("Ticket saved to your backlog");
                }}
              />
            )}
            {view === "signals" && (
              <SignalsView
                persona={persona}
                onChanged={() => setRefreshKey((value) => value + 1)}
                onOpenSprint={(id) => {
                  setSprintId(id);
                  setRefreshKey((value) => value + 1);
                  setBoardKey((value) => value + 1);
                  setView("board");
                }}
              />
            )}
            {view === "skills" && <SkillView graph={skills} />}
            {view === "placement" && (
              <PlacementView
                busy={busy}
                onAnalyze={async (jobText) => {
                  const result = await runAI<JDResponse>(
                    "Placement copilot",
                    ["Reading the job description", "Matching the skill graph", "Injecting the prep sprint"],
                    "/api/v1/placement/analyze-jd",
                    { job_description: jobText },
                  );
                  if (!result) return null;
                  setSprintId(result.sprint.id);
                  setRefreshKey((value) => value + 1);
                  setBoardKey((value) => value + 1);
                  return { result, guard: result.guard };
                }}
                onOpenSprint={(id) => {
                  setSprintId(id);
                  setView("board");
                }}
              />
            )}
            {view === "faculty" && <FacultyView cohort={cohort} persona={persona} />}
            {view === "tpo" && <TpoView matrix={readiness} persona={persona} />}
            {view === "security" && <SecurityView persona={persona} />}
          </main>
          {view === "board" && detail && (
            <div className="fixed inset-0 z-40 h-full bg-white md:static md:z-auto">
              <TicketDrawer
                detail={detail}
                result={action}
                busy={busy}
                onClose={() => setSelectedId(null)}
                onMove={move}
                onUnblock={async (message) => {
                  const result = await runAI<AIAction>(
                    "Socratic unblocker",
                    ["Diagnosing the gap", "Applying the Socratic guardrail", "Scheduling remediation"],
                    `/api/v1/lwi/${detail.id}/unblock`,
                    { message },
                  );
                  if (!result) return;
                  setAction(result);
                  setBoardKey((value) => value + 1);
                  setRefreshKey((value) => value + 1);
                }}
                onEvaluate={async (submission) => {
                  const result = await runAI<AIAction>(
                    "Rubric auditor",
                    ["Parsing rubric", "Checking edge cases", "Updating skill graph"],
                    `/api/v1/lwi/${detail.id}/evaluate`,
                    { submission },
                  );
                  if (!result) return;
                  setAction(result);
                  setBoardKey((value) => value + 1);
                  setRefreshKey((value) => value + 1);
                }}
              />
            </div>
          )}
        </div>
      </div>
      {compose && (
        <ComposeSprint
          busy={busy}
          onClose={() => setCompose(false)}
          onCreate={async (payload) => {
            const result = await runAI<GenerateResponse>(
              "Syllabus to sprint",
              ["Parsing syllabus", "Mapping CO–PO", "Building Kanban"],
              "/api/v1/sprints/generate",
              payload,
            );
            if (!result) return;
            setCompose(false);
            setSprintId(result.sprint.id);
            setView("board");
            setRefreshKey((value) => value + 1);
            setBoardKey((value) => value + 1);
            if (result.guard.injection_flags.length || result.guard.redactions) {
              setToast(guardLine(result.guard));
            }
          }}
        />
      )}
      {job && <ReasoningPill job={job} />}
      {toast && (
        <div role="status" aria-live="polite" className={`fixed left-1/2 z-50 -translate-x-1/2 rounded-full bg-ink px-4 py-2 text-sm text-white shadow-lift ${job ? "bottom-28" : "bottom-5"}`}>
          {toast}
        </div>
      )}
    </div>
  );
}

function ComposeSprint({
  busy,
  onClose,
  onCreate,
}: {
  busy: boolean;
  onClose: () => void;
  onCreate: (payload: { title: string; course_code: string; duration_weeks: number; syllabus: string }) => Promise<void>;
}) {
  const [title, setTitle] = useState("Computer Networks");
  const [courseCode, setCourseCode] = useState("CS303");
  const [weeks, setWeeks] = useState(4);
  const [syllabus, setSyllabus] = useState(SAMPLE_SYLLABUS);

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-slate-900/40 p-4">
      <form
        className="surface w-full max-w-xl p-5"
        onSubmit={(event) => {
          event.preventDefault();
          void onCreate({ title, course_code: courseCode, duration_weeks: weeks, syllabus });
        }}
      >
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-lg font-semibold">Syllabus to sprint</h2>
            <p className="text-sm text-slate-500">Units become epics. Advanced topics stay locked until the foundation is mastered.</p>
          </div>
          <button type="button" onClick={onClose} className="rounded-lg border border-line p-1.5" aria-label="Close">
            ×
          </button>
        </div>
        <div className="mt-4 grid gap-3 sm:grid-cols-[1fr_120px_90px]">
          <label className="text-xs text-slate-500">
            Title
            <input className="field mt-1" value={title} onChange={(event) => setTitle(event.target.value)} />
          </label>
          <label className="text-xs text-slate-500">
            Code
            <input className="field mt-1" value={courseCode} onChange={(event) => setCourseCode(event.target.value)} />
          </label>
          <label className="text-xs text-slate-500">
            Weeks
            <input className="field mt-1" type="number" min={1} max={18} value={weeks} onChange={(event) => setWeeks(Number(event.target.value))} />
          </label>
        </div>
        <label className="mt-3 block text-xs text-slate-500">
          Syllabus or lab brief
          <textarea className="field mt-1 min-h-40 text-sm" value={syllabus} onChange={(event) => setSyllabus(event.target.value)} />
        </label>
        <div className="mt-4 flex justify-end gap-2">
          <button type="button" onClick={() => setSyllabus(SAMPLE_SYLLABUS)} className="rounded-full border border-line px-4 py-2 text-sm">
            Sample syllabus
          </button>
          <button disabled={busy} className="rounded-full bg-brand px-4 py-2 text-sm font-semibold text-white disabled:opacity-60">
            Build Kanban
          </button>
        </div>
      </form>
    </div>
  );
}
