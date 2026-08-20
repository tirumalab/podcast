import { createClient } from "@/lib/supabase/server";
import PreferencesForm, { type Preferences } from "./PreferencesForm";
import FeedUrl from "./FeedUrl";
import Feedback from "./Feedback";

// Mirrors drive_radio/config.py's defaults, so a brand-new user starts
// from the same place the single-user pipeline does.
const DEFAULT_PREFERENCES = {
  rss_feeds: [
    "https://techcrunch.com/feed/",
    "https://www.theverge.com/rss/index.xml",
    "https://feeds.arstechnica.com/arstechnica/index",
  ],
  hn_story_count: 15,
  target_word_count_min: 2200,
  target_word_count_max: 2700,
  host_a_voice: "am_onyx",
  host_b_voice: "af_heart",
};

export default async function DashboardPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  // proxy.ts already redirects unauthenticated requests to /login, but per
  // Next.js's own guidance, don't rely on that alone — this null check is
  // the Server Component's own defense, not just a TypeScript narrowing.
  if (!user) return null;

  let { data: preferences } = await supabase
    .from("user_preferences")
    .select("*")
    .eq("user_id", user.id)
    .single();

  if (!preferences) {
    const { data: created } = await supabase
      .from("user_preferences")
      .insert({ user_id: user.id, ...DEFAULT_PREFERENCES })
      .select("*")
      .single();
    preferences = created;
  }

  const { data: feedback } = await supabase
    .from("feedback")
    .select("id, text, created_at")
    .eq("user_id", user.id)
    .order("created_at", { ascending: false })
    .limit(10);

  const baseUrl = process.env.NEXT_PUBLIC_PODCAST_BASE_URL;
  const feedUrl = `${baseUrl}/u/${user.id}/rss.xml`;

  return (
    <main className="mx-auto max-w-lg space-y-8 p-6">
      <div>
        <h1 className="text-xl font-semibold">Drive Radio</h1>
        <p className="mt-1 text-sm text-gray-600">{user.email}</p>
      </div>

      <FeedUrl feedUrl={feedUrl} />

      <Feedback userId={user.id} initialFeedback={feedback ?? []} />

      {preferences && (
        <PreferencesForm userId={user.id} initialPreferences={preferences as Preferences} />
      )}
    </main>
  );
}
