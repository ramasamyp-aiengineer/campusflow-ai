"use client";

import { useEffect, useState } from "react";

import { AppShell } from "@/components/AppShell";
import { LoginView } from "@/components/LoginView";
import { ApiError, api } from "@/lib/api";
import { SIGNED_OUT_EVENT, clearToken, getToken } from "@/lib/session";
import type { SessionUser } from "@/lib/types";

export default function HomePage() {
  const [user, setUser] = useState<SessionUser | null>(null);
  const [checking, setChecking] = useState(true);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    if (!getToken()) {
      setChecking(false);
      return;
    }
    api<SessionUser>("/api/v1/auth/me", null)
      .then(setUser)
      .catch((reason) => {
        if (reason instanceof ApiError && reason.status === 0) setNotice(reason.message);
        else clearToken();
      })
      .finally(() => setChecking(false));
  }, []);

  useEffect(() => {
    const onSignedOut = () => {
      setUser(null);
      setNotice("Your session has ended. Sign in again.");
    };
    window.addEventListener(SIGNED_OUT_EVENT, onSignedOut);
    return () => window.removeEventListener(SIGNED_OUT_EVENT, onSignedOut);
  }, []);

  async function signOut() {
    try {
      await api("/api/v1/auth/logout", null, { method: "POST" });
    } catch {
      // The token is dropped locally either way.
    }
    clearToken();
    setNotice("You are signed out.");
    setUser(null);
  }

  if (checking) return <div className="grid h-screen place-items-center text-sm text-slate-500">Opening CampusFlow…</div>;
  if (!user) {
    return (
      <LoginView
        notice={notice}
        onSignedIn={(next) => {
          setNotice("");
          setUser(next);
        }}
      />
    );
  }
  return (
    <AppShell
      key={user.id}
      user={user}
      onSignOut={() => void signOut()}
      onSwitched={(next) => {
        setNotice("");
        setUser(next);
      }}
    />
  );
}
