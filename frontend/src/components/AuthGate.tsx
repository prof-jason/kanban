"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { KanbanBoard } from "@/components/KanbanBoard";

type AuthState = "loading" | "signed-out" | "signed-in";

export const AuthGate = () => {
  const [authState, setAuthState] = useState<AuthState>("loading");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    const loadSession = async () => {
      try {
        const response = await fetch("/api/auth/session");
        if (!response.ok) {
          throw new Error("Unable to check your session.");
        }
        const session = (await response.json()) as { authenticated: boolean };
        setAuthState(session.authenticated ? "signed-in" : "signed-out");
      } catch {
        setError("Unable to check your session.");
        setAuthState("signed-out");
      }
    };

    void loadSession();
  }, []);

  const handleLogin = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);

    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

      if (!response.ok) {
        setError("Invalid username or password.");
        return;
      }

      setPassword("");
      setAuthState("signed-in");
    } catch {
      setError("Unable to sign in. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleUnauthorized = useCallback(() => {
    setAuthState("signed-out");
    setError("Your session has ended. Please sign in again.");
  }, []);

  const handleLogout = async () => {
    await fetch("/api/auth/logout", { method: "POST" });
    setAuthState("signed-out");
    setUsername("");
    setPassword("");
  };

  if (authState === "loading") {
    return <main className="p-6 text-[var(--gray-text)]">Loading session...</main>;
  }

  if (authState === "signed-in") {
    return <KanbanBoard onLogout={handleLogout} onUnauthorized={handleUnauthorized} />;
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-[var(--surface)] p-6">
      <form
        onSubmit={handleLogin}
        className="w-full max-w-sm space-y-5 rounded-2xl border border-[var(--stroke)] bg-white p-8 shadow-[var(--shadow)]"
      >
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--primary-blue)]">
            Project Management
          </p>
          <h1 className="mt-2 font-display text-3xl font-semibold text-[var(--navy-dark)]">
            Sign in
          </h1>
        </div>
        <label className="block text-sm font-medium text-[var(--navy-dark)]">
          Username
          <input
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            autoComplete="username"
            className="mt-2 w-full rounded-xl border border-[var(--stroke)] px-3 py-2 text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
            required
          />
        </label>
        <label className="block text-sm font-medium text-[var(--navy-dark)]">
          Password
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="current-password"
            className="mt-2 w-full rounded-xl border border-[var(--stroke)] px-3 py-2 text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
            required
          />
        </label>
        {error && <p className="text-sm text-red-700">{error}</p>}
        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full rounded-xl bg-[var(--secondary-purple)] px-4 py-3 text-sm font-semibold text-white transition hover:brightness-110 disabled:opacity-60"
        >
          {isSubmitting ? "Signing in..." : "Sign in"}
        </button>
      </form>
    </main>
  );
};