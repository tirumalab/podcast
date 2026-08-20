"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";

// Reached only after auth/callback has already exchanged the recovery
// link's code for a real session — updateUser() below just needs that
// session's cookie, already set by the time this page renders.
export default function ResetPasswordPage() {
  const router = useRouter();
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");
  const [errorMessage, setErrorMessage] = useState("");

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setStatus("loading");
    setErrorMessage("");

    // See login/page.tsx for why this reads FormData instead of trusting
    // controlled `value` state.
    const formData = new FormData(e.currentTarget);
    const password = formData.get("password") as string;

    const supabase = createClient();
    const { error } = await supabase.auth.updateUser({ password });

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
          <h1 className="text-xl font-semibold">Set a new password</h1>
        </div>

        <input
          name="password"
          type="password"
          required
          minLength={6}
          autoComplete="new-password"
          placeholder="New password (min. 6 characters)"
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-base"
        />

        {status === "error" && <p className="text-sm text-red-600">{errorMessage}</p>}

        <button
          type="submit"
          disabled={status === "loading"}
          className="w-full rounded-md bg-black px-3 py-2 text-base font-medium text-white disabled:opacity-50"
        >
          {status === "loading" ? "Saving…" : "Save new password"}
        </button>
      </form>
    </main>
  );
}
