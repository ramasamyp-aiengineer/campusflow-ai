import { Lock, Plus } from "lucide-react";
import { useRef, useState } from "react";

import { COLUMNS } from "@/lib/format";
import type { LWI, Sprint, Status } from "@/lib/types";

export function KanbanBoard({
  sprint,
  items,
  query,
  onOpen,
  onMove,
  onGenerate,
  onCreate,
}: {
  sprint: Sprint | undefined;
  items: LWI[];
  query: string;
  onOpen: (id: number) => void;
  onMove: (id: number, status: Status) => void;
  onGenerate: () => void;
  onCreate: (payload: { title: string; description: string; skill_tag: string; story_points: number; type: string }) => Promise<void>;
}) {
  const needle = query.trim().toLowerCase();
  const visible = items.filter((item) => {
    if (!needle) return true;
    return [item.title, item.ticket_code, item.skill_tag, item.co_tag, item.type].join(" ").toLowerCase().includes(needle);
  });
  const blocked = items.find((item) => item.blocked);
  const [adding, setAdding] = useState(false);

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex flex-wrap items-end justify-between gap-3 px-5 pb-3 pt-4">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="mono rounded-md bg-[#E7F3EF] px-2 py-0.5 text-xs font-medium text-brand">
              {sprint?.course_code ?? "Sprint"}
            </span>
            {sprint?.kind === "PLACEMENT" && <span className="rounded-md bg-emerald-50 px-2 py-0.5 text-[11px] font-medium text-emerald-700">14-day prep</span>}
            {sprint?.kind === "GENERATED" && <span className="rounded-md bg-amber-50 px-2 py-0.5 text-[11px] font-medium text-amber-700">Generated</span>}
            <span className="text-xs text-slate-500">
              {sprint ? `${sprint.start_date} → ${sprint.end_date}` : "Select a course"}
            </span>
          </div>
          <h1 className="mt-1 text-xl font-semibold tracking-tight text-ink">{sprint?.title ?? "No sprint yet"}</h1>
          <p className="mt-1 max-w-xl text-sm text-slate-500">Move work only when the prerequisite is mastered. AI Review is the gate before a ticket can count as evidence.</p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {sprint?.co_po_tags.map((tag) => (
              <span key={tag} className="mono rounded-full border border-line px-2 py-0.5 text-[10px] text-slate-500">
                {tag}
              </span>
            ))}
          </div>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setAdding((open) => !open)} className="inline-flex items-center gap-1.5 rounded-full bg-brand px-4 py-2 text-sm font-semibold text-white">
            <Plus size={14} /> Add ticket
          </button>
          <button onClick={onGenerate} className="rounded-full border border-line bg-white px-4 py-2 text-sm font-semibold">
            Generate from syllabus
          </button>
        </div>
      </div>
      {adding && <TicketComposer onClose={() => setAdding(false)} onCreate={onCreate} />}
      {blocked && (
        <div className="mx-5 mb-3 flex items-center gap-2 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
          <Lock size={14} />
          <span>
            <span className="mono">{blocked.ticket_code}</span> is locked. {blocked.block_reason}
          </span>
        </div>
      )}
      <div className="grid min-h-0 flex-1 grid-cols-1 gap-3 overflow-auto px-5 pb-5 md:grid-cols-2 xl:grid-cols-4">
        {COLUMNS.map((column) => {
          const cards = visible.filter((item) => item.status === column.id);
          const points = cards.reduce((sum, item) => sum + item.story_points, 0);
          return (
            <section
              key={column.id}
              className="flex min-h-[280px] flex-col rounded-2xl bg-[#EFE8DC]/90 p-2"
              onDragOver={(event) => event.preventDefault()}
              onDrop={(event) => {
                event.preventDefault();
                const id = Number(event.dataTransfer.getData("text/plain"));
                if (id) onMove(id, column.id);
              }}
            >
              <header className="flex items-center justify-between px-2 py-1.5">
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full" style={{ background: column.bar }} />
                  <h2 className="text-sm font-semibold">{column.label}</h2>
                  <span className="mono text-[11px] text-slate-400">{cards.length}</span>
                </div>
                <span className="mono text-[11px] text-slate-400">{points} SP</span>
              </header>
              <div className="flex flex-1 flex-col gap-2">
                {cards.map((item) => (
                  <TicketCard key={item.id} item={item} onOpen={onOpen} />
                ))}
                {cards.length === 0 && <p className="px-2 py-6 text-center text-xs text-slate-400">Drop a ticket here</p>}
              </div>
            </section>
          );
        })}
      </div>
    </div>
  );
}

