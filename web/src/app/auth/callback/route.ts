import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

// Supabase redirects here with a one-time `code` after a signup
// confirmation, a password-recovery link, or (legacy) a magic link; we
// exchange it for a real session (stored as cookies via the server client)
// then send the user on to `next` (defaults to the dashboard) — the
// forgot-password flow sets next=/auth/reset-password so the recovery
// session lands on the "set a new password" form instead.
export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");
  const next = searchParams.get("next") || "/";

  if (code) {
    const supabase = await createClient();
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (!error) {
      return NextResponse.redirect(`${origin}${next}`);
    }
  }

  return NextResponse.redirect(`${origin}/login`);
}
