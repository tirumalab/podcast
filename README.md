# Drive Radio

A personal ~15-18 minute morning briefing, generated fresh every day from
Hacker News + a set of tech/industry RSS feeds, performed as a two-host
banter dialogue (think "The Best One Yet" energy) by text-to-speech, and
published as a private podcast RSS feed you subscribe to once in your
podcast app of choice (Apple Podcasts, Overcast, Spotify, etc.) — no custom
app needed.

Pipeline: fetch stories → Claude picks ~5-6 and writes a two-host dialogue
script with curiosity hooks, real banter, and a per-line emotional
"delivery" tag → [Kokoro](https://huggingface.co/hexgrad/Kokoro-82M) (a
free, open-weight, self-hosted TTS model — no per-minute API cost) performs
each host's lines in a distinct voice, with that delivery tag mapped to a
speaking-speed variation as a proxy for energy → a looped background music
bed gets mixed in under the whole episode → an episode manifest + `rss.xml`
get updated and published to GitHub Pages via GitHub Actions on a daily
cron.

Kokoro has no natural-language emotion control the way some paid TTS APIs
do (e.g. OpenAI's `gpt-4o-mini-tts`, which this project used before
switching) — it can't be told to "sound excited." The delivery-to-speed
mapping in `config.DELIVERY_SPEED_KEYWORDS` is a cruder stand-in: faster
pacing for excited/urgent lines, slower for dry/serious ones. Worth knowing
if you ever compare the two.

Actual songs aren't embedded — hosting copyrighted music in a
redistributable RSS feed is a real licensing problem. The background bed
should be a royalty-free instrumental loop (see setup below), which is fine
to redistribute. A future native-app version could interleave actual song
playback via a Spotify/Apple Music SDK instead, which sidesteps the
copyright issue entirely since nothing gets redistributed.

## One-time setup

### 1. Local environment (for testing)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
brew install ffmpeg espeak-ng   # pydub needs ffmpeg; Kokoro needs espeak-ng for phonemization
```

Set your API key for local runs (only Claude is a paid API now — TTS is
local/free via Kokoro, which downloads its model weights on first run):

```bash
export ANTHROPIC_API_KEY=sk-ant-...
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
  add `ANTHROPIC_API_KEY`.
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
- **Hosts & voices**: `HOST_A_NAME` / `HOST_A_VOICE` and `HOST_B_*`
  equivalents in the same file. Voice IDs are Kokoro's — see the
  [full voice list](https://huggingface.co/hexgrad/Kokoro-82M/tree/main/voices)
  (prefix convention: first letter is language, second is gender, e.g.
  `am_onyx` = American male, `af_heart` = American female).
- **Delivery/energy mapping**: `DELIVERY_SPEED_KEYWORDS` maps words that
  might show up in a line's delivery tag (excited, urgent, dry, serious,
  etc.) to a speed multiplier — add keywords or adjust the multipliers to
  taste.
- **Daily format variety**: `STYLE_VARIANTS` is a list of tone/format notes
  (rapid-fire, investigative mystery, debate, etc.) picked deterministically
  by date — add, remove, or rewrite entries to change the rotation.
- **Episode length**: `TARGET_WORD_COUNT_MIN` / `_MAX`.
- **Bumper music**: drop royalty-free clips at `assets/intro.mp3` and
  `assets/outro.mp3` — they're stitched onto the episode automatically if
  present, skipped otherwise.
- **Background music bed**: drop a royalty-free instrumental loop at
  `assets/background_music.mp3` — it's looped under the whole episode
  (including bumpers) at a reduced volume automatically if present, skipped
  otherwise. Good free sources: the
  [YouTube Audio Library](https://www.youtube.com/audiolibrary/music) (no
  attribution required) or [Pixabay Music](https://pixabay.com/music/). Pick
  something instrumental and fairly neutral in energy — it's playing
  underneath talking the entire time. `BACKGROUND_MUSIC_GAIN_DB` controls
  how far it's ducked below the dialogue (more negative = quieter); start at
  -22 and adjust after listening to one episode.
- **Schedule**: the cron line in
  [`.github/workflows/daily-episode.yml`](.github/workflows/daily-episode.yml)
  is in UTC and doesn't auto-adjust for daylight saving — nudge the hour
  twice a year if you want it pinned to a fixed local time.

## Costs

Close to $0/day for a personal feed. TTS is free — Kokoro runs locally on
CPU (in GitHub Actions' free compute for public repos), no per-minute API
charge. The only paid API left is the Claude curation call, a single cheap
request per day (plus rare retries if a script comes back short).
