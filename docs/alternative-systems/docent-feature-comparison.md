# Docent (danmunz/docent) vs. framegallery

A feature and architecture comparison against the open-source
[`danmunz/docent`](https://github.com/danmunz/docent) project, which targets the same goal as
framegallery: getting a personal photo/art library onto a Samsung "The Frame" TV in Art Mode.

Analysis performed 2026-07-16 against the `main` branch of the GitHub repository (Docent v1.0.1).

## What it is, in one line

Docent is a **long-running async FastAPI server** (much like framegallery) whose defining bet is
a rich **AI art-curation layer** — reverse-image identification, LLM analysis, and weather-aware
recommendations — bolted onto a polished single-file "museum" web UI, with **no database** (all
state in JSON files and the TV's own storage) and **no app-managed slideshow** (it defers rotation
to the TV or to explicit user/AI clicks).

Of the three alternative systems reviewed so far, Docent is architecturally the **closest** to
framegallery (async FastAPI, persistent connection, uploads to TV storage) while being the
**furthest** on feature philosophy (AI curation vs. filter-driven automation).

## Feature overview of Docent

| Area | What it does |
|---|---|
| **Core model** | "Send any image to your Frame with one click." Browse gallery → "Display on Frame" → `select_image` on the TV |
| **Gallery UI** | Dense grid, hover titles, lazy thumbnails, lightbox, keyboard nav, year grouping with adaptive bucketing, sticky group nav, collections, bulk ops |
| **AI art analysis** | Two-stage: **Google Vision** reverse-image identification → **Claude or OpenAI** vision analysis returning artist/title/year/medium/movement/mood/description; auto-analyze on upload; batch analysis; low-confidence Opus escalation |
| **Atmosphere** | Weather-aware curation — reads local weather (NWS → Open-Meteo fallback), matches gallery mood metadata, presents 3 LLM-curated picks with curator's notes and a variety engine that avoids repeats |
| **Wikipedia links** | Every metadata field (artist/school/medium/year/title) becomes a client-side Wikipedia link |
| **Google Drive sync** | Import artwork from a shared Drive folder, with per-sync `file_map` dedup by Drive file ID |
| **TV controls** | Art-mode toggle, matte selection (shadow box / modern / panoramic), photo filters, favourites, slideshow config passed through to the TV |
| **Cropping** | Client-side crop editor with 16:9 compliance checking; smart-crop heuristic in the browser + optional Google Vision "crop hint" seed |
| **Cost tracking** | Per-model token counts and monthly cost estimates in `api_usage.json` |
| **Ops** | `Docent.command` double-click launcher with setup wizard (macOS), Docker image on GHCR, `/health` endpoint, 90 integration tests |
| **Persistence** | **JSON files only** (`artwork_meta.json`, `collections.json`, `ai_config.json`, `api_usage.json`, `drive_sync.json`, `atmosphere_history.json`) + `.tv-token` + local `.cache/`. No database (a deliberate guardrail) |
| **Security posture** | No auth, no multi-user, single TV — same "trusted LAN" posture as the others |

## How Docent manages the TV connection

- **Library:** upstream **`samsungtvws==3.0.4`** from PyPI (not a fork), the **synchronous**
  `SamsungTVWS` + `.art()` API — *not* the async `SamsungTVAsyncArt`.
  Blocking calls are pushed off the event loop with `asyncio.to_thread`.
- **Persistent singleton with idle recycling:** module-level `_tv_conn` / `_tv_art` /
  `_tv_last_used` globals.
  `_ensure_tv_connection()` reuses the open art WebSocket but proactively closes and reopens it
  if idle longer than **30 s** (`TV_CONN_MAX_IDLE`), because the Frame's sockets go stale after
  ~30–60 s of inactivity and start throwing `BrokenPipeError`.
- **Serialized access:** a single `asyncio.Lock` (`_tv_lock`) wraps *all* TV I/O via a
  `_tv_op(fn, *, attempts, timeout)` helper, because the Frame dislikes concurrent connections.
- **Pairing:** delegated entirely to the library's `token_file=.tv-token` mechanism; first
  connect pops the on-screen "Allow" prompt on the token-secured port (default **8001**), then
  the token is reused.
  No custom two-channel pairing workaround.
- **Reliability is the headline investment:**
  - `_tv_op` retries `DOCENT_TV_ATTEMPTS` (default 3) times with `DOCENT_TV_RETRY_DELAY` (2 s)
    between attempts, each attempt bounded by `asyncio.wait_for` so a hung socket can't hold the
    lock forever.
  - On failure it closes the connection and **sends a Wake-on-LAN magic packet** (if
    `DOCENT_TV_MAC` is set) before retrying — the documented quirk being that the Frame often
    accepts the TCP socket without answering the art handshake.
  - `ResponseError` (a definitive TV rejection) is **not** retried.
  - Uploads use `attempts=1, timeout=120` so a lost response can't cause a duplicate upload.
  - A **circuit breaker** around batch thumbnail fetches (60 s cooldown after a failure) plus a
    background thumbnail prefetch task with escalating backoff and a self-rescheduling retry.
  - Endpoints degrade gracefully — serving stale cache with `"stale": true`, or HTTP 502
    "Cannot reach TV — is it on and connected?" — when the TV is unreachable.

## How framegallery differs

| Dimension | Docent | framegallery |
|---|---|---|
| **Runtime shape** | Long-running **async FastAPI** server | Long-running **async FastAPI** server — *same* |
| **samsungtvws** | Upstream sync `SamsungTVWS.art()`, run via `to_thread` | **Own git fork**, native async `SamsungTVAsyncArt` + `SamsungTVWSAsyncRemote` |
| **Connection** | Persistent singleton, **30 s idle recycle**, serialized by `_tv_lock` | Persistent, `start_listening()` + push callbacks; ICMP-ping-driven reconnect |
| **Pairing quirk** | WoL + retry (handshake quirk); library token file | Recent firmware won't pair on the art channel → pairs on the **remote channel first**, reuses token |
| **What drives rotation** | **Nothing app-side** — user click, or the TV's native slideshow, or on-demand Atmosphere | **The app** pushes one active image every `slideshow_interval` (180 s) |
| **Images on the TV** | Uploads all, no cap, lets the Frame hold them | Essentially **one at a time** — upload → activate → delete previous (+ cleanup keeping last 3) |
| **Image source** | Browser upload + Google Drive import | Pluggable **libraries** — local SQLite gallery **+ Immich** (streamed originals) |
| **Selection** | Manual, or LLM-curated (Atmosphere), or TV shuffle | **Filter-driven** (react-querybuilder) + weighted-random across libraries |
| **Persistence** | **JSON files only, no DB** (explicit guardrail) | **SQLite + SQLAlchemy + Alembic** migrations |
| **AI / curation** | **Extensive** — Vision ID, Claude/OpenAI analysis, weather-aware Atmosphere, cost tracking | None |
| **Metadata display** | Rich (artist/title/year/medium/movement/mood) + Wikipedia links | None — filename/keyword based |
| **Cropping** | Client-side editor + browser smart-crop + Google Vision crop-hint seed | Server-side percentage crop + aspect-ratio pipeline (3:2 / 4:3 → 16:9) |
| **Reliability plumbing** | WoL, bounded-timeout retries, circuit breaker, prefetch backoff, stale-cache fallback | ICMP pinger, reconnect on disconnect, per-op guards, 60 s upload timeout |
| **Real-time UI** | **None** — REST polling + thumbnail fallback/retry | **SSE** (`/api/slideshow/events`) pushes updates to the React app |
| **Frontend** | Single-file vanilla HTML/CSS/JS (no build step, by guardrail) | React/TypeScript + Vite + Material-UI |
| **Matte** | Client-baked crop; `shadowbox_polar` default, plus `change_matte` / photo filters | `none` for 16:9, `shadowbox_black` otherwise; portrait matte `none` |
| **Auth** | None (by design) | None either |

## Ideas from Docent worth considering for framegallery

Docent's strengths are almost entirely on the **curation and reliability** axes, which is exactly
where framegallery is thinnest:

1. **AI art analysis + metadata** — the marquee feature.
   A two-stage Google Vision → Claude/OpenAI pipeline that returns artist/title/year/medium/mood
   and a description, with cost tracking.
   framegallery has *no* metadata enrichment at all; even a cut-down "identify + describe" pass
   would be a real differentiator (and note the close-hauled project does a lighter version of
   this for location plaques).
2. **Atmosphere / weather-aware curation** — genuinely novel.
   Match gallery mood metadata against local weather and surface a few curated picks.
   This depends on (1) existing first, but it is the kind of feature that gets a project written
   up in The Verge.
3. **Connection reliability plumbing** — the most directly portable ideas:
   - **Proactive idle recycle** (close + reopen after ~30 s idle) to pre-empt the Frame's stale-socket `BrokenPipeError`.
     framegallery relies on catching the error after the fact.
   - **Wake-on-LAN before retry.** framegallery already depends on `wakeonlan` but does not
     import or use it in the connector — Docent shows the pattern (magic packet, gated on a MAC env var).
   - **A circuit breaker + stale-cache fallback** so a flaky TV degrades gracefully instead of
     hanging requests.
4. **A real `/health` endpoint** that checks data-file integrity and directory writability
   (framegallery's `/api/status` is currently hardcoded to `tv_on=True, art_mode_active=True`).
5. **Cost tracking for AI usage** — relevant only if framegallery adds AI, but a nice pattern:
   a per-model pricing table and monthly token/cost accounting.

Conversely, framegallery is ahead on **multi-source libraries (Immich)**, **filter-based automated
rotation** (Docent has no app-managed slideshow at all — it either relies on the TV's native
shuffle or requires a manual click), **a real database with migrations**, a **typed React UI**, and
**SSE real-time updates** — none of which Docent attempts (and several of which it explicitly rules
out via its "no database, no build step, no auth" guardrails).

## Where the three projects sit relative to each other

- **framegallery** — automated, filter-driven, multi-source (Immich), DB-backed, async, actively
  pushes one image at a time.
- **Docent** — manual/AI-curated, single-source (local + Drive), file-backed, async, defers
  rotation to the TV or the user, with a deep AI layer.
- **frame-close-hauled (frame-sync)** — automated batch sync, cron-driven CLI, uploads ~50 photos
  and lets the TV's native slideshow rotate them, with AI location plaques.

Docent and framegallery share the most infrastructure (async FastAPI + persistent connection);
they diverge on *what the app is for* — Docent curates and identifies art, framegallery automates a
filtered photo slideshow.