function TicketCard({ item, onOpen }: { item: LWI; onOpen: (id: number) => void }) {
  const dragged = useRef(false);
  const accent = item.blocked ? "#BE123C" : item.status === "MASTERED" ? "#0F7A4A" : item.status === "AI_REVIEW" ? "#C47B12" : item.status === "IN_PROGRESS" ? "#0E7C66" : "#D6CFC4";
  return (
    <article
      draggable
      onDragStart={(event) => {
        dragged.current = true;
        event.dataTransfer.setData("text/plain", String(item.id));
        event.dataTransfer.effectAllowed = "move";
      }}
      onDragEnd={() => {
        window.setTimeout(() => {
          dragged.current = false;
        }, 0);
      }}
      onClick={() => {
        if (dragged.current) return;
        onOpen(item.id);
      }}
      className="cursor-pointer rounded-xl border border-line bg-white p-3 shadow-card transition hover:-translate-y-0.5 hover:shadow-lift"
      style={{ borderLeft: `3px solid ${accent}` }}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="mono text-[11px] text-slate-500">{item.ticket_code}</span>
        <span className="mono rounded-md bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-600">{item.story_points} SP</span>
      </div>
      <h3 className="mt-1.5 text-sm font-semibold leading-5 text-ink">{item.title}</h3>
      <div className="mt-2 flex flex-wrap items-center gap-1.5">
        <span className="rounded-md bg-slate-100 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-slate-500">{item.type}</span>
        <span className="mono rounded-md bg-[#E7F3EF] px-1.5 py-0.5 text-[10px] text-brand">{item.co_tag}</span>
        <span className="rounded-md bg-emerald-50 px-1.5 py-0.5 text-[10px] font-medium text-emerald-700">{item.skill_tag}</span>
        {item.blocked && (
          <span className="inline-flex items-center gap-1 rounded-md bg-rose-50 px-1.5 py-0.5 text-[10px] font-medium text-rose-700">
            <Lock size={10} /> Blocked
          </span>
        )}
      </div>
    </article>
  );
}

function TicketComposer({
  onClose,
  onCreate,
}: {
  onClose: () => void;
  onCreate: (payload: { title: string; description: string; skill_tag: string; story_points: number; type: string }) => Promise<void>;
}) {
  const [title, setTitle] = useState("");
  const [skill, setSkill] = useState("SQL");
  const [points, setPoints] = useState(3);
  const [kind, setKind] = useState("TASK");
  const [description, setDescription] = useState("");
  const [saving, setSaving] = useState(false);

  return (
    <form
      className="mx-5 mb-3 grid gap-3 rounded-2xl border border-line bg-white p-4 shadow-card md:grid-cols-[1.4fr_0.7fr_90px_120px]"
      onSubmit={async (event) => {
        event.preventDefault();
        setSaving(true);
        try {
          await onCreate({ title, description, skill_tag: skill, story_points: points, type: kind });
          setTitle("");
          setDescription("");
          onClose();
        } finally {
          setSaving(false);
        }
      }}
    >
      <label className="text-xs text-slate-500 md:col-span-4">
        Your ticket
        <input className="field mt-1" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="What you will actually do" required minLength={3} />
      </label>
      <label className="text-xs text-slate-500">
        Skill
        <input className="field mt-1" value={skill} onChange={(event) => setSkill(event.target.value)} required />
      </label>
      <label className="text-xs text-slate-500">
        Points
        <input className="field mt-1" type="number" min={1} max={13} value={points} onChange={(event) => setPoints(Number(event.target.value))} />
      </label>
      <label className="text-xs text-slate-500">
        Type
        <select className="field mt-1" value={kind} onChange={(event) => setKind(event.target.value)}>
          <option>TASK</option>
          <option>EPIC</option>
          <option>SUBTASK</option>
        </select>
      </label>
      <div className="flex items-end justify-end gap-2">
        <button type="button" onClick={onClose} className="rounded-full border border-line px-3 py-2 text-sm">
          Cancel
        </button>
        <button disabled={saving} className="rounded-full bg-ink px-3 py-2 text-sm font-semibold text-white disabled:opacity-60">
          Save to backlog
        </button>
      </div>
      <label className="text-xs text-slate-500 md:col-span-4">
        Notes
        <textarea className="field mt-1 min-h-16 text-sm" value={description} onChange={(event) => setDescription(event.target.value)} placeholder="What done looks like, in your words" />
      </label>
    </form>
  );
}
