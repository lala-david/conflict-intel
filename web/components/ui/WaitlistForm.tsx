"use client";

import { useState } from "react";

interface Props {
  interest?: string; // 'pro' | 'team' | 'api' | 'general'
  cta?: string;
  placeholder?: string;
  compact?: boolean;
}

export function WaitlistForm({
  interest = "general",
  cta = "Notify me",
  placeholder = "you@work.com",
  compact = false,
}: Props) {
  const [email, setEmail] = useState("");
  const [state, setState] = useState<"idle" | "loading" | "done" | "error">("idle");
  const [msg, setMsg] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setState("loading");
    try {
      const res = await fetch("/api/waitlist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email,
          interest,
          source: typeof window !== "undefined" ? window.location.pathname : "",
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok) {
        setState("done");
      } else {
        setState("error");
        setMsg(data?.error ?? "Something went wrong.");
      }
    } catch {
      setState("error");
      setMsg("Network error — try again.");
    }
  }

  if (state === "done") {
    return (
      <p className="text-sm font-medium text-emerald-400">
        ✓ You&apos;re on the list — we&apos;ll email you when it&apos;s ready.
      </p>
    );
  }

  return (
    <form onSubmit={submit} className={compact ? "flex gap-2" : "flex flex-col gap-2 sm:flex-row"}>
      <input
        type="email"
        required
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder={placeholder}
        className="flex-1 rounded-md border border-border bg-surface px-3 py-2 text-sm text-text-primary outline-none placeholder:text-text-dim focus:border-accent"
      />
      <button
        type="submit"
        disabled={state === "loading"}
        className="rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white transition hover:bg-accent/90 disabled:opacity-50"
      >
        {state === "loading" ? "…" : cta}
      </button>
      {state === "error" && (
        <span className="self-center text-xs text-accent">{msg}</span>
      )}
    </form>
  );
}
