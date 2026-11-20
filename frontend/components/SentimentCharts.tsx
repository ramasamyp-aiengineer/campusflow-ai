import { SENTIMENT_ORDER, SENTIMENT_STYLE } from "@/lib/format";
import type { SignalCluster } from "@/lib/types";

export function sentimentCounts(rows: { sentiment: string }[]): Record<string, number> {
  const counts: Record<string, number> = { Positive: 0, Watchful: 0, Critical: 0, Neutral: 0 };
  for (const row of rows) {
    const key = counts[row.sentiment] === undefined ? "Neutral" : row.sentiment;
    counts[key] += 1;
  }
  return counts;
}

export function SentimentDonut({ counts, caption }: { counts: Record<string, number>; caption: string }) {
  const total = SENTIMENT_ORDER.reduce((sum, label) => sum + (counts[label] ?? 0), 0);
  let cursor = 0;
  const stops = SENTIMENT_ORDER.flatMap((label) => {
    const count = counts[label] ?? 0;
    if (!count || total === 0) return [];
    const next = cursor + (count / total) * 100;
    const stop = `${SENTIMENT_STYLE[label].bar} ${cursor}% ${next}%`;
    cursor = next;
    return [stop];
  });
  const paint = stops.length ? `conic-gradient(${stops.join(", ")})` : "conic-gradient(#E7E1D8 0% 100%)";
  const captionId = "sentiment-donut-caption";

  return (
    <div className="flex items-center gap-4" role="group" aria-labelledby={captionId}>
      <div
        className="relative h-28 w-28 shrink-0"
        role="img"
        aria-label={`Sentiment breakdown across ${total} stories`}
      >
        <div className="h-full w-full rounded-full" style={{ background: paint }} />
        <div className="absolute inset-3 grid place-items-center rounded-full bg-[#FFFCF8]">
          <div className="text-center">
            <p className="mono text-lg font-semibold leading-none text-ink">{total}</p>
            <p className="mt-1 text-[10px] uppercase tracking-wide text-slate-400">stories</p>
          </div>
        </div>
      </div>
      <div className="min-w-0 flex-1">
        <p id={captionId} className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">
          {caption}
        </p>
        <ul className="mt-2 space-y-1">
          {SENTIMENT_ORDER.map((label) => (
            <li key={label} className="flex items-center justify-between gap-3 text-xs">
              <span className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full" style={{ background: SENTIMENT_STYLE[label].bar }} aria-hidden />
                <span className={SENTIMENT_STYLE[label].text}>{label}</span>
              </span>
              <span className="mono text-slate-500">{counts[label] ?? 0}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export function ClusterBars({ clusters }: { clusters: SignalCluster[] }) {
  const peak = Math.max(1, ...clusters.map((cluster) => cluster.count));
  if (clusters.length === 0) {
    return <p className="text-sm text-slate-500">Topics appear after a scan keeps at least one story.</p>;
  }
  return (
    <ul className="space-y-3">
      {clusters.map((cluster) => (
        <li key={cluster.label} aria-label={`${cluster.label}, ${cluster.count} stories`}>
          <div className="mb-1 flex items-baseline justify-between gap-2">
            <p className="truncate text-sm font-medium text-ink">{cluster.label}</p>
            <p className="mono text-[11px] text-slate-400">{cluster.count}</p>
          </div>
          <div
            className="flex h-2.5 overflow-hidden rounded-full bg-[#EFE8DC]"
            style={{ width: `${Math.max(18, (cluster.count / peak) * 100)}%` }}
            role="meter"
            aria-valuemin={0}
            aria-valuemax={peak}
            aria-valuenow={cluster.count}
            aria-label={`${cluster.label} volume`}
          >
            {SENTIMENT_ORDER.map((label) => {
              const count = cluster.sentiments[label] ?? 0;
              if (!count) return null;
              return (
                <div
                  key={label}
                  style={{ width: `${(count / cluster.count) * 100}%`, background: SENTIMENT_STYLE[label].bar }}
                />
              );
            })}
          </div>
        </li>
      ))}
    </ul>
  );
}
