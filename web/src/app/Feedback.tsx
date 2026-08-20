"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";

export type FeedbackEntry = { id: string; text: string; created_at: string };

export default function Feedback({
  userId,
  initialFeedback,
}: {
  userId: string;
  initialFeedback: FeedbackEntry[];
}) {
  const [entries, setEntries] = useState(initialFeedback);
  const [text, setText] = useState("");
  const [status, setStatus] = useState<"idle" | "saving" | "error">("idle");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!text.trim()) return;
    setStatus("saving");

    const supabase = createClient();
    const { data, error } = await supabase
      .from("feedback")
      .insert({ user_id: userId, text: text.trim() })
      .select("id, text, created_at")
      .single();

    if (error || !data) {
      setStatus("error");
      return;
    }
    setEntries([data, ...entries]);
    setText("");
    setStatus("idle");
  }

  async function handleDelete(id: string) {
    setEntries(entries.filter((e) => e.id !== id));
    const supabase = createClient();
    await supabase.from("feedback").delete().eq("id", id);
  }

  return (
    <div className="rounded-lg border border-gray-200 p-4">
      <h2 className="font-medium">Feedback</h2>
      <p className="mt-1 text-sm text-gray-600">
        Tell the hosts what to do differently — too many analogies, more jokes, skip crypto
        stories, whatever. It gets factored into future episodes.
      </p>

      <form onSubmit={handleSubmit} className="mt-3 flex gap-2">
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="e.g. less music, more banter"
          className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm"
        />
        <button
          type="submit"
          disabled={status === "saving"}
          className="shrink-0 rounded-md bg-black px-3 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          Send
        </button>
      </form>
      {status === "error" && (
        <p className="mt-2 text-sm text-red-600">Something went wrong — try again.</p>
      )}

      {entries.length > 0 && (
        <ul className="mt-4 space-y-2">
          {entries.map((entry) => (
            <li
              key={entry.id}
              className="flex items-start justify-between gap-3 rounded-md bg-gray-50 px-3 py-2 text-sm"
            >
              <span>{entry.text}</span>
              <button
                type="button"
                onClick={() => handleDelete(entry.id)}
                aria-label="Remove"
                className="shrink-0 text-gray-400 hover:text-red-600"
              >
                ✕
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
