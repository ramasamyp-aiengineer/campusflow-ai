import { Radar } from "@/components/Radar";
import { Ring } from "@/components/Ring";
import { scoreColor } from "@/lib/format";
import type { SkillGraph } from "@/lib/types";

export function SkillView({ graph }: { graph: SkillGraph | null }) {
  if (!graph) return <Empty label="Loading the skill graph…" />;
  return (
    <div className="h-full overflow-auto px-5 py-5">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="mono text-xs text-slate-500">{graph.anon_token}</p>
          <h1 className="text-xl font-semibold">Skill graph</h1>
          <p className="text-sm text-slate-500">{graph.student_name} · a score is recorded evidence. New mastery is added when faculty co-sign an AI review.</p>
        </div>
        <div className="flex items-center gap-3 rounded-2xl border border-line bg-white px-3 py-2">
          <Ring value={graph.verified_skill_score} color={scoreColor(graph.verified_skill_score)} />
          <div>
            <p className="text-xs text-slate-500">Evidence score</p>
            <p className="text-sm font-semibold">Mean of evidence-backed skills</p>
          </div>
        </div>
      </div>
      <div className="grid gap-4 lg:grid-cols-[340px_1fr]">
        <div className="surface h-[320px] p-2">
          <Radar skills={graph.skills} />
        </div>
        <div className="space-y-2">
          {graph.skills.map((skill) => (
            <article key={skill.id} className="surface px-4 py-3">
              <div className="flex items-center justify-between gap-3">
                <h2 className="text-sm font-semibold">{skill.skill_name}</h2>
                <span className="mono text-sm font-semibold" style={{ color: scoreColor(skill.proficiency_score) }}>
                  {skill.proficiency_score}
                </span>
              </div>
              <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-100">
                <div className="h-full rounded-full" style={{ width: `${skill.proficiency_score}%`, background: scoreColor(skill.proficiency_score) }} />
              </div>
              <p className="mt-2 text-xs text-slate-500">
                {skill.verified_lwi_count} linked ticket{skill.verified_lwi_count === 1 ? "" : "s"}
                {skill.evidence_tickets.length > 0 ? ` · ${skill.evidence_tickets.join(", ")}` : ""}
                {skill.evidence_hash ? ` · ${skill.evidence_hash}` : ""}
              </p>
            </article>
          ))}
        </div>
      </div>
    </div>
  );
}

export function Empty({ label }: { label: string }) {
  return <div className="grid h-full place-items-center text-sm text-slate-500">{label}</div>;
}
