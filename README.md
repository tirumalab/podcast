# Drive Radio

A personal ~15-18 minute morning briefing, generated fresh every day from
Hacker News + a set of tech/industry RSS feeds, narrated by text-to-speech,
and published as a private podcast RSS feed you subscribe to once in your
podcast app of choice (Apple Podcasts, Overcast, Spotify, etc.) — no custom
app needed.

Pipeline: fetch stories → Claude picks ~5-6 and writes a conversational
script → OpenAI TTS narrates it → an episode manifest + `rss.xml` get
updated and published to GitHub Pages via GitHub Actions on a daily cron.

Music isn't embedded in this version — hosting copyrighted songs in a
redistributable RSS feed is a real licensing problem. A future native-app
version could interleave actual song playback via a Spotify/Apple Music SDK
instead, which sidesteps that issue since nothing gets redistributed.

## One-time setup

### 1. Local environment (for testing)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
brew install ffmpeg   # pydub needs ffmpeg on the PATH
```

Set your API keys for local runs:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
export OPENAI_API_KEY=sk-...
```

Try a dry run first — it fetches and curates but skips TTS, so you can sanity
check story selection and script quality for free:

```bash
python -m drive_radio.main --dry-run
```

When that looks good, run the full pipeline to produce a real episode:

```bash
python -m drive_radio.main
open out/episodes/*.mp3   # listen to it
```

### 2. Push to GitHub

```bash
git init
git add .
git commit -m "Initial Drive Radio pipeline"
git branch -M main
git remote add origin <your new GitHub repo URL>
git push -u origin main
```

### 3. Configure the repo on GitHub

- **Secrets** (Settings → Secrets and variables → Actions → *Secrets* tab):
  add `ANTHROPIC_API_KEY` and `OPENAI_API_KEY`.
- **Variable** (same page, *Variables* tab): add `PODCAST_BASE_URL` set to
  `https://<your-github-username>.github.io/<repo-name>`.
- Trigger the workflow once manually: Actions tab → "Daily Drive Radio
  episode" → Run workflow. This creates the `gh-pages` branch.
- After that first run succeeds, go to Settings → Pages and set the source
  to the `gh-pages` branch (GitHub sometimes picks this up automatically,
  but check).

### 4. Subscribe

Once Pages is live, your feed is at:

```
https://<your-github-username>.github.io/<repo-name>/rss.xml
```

Add that URL in your podcast app (Apple Podcasts: Library → Shows → "..." →
Follow a Show by URL; Overcast: "+" → Add URL; similar in most players).

## Customizing

- **Sources**: edit `RSS_FEEDS` in [`drive_radio/config.py`](drive_radio/config.py).
  Add your own newsletters/feeds as you get RSS URLs for them.
- **Voice**: `TTS_VOICE` in the same file (OpenAI TTS voices: alloy, echo,
  fable, onyx, nova, shimmer).
- **Episode length**: `TARGET_WORD_COUNT_MIN` / `_MAX`.
- **Bumper music**: drop royalty-free clips at `assets/intro.mp3` and
  `assets/outro.mp3` — they're stitched onto the episode automatically if
  present, skipped otherwise.
- **Schedule**: the cron line in
  [`.github/workflows/daily-episode.yml`](.github/workflows/daily-episode.yml)
  is in UTC and doesn't auto-adjust for daylight saving — nudge the hour
  twice a year if you want it pinned to a fixed local time.

## Costs

Roughly pennies per day for a personal feed: OpenAI TTS is about $0.015 per
1,000 characters (~$0.20-0.30 per 18-minute episode), and the Claude curation
call is a single request per day. GitHub Actions and Pages are free for a
public repo at this volume.
