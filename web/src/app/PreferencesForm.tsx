"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";

export type Preferences = {
  rss_feeds: string[];
  hn_story_count: number;
  target_word_count_min: number;
  target_word_count_max: number;
  host_a_voice: string;
  host_b_voice: string;
};

// A curated subset of Kokoro's voices (see drive_radio/config.py for the
// full list) — labeled by what the voice ID itself encodes (language,
// gender), not by invented character descriptions we haven't verified.
const VOICE_OPTIONS = [
  { id: "am_onyx", label: "am_onyx — American, male" },
  { id: "am_michael", label: "am_michael — American, male" },
  { id: "am_adam", label: "am_adam — American, male" },
  { id: "af_heart", label: "af_heart — American, female" },
  { id: "af_bella", label: "af_bella — American, female" },
  { id: "af_nova", label: "af_nova — American, female" },
  { id: "bm_george", label: "bm_george — British, male" },
  { id: "bm_daniel", label: "bm_daniel — British, male" },
  { id: "bf_emma", label: "bf_emma — British, female" },
  { id: "bf_alice", label: "bf_alice — British, female" },
];

const LENGTH_PRESETS = [
  { label: "Short (~8-10 min)", min: 1200, max: 1500 },
  { label: "Medium (~15-18 min)", min: 2200, max: 2700 },
  { label: "Long (~20-25 min)", min: 3000, max: 3500 },
];

function presetForRange(min: number, max: number) {
  const match = LENGTH_PRESETS.find((p) => p.min === min && p.max === max);
  return match ?? LENGTH_PRESETS[1];
}

export default function PreferencesForm({
  userId,
  initialPreferences,
}: {
  userId: string;
  initialPreferences: Preferences;
}) {
  const [feedsText, setFeedsText] = useState(initialPreferences.rss_feeds.join("\n"));
  const [hostAVoice, setHostAVoice] = useState(initialPreferences.host_a_voice);
  const [hostBVoice, setHostBVoice] = useState(initialPreferences.host_b_voice);
  const [lengthPreset, setLengthPreset] = useState(
    presetForRange(
      initialPreferences.target_word_count_min,
      initialPreferences.target_word_count_max,
    ).label,
  );
  const [status, setStatus] = useState<"idle" | "saving" | "saved" | "error">("idle");

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setStatus("saving");

    const preset = LENGTH_PRESETS.find((p) => p.label === lengthPreset)!;
    const rss_feeds = feedsText
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean);

    const supabase = createClient();
    const { error } = await supabase
      .from("user_preferences")
      .update({
        rss_feeds,
        target_word_count_min: preset.min,
        target_word_count_max: preset.max,
        host_a_voice: hostAVoice,
        host_b_voice: hostBVoice,
      })
      .eq("user_id", userId);

    setStatus(error ? "error" : "saved");
    if (!error) setTimeout(() => setStatus("idle"), 2000);
  }

  return (
    <form onSubmit={handleSave} className="space-y-5">
      <h2 className="font-medium">Preferences</h2>

      <div>
        <label className="block text-sm font-medium text-gray-700">
          Sources (one RSS feed URL per line)
        </label>
        <textarea
          value={feedsText}
          onChange={(e) => setFeedsText(e.target.value)}
          rows={4}
          className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 font-mono text-xs"
        />
        <p className="mt-1 text-xs text-gray-500">Hacker News is always included automatically.</p>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700">Episode length</label>
        <select
          value={lengthPreset}
          onChange={(e) => setLengthPreset(e.target.value)}
          className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
        >
          {LENGTH_PRESETS.map((p) => (
            <option key={p.label} value={p.label}>
              {p.label}
            </option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-sm font-medium text-gray-700">Host 1 voice</label>
          <select
            value={hostAVoice}
            onChange={(e) => setHostAVoice(e.target.value)}
            className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
          >
            {VOICE_OPTIONS.map((v) => (
              <option key={v.id} value={v.id}>
                {v.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">Host 2 voice</label>
          <select
            value={hostBVoice}
            onChange={(e) => setHostBVoice(e.target.value)}
            className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
          >
            {VOICE_OPTIONS.map((v) => (
              <option key={v.id} value={v.id}>
                {v.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <button
        type="submit"
        disabled={status === "saving"}
        className="w-full rounded-md bg-black px-3 py-2 text-sm font-medium text-white disabled:opacity-50"
      >
        {status === "saving" ? "Saving…" : status === "saved" ? "Saved" : "Save preferences"}
      </button>
      {status === "error" && (
        <p className="text-sm text-red-600">Something went wrong saving — try again.</p>
      )}
      <p className="text-xs text-gray-500">
        Changes apply to tomorrow&apos;s episode, not one already generated today.
      </p>
    </form>
  );
}
