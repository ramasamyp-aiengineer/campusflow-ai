import { LogOut, Menu, Search } from "lucide-react";
import { useState } from "react";

import { api } from "@/lib/api";
import { DEMO_ACCOUNTS, DEMO_PASSWORD, waitLabel } from "@/lib/format";
import { clearToken, setToken } from "@/lib/session";
import type { Bootstrap, LoginResult, Persona, SessionUser } from "@/lib/types";

const ROLE_LABEL: Record<string, string> = { student: "Student", faculty: "Faculty", tpo: "Placement Cell" };
const SWITCH_LABEL: Record<Persona, string> = { student: "Arjun", faculty: "Faculty", tpo: "Placement" };

export function TopBar({
  user,
  boot,
  query,
  liveLabel,
  onQuery,
  onSignOut,
  onSwitched,
  onMenu,
}: {
  user: SessionUser;
  boot: Bootstrap;
  query: string;
  liveLabel: string;
  onQuery: (value: string) => void;
  onSignOut: () => void;
  onSwitched: (next: SessionUser) => void;
  onMenu: () => void;
}) {
  const persona = user.persona;
  const model = boot.ai_mode === "gemini" ? "Gemini connected" : "Local rules";
  const [switching, setSwitching] = useState(false);

  async function switchPersona(next: (typeof DEMO_ACCOUNTS)[number]) {
    if (next.id === persona || switching) return;
    setSwitching(true);
    try {
      try {
        await api("/api/v1/auth/logout", null, { method: "POST" });
      } catch {
        // Local token is replaced either way.
      }
      clearToken();
      const result = await api<LoginResult>("/api/v1/auth/login", null, {
        method: "POST",
        body: JSON.stringify({ email: next.email, password: DEMO_PASSWORD }),
      });
      setToken(result.token);
      onSwitched(result.user);
    } catch {
      onSignOut();
    } finally {
      setSwitching(false);
    }
  }

  return (
    <div className="border-b border-line bg-[#FFFCF8]/90 backdrop-blur">
      <header className="flex flex-wrap items-center gap-3 px-4 py-3">
        <button className="rounded-lg border border-line p-2 md:hidden" onClick={onMenu} aria-label="Open navigation">
          <Menu size={16} />
        </button>
        <div className="min-w-0">
          <p className="truncate text-[11px] text-slate-500">
            {boot.institution.university} / {boot.institution.college} / {boot.institution.department}
          </p>
          <p className="display text-lg leading-none text-ink">{boot.semester_label}</p>
          {persona === "student" && (
            <p className="text-[11px] text-slate-400">Signals rescan in {waitLabel(boot.signal_next_poll)}</p>
          )}
        </div>
        <div className="order-3 flex w-full items-center gap-2 rounded-full border border-line bg-canvas px-3 py-1.5 sm:order-none sm:ml-auto sm:w-auto">
          <Search size={14} className="text-slate-400" />
          <input
            value={query}
            onChange={(event) => onQuery(event.target.value)}
            placeholder="Filter tickets, skills, CO tags"
            aria-label="Filter tickets, skills, and CO tags"
            className="w-full bg-transparent text-sm outline-none sm:w-56"
          />
        </div>
        <div className="flex items-center gap-2">
          {DEMO_PASSWORD ? (
            <div
              className="flex items-center rounded-full border border-line bg-canvas p-1"
              role="group"
              aria-label="Instant persona switcher"
            >
              {DEMO_ACCOUNTS.map((account) => {
                const active = account.id === persona;
                return (
                  <button
                    key={account.id}
                    type="button"
                    disabled={switching}
                    onClick={() => void switchPersona(account)}
                    className={`rounded-full px-2.5 py-1.5 text-xs font-semibold transition disabled:opacity-60 ${
                      active ? "bg-ink text-white shadow-card" : "text-slate-500 hover:bg-white hover:text-ink"
                    }`}
                    title={`${account.name} · ${account.detail}`}
                    aria-pressed={active}
                  >
                    {SWITCH_LABEL[account.id]}
                  </button>
                );
              })}
            </div>
          ) : null}
          <div className="flex items-center gap-1 rounded-full border border-line bg-canvas p-1">
            <span className="flex items-center gap-2 rounded-full bg-white px-2.5 py-1 shadow-card" title={user.email}>
              <span className="grid h-6 w-6 place-items-center rounded-full bg-brand text-[10px] font-semibold text-white">
                {user.avatar_initials}
              </span>
              <span className="hidden lg:block">
                <span className="block text-xs font-semibold leading-4 text-ink">{user.name}</span>
                <span className="block text-[10px] text-slate-500">{ROLE_LABEL[persona] ?? user.role}</span>
              </span>
            </span>
            <button
              onClick={onSignOut}
              className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1.5 text-xs font-semibold text-slate-500 transition hover:bg-white hover:text-rose-700"
              aria-label="Sign out"
            >
              <LogOut size={14} /> <span className="hidden md:inline">Sign out</span>
            </button>
          </div>
        </div>
      </header>
      <div className="flex items-center gap-2 border-t border-line/80 px-4 py-1.5 text-xs">
        <span className="live-dot" aria-hidden />
        <span className="font-semibold text-brand">Live</span>
        <span className="text-slate-500">{model}</span>
        <span className="text-[#D6CFC4]">·</span>
        <span className="min-w-0 flex-1 truncate text-slate-600">{liveLabel}</span>
        {persona === "student" && <span className="hidden text-slate-400 sm:inline">Board refreshes every 60s</span>}
      </div>
    </div>
  );
}
