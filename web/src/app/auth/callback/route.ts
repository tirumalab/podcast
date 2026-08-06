import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

// Supabase's magic link redirects here with a one-time `code` param; we
// exchange it for a real session (stored as cookies via the server client)
// then send the user on to the dashboard.
export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");

  if (code) {
    const supabase = await createClient();
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (!error) {
      return NextResponse.redirect(`${origin}/`);
    }
  }

  return NextResponse.redirect(`${origin}/login`);
}
