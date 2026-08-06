import { createBrowserClient } from "@supabase/ssr";

// Safe to expose client-side: the anon key can only ever do what Row Level
// Security on each table allows, which is "read/write your own rows only"
// (see ../../../schema.sql). The real access control is enforced in
// Postgres, not by hiding this key.
export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
  );
}
