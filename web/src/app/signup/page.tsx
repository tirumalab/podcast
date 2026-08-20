"use client";

import { useState } from "react";
import Link from "next/link";
import { createClient } from "@/lib/supabase/client";

export default function SignupPage() {
  const [sentEmail, setSentEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "sent" | "error">("idle");
  const [errorMessage, setErrorMessage] = useState("");

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setStatus("loading");
    setErrorMessage("");

    // See login/page.tsx for why this reads FormData instead of trusting
    // controlled `value` state — autofilled fields don't reliably fire
    // React's onChange.
    const formData = new FormData(e.currentTarget);
    const email = formData.get("email") as string;
    const password = formData.get("password") as string;

    const supabase = createClient();

    // Check the allowlist directly first: Supabase Auth wraps the database
    // trigger's rejection into a generic "Database error saving new user",
    // which isn't distinguishable from any other failure — this RPC (see
    // schema.sql) gives an accurate message before we even attempt signup.
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

    const { error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        emailRedirectTo: `${window.location.origin}/auth/callback`,
      },
    });

    if (error) {
      setStatus("error");
      setErrorMessage(error.message);
      return;
    }

    setSentEmail(email);
    setStatus("sent");
  }

  if (status === "sent") {
    return (
      <main className="flex min-h-screen items-center justify-center p-6">
        <div className="max-w-sm text-center">
          <h1 className="text-xl font-semibold">Check your email</h1>
          <p className="mt-2 text-gray-600">
            We sent a confirmation link to <span className="font-medium">{sentEmail}</span>. Open
            it to finish creating your account.
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
          <p className="mt-1 text-gray-600">Create your account.</p>
        </div>

        <input
          name="email"
          type="email"
          required
          autoComplete="email"
          placeholder="you@example.com"
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-base"
        />
        <input
          name="password"
          type="password"
          required
          minLength={6}
          autoComplete="new-password"
          placeholder="Password (min. 6 characters)"
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-base"
        />

        {status === "error" && <p className="text-sm text-red-600">{errorMessage}</p>}

        <button
          type="submit"
          disabled={status === "loading"}
          className="w-full rounded-md bg-black px-3 py-2 text-base font-medium text-white disabled:opacity-50"
        >
          {status === "loading" ? "Creating account…" : "Create account"}
        </button>

        <p className="text-sm text-gray-600">
          Already have an account?{" "}
          <Link href="/login" className="font-medium text-black hover:underline">
            Sign in
          </Link>
        </p>
      </form>
    </main>
  );
}
