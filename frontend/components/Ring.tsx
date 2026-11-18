export function Ring({
  value,
  size = 52,
  color = "#4F46E5",
  track = "#E2E8F0",
  text = "#0F172A",
}: {
  value: number;
  size?: number;
  color?: string;
  track?: string;
  text?: string;
}) {
  const safe = Math.max(0, Math.min(100, Math.round(value)));
  const stroke = 4;
  const radius = (size - stroke * 2) / 2;
  const circ = 2 * Math.PI * radius;
  const center = size / 2;
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-label={`${safe} percent`}>
      <circle cx={center} cy={center} r={radius} stroke={track} strokeWidth={stroke} fill="none" />
      <circle
        cx={center}
        cy={center}
        r={radius}
        stroke={color}
        strokeWidth={stroke}
        fill="none"
        strokeLinecap="round"
        strokeDasharray={circ}
        strokeDashoffset={circ - (safe / 100) * circ}
        transform={`rotate(-90 ${center} ${center})`}
      />
      <text
        x={center}
        y={center + 1}
        textAnchor="middle"
        dominantBaseline="middle"
        fill={text}
        fontSize={size < 64 ? 11 : 16}
        fontFamily="IBM Plex Mono, ui-monospace, monospace"
        fontWeight="600"
      >
        {safe}
      </text>
    </svg>
  );
}
