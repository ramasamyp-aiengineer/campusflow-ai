import { AlertTriangle, Briefcase, Gauge, LayoutGrid, Rss, ShieldCheck, Users, Waypoints } from "lucide-react";

import { Ring } from "@/components/Ring";
import type { Persona, Sprint, View } from "@/lib/types";

const NAV: Record<Persona, { id: View; label: string; hint: string; icon: typeof LayoutGrid }[]> = {
  student: [
    { id: "dashboard", label: "Dashboard", hint: "Your record", icon: Gauge },
    { id: "signals", label: "My interests", hint: "Topics and RSS", icon: Rss },
    { id: "board", label: "Sprint board", hint: "Your tickets", icon: LayoutGrid },
    { id: "skills", label: "Skill graph", hint: "Verified only", icon: Waypoints },
    { id: "placement", label: "Placement copilot", hint: "JD to sprint", icon: Briefcase },
  ],
  faculty: [{ id: "faculty", label: "Cohort radar", hint: "Early warning", icon: AlertTriangle }],
  tpo: [{ id: "tpo", label: "Readiness matrix", hint: "Evidence first", icon: Users }],
};

export function Sidebar({
  persona,
  view,
  sprints,
  sprintId,
  progress,
  unread,
  open,
  onView,
  onSprint,
  onSecurity,
  onClose,
}: {
  persona: Persona;
  view: View;
  sprints: Sprint[];
  sprintId: number | null;
  progress: number;
  unread: number;
  open: boolean;
  onView: (view: View) => void;
  onSprint: (id: number) => void;
  onSecurity: () => void;
  onClose: () => void;
}) {
  return (
    <>
      {open && <button className="fixed inset-0 z-20 bg-[#241C16]/45 md:hidden" onClick={onClose} aria-label="Close menu" />}
      <aside
        className={`fixed inset-y-0 left-0 z-30 flex w-[272px] flex-col bg-ink text-[#F6E7D4] transition-transform md:static md:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="px-4 pb-4 pt-5">
          <div className="flex items-center gap-3">
            <div className="grid h-9 w-9 place-items-center rounded-2xl bg-[#F4E6CF] text-sm font-semibold text-ink">CF</div>
            <div>
              <p className="display text-[1.15rem] leading-none text-[#FFF8EF]">CampusFlow</p>
              <p className="mt-1 text-[11px] tracking-wide text-[#D7B89A]">Agile campus OS</p>
            </div>
          </div>
        </div>

        <nav className="space-y-1 px-3">
          {NAV[persona].map((item) => {
            const Icon = item.icon;
            const active = view === item.id;
            return (
              <button
                key={item.id}
                onClick={() => {
                  onView(item.id);
                  onClose();
                }}
                className={`group flex w-full items-center gap-2.5 rounded-2xl px-2.5 py-2 text-left transition ${
                  active ? "bg-[#F4E6CF] text-ink shadow-card" : "text-[#E7D3C0] hover:bg-white/8"
                }`}
              >
                <span className={`grid h-8 w-8 place-items-center rounded-xl ${active ? "bg-ink text-[#F4E6CF]" : "bg-white/8 text-[#F0C9A0]"}`}>
                  <Icon size={15} />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block text-sm font-semibold leading-4">{item.label}</span>
                  <span className={`block text-[11px] ${active ? "text-[#8A6244]" : "text-[#CDB39A]"}`}>{item.hint}</span>
                </span>
                {item.id === "signals" && unread > 0 && (
                  <span className={`mono rounded-full px-1.5 py-0.5 text-[10px] font-semibold ${active ? "bg-copper text-white" : "bg-[#C46B2C] text-white"}`}>
                    {unread}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {persona === "student" && (
          <div className="mt-5 min-h-0 flex-1 overflow-auto px-3">
            <p className="px-2 pb-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-[#C46B2C]">Courses</p>
            <div className="space-y-1">
              {sprints.map((sprint) => {
                const active = sprint.id === sprintId;
                return (
                  <button
                    key={sprint.id}
                    onClick={() => {
                      onSprint(sprint.id);
                      onView("board");
                      onClose();
                    }}
                    className={`w-full rounded-2xl px-3 py-2 text-left transition ${
                      active ? "bg-white/10 text-white" : "text-[#E7D3C0] hover:bg-white/6"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="mono text-[11px] text-[#F0C9A0]">{sprint.course_code}</span>
                      <span className="mono text-[10px] text-[#D7B89A]">{sprint.progress_percent}%</span>
                    </div>
                    <p className="truncate text-xs">{sprint.title}</p>
                    <div className="mt-1.5 h-1 overflow-hidden rounded-full bg-white/10">
                      <div className="h-full rounded-full bg-[#E7B15A]" style={{ width: `${sprint.progress_percent}%` }} />
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        <div className="mt-auto space-y-3 p-3">
          <div className="flex items-center gap-3 rounded-2xl bg-[#F4E6CF] px-3 py-2.5 text-ink">
            <Ring value={progress} size={46} color="#C46B2C" track="#E7D3BC" text="#241C16" />
            <div>
              <p className="text-xs font-semibold">Semester</p>
              <p className="text-[11px] text-[#8A6244]">Story points mastered</p>
            </div>
          </div>
          <button
            onClick={() => {
              onSecurity();
              onClose();
            }}
            className={`flex w-full items-center gap-2 rounded-2xl px-2.5 py-2 text-left text-sm transition ${
              view === "security" ? "bg-[#F4E6CF] text-ink" : "text-[#E7D3C0] hover:bg-white/8"
            }`}
          >
            <ShieldCheck size={16} />
            Security posture
          </button>
        </div>
      </aside>
    </>
  );
}
