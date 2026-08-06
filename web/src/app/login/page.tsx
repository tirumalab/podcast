"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "sending" | "sent" | "error">("idle");
  const [errorMessage, setErrorMessage] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setStatus("sending");
    setErrorMessage("");

    const supabase = createClient();

    // Check the allowlist directly first: Supabase Auth wraps the
    // database trigger's rejection into a generic "Database error saving
    // new user" on signInWithOtp, which isn't distinguishable from any
    // other failure — this RPC (see schema.sql) gives an accurate message
    // before we even attempt sign-in.
    const { data: allowed, error: checkError } = await supabase.rpc("is_allowlisted", {
      check_email: email,
    });

    if (checkError) {
      setStatus("error");
      setErrorMessage(checkError.message);
      return;
    }

    if (!allowed) {
      setStatus("error");
      setErrorMessage("That email hasn't been invited yet. Ask whoever's running this to add you.");
      return;
    }

    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: {
        emailRedirectTo: `${window.location.origin}/auth/callback`,
      },
    });

    if (error) {
      setStatus("error");
      setErrorMessage(error.message);
      return;
    }

    setStatus("sent");
  }

  if (status === "sent") {
    return (
      <main className="flex min-h-screen items-center justify-center p-6">
        <div className="max-w-sm text-center">
          <h1 className="text-xl font-semibold">Check your email</h1>
          <p className="mt-2 text-gray-600">
            We sent a sign-in link to <span className="font-medium">{email}</span>. Open it on
            this device to finish logging in.
          </p>
        </div>
      </main>
    );
  }

  return (
    <main className="flex min-h-screen items-center justify-center p-6">
      <form onSubmit={handleSubmit} className="w-full max-w-sm space-y-4">
        <div>
          <h1 className="text-xl font-semibold">Drive Radio</h1>
          <p className="mt-1 text-gray-600">Sign in with your email — no password needed.</p>
        </div>

        <input
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@example.com"
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-base"
        />

        {status === "error" && <p className="text-sm text-red-600">{errorMessage}</p>}

        <button
          type="submit"
          disabled={status === "sending"}
          className="w-full rounded-md bg-black px-3 py-2 text-base font-medium text-white disabled:opacity-50"
        >
          {status === "sending" ? "Sending…" : "Send sign-in link"}
        </button>
      </form>
    </main>
  );
}
