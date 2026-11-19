"use client";

import { ArrowRight, Eye, EyeOff, GraduationCap, KanbanSquare, LockKeyhole, Radar, ShieldCheck } from "lucide-react";
import { useState } from "react";

import { api } from "@/lib/api";
import { DEMO_ACCOUNTS, DEMO_PASSWORD } from "@/lib/format";
import { setToken } from "@/lib/session";
import type { LoginResult, SessionUser } from "@/lib/types";

const PROMISES = [
  { icon: KanbanSquare, title: "Your semester as a sprint board", detail: "Course outcomes become tickets you can move and prove." },
  { icon: GraduationCap, title: "Skills backed by evidence", detail: "A score is recorded when faculty co-sign an AI-reviewed ticket." },
  { icon: Radar, title: "Early signals for mentors", detail: "Faculty and the placement cell see risk before exams do." },
];

export function LoginView({ notice, onSignedIn }: { notice: string; onSignedIn: (user: SessionUser) => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [creating, setCreating] = useState(false);
  const [reveal, setReveal] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function createAccount() {
    setBusy(true);
    setError("");
    try {
      const result = await api<LoginResult>("/api/v1/auth/register", null, {
        method: "POST",
        body: JSON.stringify({ name: name.trim(), email: email.trim(), password }),
      });
      setToken(result.token);
      onSignedIn(result.user);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not create the account");
    } finally {
      setBusy(false);
    }
  }

  async function signIn(nextEmail = email, nextPassword = password) {
    setBusy(true);
    setError("");
    try {
      const result = await api<LoginResult>("/api/v1/auth/login", null, {
        method: "POST",
        body: JSON.stringify({ email: nextEmail.trim(), password: nextPassword }),
      });
      setToken(result.token);
      onSignedIn(result.user);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not sign in");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid min-h-screen bg-canvas lg:grid-cols-[1.05fr_1fr]">
      <section className="relative hidden overflow-hidden bg-ink px-12 py-10 text-white lg:flex lg:flex-col">
        <div className="pointer-events-none absolute -right-24 -top-24 h-80 w-80 rounded-full bg-brand/30 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-32 left-10 h-72 w-72 rounded-full bg-copper/25 blur-3xl" />
        <Logo light />
        <div className="relative mt-auto max-w-md">
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#F4E6CF]">CampusFlow University · School of Computing</p>
          <h1 className="display mt-3 text-[2.6rem] leading-[1.08]">Run your semester like a product team.</h1>
          <ul className="mt-8 space-y-5">
            {PROMISES.map((item) => {
              const Icon = item.icon;
              return (
                <li key={item.title} className="flex gap-3">
                  <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-white/10">
                    <Icon size={17} />
                  </span>
                  <span>
                    <span className="block text-sm font-semibold">{item.title}</span>
                    <span className="block text-sm text-white/60">{item.detail}</span>
                  </span>
                </li>
              );
            })}
          </ul>
        </div>
        <p className="relative mt-10 flex items-center gap-2 text-xs text-white/50">
          <ShieldCheck size={14} /> Passwords are hashed. Sessions end after 12 hours or when you sign out.
        </p>
      </section>

      <section className="flex items-center justify-center px-5 py-10">
        <div className="w-full max-w-[420px]">
          <div className="lg:hidden">
            <Logo />
          </div>
          <h2 className="display mt-8 text-[2rem] leading-tight text-ink lg:mt-0">Sign in</h2>
          <p className="mt-1 text-sm text-slate-500">
            Use your campus account. Seeded Student, Faculty, and Placement workspaces stay on the buttons below for a walkthrough.
          </p>

          {notice && <p className="mt-5 rounded-2xl bg-[#F4E6CF] px-4 py-2.5 text-sm text-[#8A4A1C]">{notice}</p>}

          <form
            className="mt-6 space-y-4"
            onSubmit={(event) => {
              event.preventDefault();
              if (creating) void createAccount();
              else void signIn();
            }}
          >
            {creating && (
              <label htmlFor="login-name" className="block text-xs font-medium text-slate-600">
                Name
                <input id="login-name" className="field mt-1" value={name} onChange={(event) => setName(event.target.value)} required minLength={2} />
              </label>
            )}
            <label htmlFor="login-email" className="block text-xs font-medium text-slate-600">
              Campus email
              <input
                id="login-email"
                className="field mt-1"
                type="email"
                autoComplete="username"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="you@campusflow.edu"
                required
                autoFocus
              />
            </label>
            <label htmlFor="login-password" className="block text-xs font-medium text-slate-600">
              Password
              <span className="relative mt-1 block">
                <input
                  id="login-password"
                  className="field pr-10"
                  type={reveal ? "text" : "password"}
                  autoComplete={creating ? "new-password" : "current-password"}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  required
                  minLength={creating ? 10 : 1}
                />
                <button
                  type="button"
                  onClick={() => setReveal((value) => !value)}
                  aria-label={reveal ? "Hide password" : "Show password"}
                  className="absolute inset-y-0 right-0 grid w-10 place-items-center text-slate-400 hover:text-ink"
                >
                  {reveal ? <EyeOff size={16} aria-hidden /> : <Eye size={16} aria-hidden />}
                </button>
              </span>
            </label>
            {error && (
              <p role="alert" className="rounded-2xl bg-rose-50 px-4 py-2.5 text-sm text-rose-700">
                {error}
              </p>
            )}
            <button
              disabled={busy}
              className="inline-flex w-full items-center justify-center gap-2 rounded-full bg-brand px-4 py-3 text-sm font-semibold text-white transition hover:bg-[#0B6A57] disabled:opacity-60"
            >
              <LockKeyhole size={15} /> {busy ? "Working…" : creating ? "Create account" : "Sign in"}
            </button>
          </form>
          <button
            type="button"
            className="mt-3 text-sm font-medium text-brand"
            onClick={() => {
              setCreating((value) => !value);
              setError("");
            }}
          >
            {creating ? "Have an account? Sign in" : "Create a student account"}
          </button>

          {DEMO_PASSWORD && (
            <div className="mt-8">
              <div className="flex items-center gap-3">
                <span className="h-px flex-1 bg-line" />
                <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">Demo accounts</span>
                <span className="h-px flex-1 bg-line" />
              </div>
              <div className="mt-3 space-y-2">
                {DEMO_ACCOUNTS.map((account) => (
                  <button
                    key={account.id}
                    type="button"
                    disabled={busy}
                    onClick={() => {
                      setEmail(account.email);
                      setPassword(DEMO_PASSWORD);
                      void signIn(account.email, DEMO_PASSWORD);
                    }}
                    className="group flex w-full items-center gap-3 rounded-2xl border border-line bg-white px-3 py-2.5 text-left transition hover:-translate-y-0.5 hover:shadow-card disabled:opacity-60"
                  >
                    <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-ink text-[11px] font-semibold text-white">{account.initials}</span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-sm font-semibold text-ink">{account.name}</span>
                      <span className="block truncate text-[11px] text-slate-500">
                        {account.detail} · {account.email}
                      </span>
                    </span>
                    <ArrowRight size={15} className="text-slate-300 transition group-hover:text-brand" />
                  </button>
                ))}
              </div>
              <p className="mono mt-2 text-center text-[11px] text-slate-400">Demo password: {DEMO_PASSWORD}</p>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

function Logo({ light = false }: { light?: boolean }) {
  return (
    <div className="relative flex items-center gap-2.5">
      <div className="grid h-9 w-9 grid-cols-2 gap-0.5 rounded-xl bg-brand p-2">
        <span className="rounded-[2px] bg-white" />
        <span className="rounded-[2px] bg-white/70" />
        <span className="rounded-[2px] bg-white/70" />
        <span className="rounded-[2px] bg-white" />
      </div>
      <div>
        <p className={`text-[15px] font-semibold leading-4 ${light ? "text-white" : "text-ink"}`}>CampusFlow</p>
        <p className={`text-[11px] ${light ? "text-white/50" : "text-slate-500"}`}>Agile campus OS</p>
      </div>
    </div>
  );
}
