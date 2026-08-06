"use client";

import { useState } from "react";

export default function FeedUrl({ feedUrl }: { feedUrl: string }) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    await navigator.clipboard.writeText(feedUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="rounded-lg border border-gray-200 p-4">
      <h2 className="font-medium">Your feed</h2>
      <p className="mt-1 text-sm text-gray-600">
        Add this URL in your podcast app (Pocket Casts, Podcast Addict, or AntennaPod on
        Android; Apple Podcasts or Overcast on iOS) — look for &ldquo;Add by URL&rdquo; or
        &ldquo;Add custom feed&rdquo;.
      </p>
      <div className="mt-3 flex gap-2">
        <input
          readOnly
          value={feedUrl}
          onFocus={(e) => e.target.select()}
          className="flex-1 truncate rounded-md border border-gray-300 bg-gray-50 px-3 py-2 text-sm"
        />
        <button
          onClick={handleCopy}
          className="shrink-0 rounded-md bg-black px-3 py-2 text-sm font-medium text-white"
        >
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <p className="mt-2 text-xs text-gray-500">
        A new episode is generated for you daily. Once you subscribe, it&apos;ll just show up.
      </p>
    </div>
  );
}
