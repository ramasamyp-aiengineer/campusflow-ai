import type { Skill } from "@/lib/types";

export function Radar({ skills }: { skills: Skill[] }) {
  const points = skills.slice(0, 8);
  const count = Math.max(points.length, 3);
  const cx = 160;
  const cy = 150;
  const radius = 92;

  const at = (index: number, scale: number) => {
    const angle = -Math.PI / 2 + (index * 2 * Math.PI) / count;
    return [cx + Math.cos(angle) * radius * scale, cy + Math.sin(angle) * radius * scale];
  };

  const grid = [0.35, 0.65, 1];
  const polygon = points
    .map((skill, index) => at(index, skill.proficiency_score / 100).join(","))
    .join(" ");

  return (
    <svg viewBox="0 0 320 300" className="h-full w-full">
      {grid.map((scale) => (
        <polygon
          key={scale}
          fill="none"
          stroke="#E2E8F0"
          strokeWidth="1"
          points={Array.from({ length: count }, (_, index) => at(index, scale).join(",")).join(" ")}
        />
      ))}
      {Array.from({ length: count }, (_, index) => {
        const [x, y] = at(index, 1);
        return <line key={index} x1={cx} y1={cy} x2={x} y2={y} stroke="#E2E8F0" />;
      })}
      {points.length > 0 && (
        <polygon points={polygon} fill="rgba(79, 70, 229, 0.18)" stroke="#4F46E5" strokeWidth="2" />
      )}
      {points.map((skill, index) => {
        const [x, y] = at(index, skill.proficiency_score / 100);
        const [lx, ly] = at(index, 1.18);
        return (
          <g key={skill.id}>
            <circle cx={x} cy={y} r="3.5" fill="#4F46E5" />
            <text
              x={lx}
              y={ly}
              textAnchor="middle"
              dominantBaseline="middle"
              fill="#334155"
              fontSize="11"
              fontFamily="Plus Jakarta Sans, sans-serif"
            >
              {skill.skill_name.length > 18 ? `${skill.skill_name.slice(0, 16)}…` : skill.skill_name}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
