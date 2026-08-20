"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";

export default function LoginPage() {
  const router = useRouter();
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");
  const [errorMessage, setErrorMessage] = useState("");

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setStatus("loading");
    setErrorMessage("");

    // Read straight from the DOM via FormData rather than trusting React's
    // controlled `value` state: some browsers/password managers autofill a
    // field without firing the `input` event React listens to, so the
    // field visibly shows the saved password but React's state stays
    // empty — sending that stale state gets a real "invalid credentials"
    // rejection that only "fixes itself" on a reload (autofill re-fires
    // differently). FormData always reflects the field's actual value.
    const formData = new FormData(e.currentTarget);
    const email = formData.get("email") as string;
    const password = formData.get("password") as string;

    const supabase = createClient();
    const { error } = await supabase.auth.signInWithPassword({ email, password });

    if (error) {
      setStatus("error");
      setErrorMessage(error.message);
      return;
    }

    router.push("/");
    router.refresh();
  }

  return (
    <main className="flex min-h-screen items-center justify-center p-6">
      <form onSubmit={handleSubmit} className="w-full max-w-sm space-y-4">
        <div>
          <h1 className="text-xl font-semibold">Drive Radio</h1>
          <p className="mt-1 text-gray-600">Sign in to your account.</p>
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
          autoComplete="current-password"
          placeholder="Password"
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-base"
        />

        {status === "error" && <p className="text-sm text-red-600">{errorMessage}</p>}

        <button
          type="submit"
          disabled={status === "loading"}
          className="w-full rounded-md bg-black px-3 py-2 text-base font-medium text-white disabled:opacity-50"
        >
          {status === "loading" ? "Signing in…" : "Sign in"}
        </button>

        <div className="flex justify-between text-sm text-gray-600">
          <Link href="/signup" className="hover:text-black">
            Create an account
          </Link>
          <Link href="/forgot-password" className="hover:text-black">
            Forgot password?
          </Link>
        </div>
      </form>
    </main>
  );
}
