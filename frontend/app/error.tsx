"use client";

import { useEffect } from "react";

export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="grid min-h-screen place-items-center bg-canvas px-6">
      <div className="max-w-md rounded-3xl border border-line bg-white p-8 text-center shadow-card">
        <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-copper">CampusFlow</p>
        <h1 className="mt-2 text-2xl text-ink">This screen hit a problem</h1>
        <p className="mt-2 text-sm text-slate-500">Your data is safe. Reload the view to try again.</p>
        <button onClick={reset} className="mt-5 rounded-full bg-brand px-5 py-2 text-sm font-semibold text-white">
          Reload the view
        </button>
      </div>
    </div>
  );
}
