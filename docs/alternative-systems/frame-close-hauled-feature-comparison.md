# frame-sync (close-hauled/frame) vs. framegallery

A feature and architecture comparison against the open-source
[`close-hauled/frame`](https://gitlab.com/close-hauled/frame) project (aka "frame-sync"),
which targets the same goal as framegallery: displaying a personal photo library on a
Samsung "The Frame" TV in Art Mode.

Analysis performed 2026-07-15 against the `master` branch of the GitLab repository.

## What it is, in one line

`frame-sync` is a **cron-driven Python CLI** that periodically uploads a rotating batch of
~50 processed photos into the TV's own internal storage and lets *the TV's built-in
slideshow* cycle them, with a thin Flask web UI bolted on for monitoring and manual control.

That is a fundamentally different architecture from framegallery, which is a **long-running
async service** that pushes one active image at a time on its own timer.

## Feature overview of frame-sync

| Area | What it does |
|---|---|
| **Core model** | Keeps an ordered `playlist` in `state.json`; each run evicts photos the TV has already cycled past and refills the TV back up to 50, so with N photos each gets ~`50/N` of the display time |
| **Rotation** | The **TV's** native slideshow rotates the 50 resident images; the app only swaps the *set* of 50 on a schedule and re-asserts rotation at the end of each run |
| **TV-progress-aware eviction** | Calls `get_current()` to see what's on screen, evicts only already-seen photos, keeps the current one to avoid a mid-display jump |
| **AI location lookup** | For photos with no GPS EXIF, sends the image to **Claude Sonnet (vision)** to identify the location; cached by file hash in `location_cache.json` |
| **Location/date plaques** | Composites a silver "location + date" plaque onto each photo before upload; manual `--set-location` / `--set-date` overrides, re-uploaded on the spot |
| **Image prep** | EXIF-transpose, landscape → cover-crop to 3840×2160, portrait → scaled to height with `shadowbox_polar` matte |
| **Web UI (Flask + Gunicorn)** | Dashboard, Now Playing (edit location/date), On TV (the 50-window), Library (Push / Add to frame), Upload, Years histogram, History, Rotate-with-live-log |
| **Ops** | One-shot CLI (`--yes` for cron), `--evict-all`, `--ensure-rotation` watchdog, `--preview`, systemd unit, Docker, reverse-proxy configs |
| **State files** | `state.json`, `hash_index.json`, `location_cache.json`, `date_cache.json`, `year_cache.json`, `.tv_token` |
| **Security posture** | Explicitly **no auth** — meant to sit behind a reverse proxy on a trusted LAN |

## How frame-sync manages the TV connection

- **Library:** upstream **`samsungtvws>=3.0.0`** (PyPI, not forked), the **synchronous**
  `SamsungTVArt`.
  But it subclasses it as `FrameTVArt(SamsungTVArt)` to patch firmware quirks — effectively a
  "fork by subclass."
- **Sync, per-invocation:** each CLI run creates one `FrameTVArt(host, token_file,
  timeout=30)`, reuses it for that run, and never explicitly closes it — the process just
  exits.
  No daemon, no persistent socket between runs.
- **Pairing:** delegated entirely to the library via `token_file=.tv_token`; first run pops
  the "Allow" prompt, later runs are silent.
- **Reliability is defensive, not connective:**
  - Uploads run in a `ThreadPoolExecutor(max_workers=1)` with a hard **120 s timeout** plus a
    heartbeat-logging thread.
  - Retries up to **3×** on `BrokenPipeError`, re-creating the connection object each time.
  - Overrides `get_api_version()` to a no-op (the real call *hangs* because the TV's 6-second
    keepalive pings reset the socket timeout).
  - `set_slideshow_status` / `set_auto_rotation_status` are **fire-and-forget** (TV returns
    error −7 / no reply).
  - Rewrote `_wait_for_d2d()` to treat `notify.sync_server` `status=="finish"` as
    upload-complete (the stock `image_added` event never arrives on this firmware).
- **Content tracking:** a persistent **hash → content_id map** in `state.json`, and it
  discovers each upload's `content_id` by diffing the TV art list before/after the upload
  (the firmware doesn't return it).
- **TV off/asleep:** no active power management; swallows errors and returns empty.
  A separate `--ensure-rotation` watchdog crontab re-enables the slideshow if the TV gets
  stuck, with a 12h anti-spam cooldown.

## How framegallery differs

| Dimension | frame-sync | framegallery |
|---|---|---|
| **Runtime shape** | One-shot CLI on cron + optional Flask UI | Always-on **async FastAPI** service; slideshow is an internal asyncio task |
| **samsungtvws** | Upstream sync `SamsungTVArt`, patched via subclass | **Own git fork**, async `SamsungTVAsyncArt` + `SamsungTVWSAsyncRemote` |
| **Connection** | Sync, rebuilt per run, never closed | **Persistent** websocket; `start_listening()` + push callbacks (`go_to_standby`) |
| **What drives rotation** | **The TV's** native slideshow rotates 50 resident images | **The app** pushes one active image every `slideshow_interval` (180 s) and lets the TV just display it |
| **Images on the TV** | ~50 uploaded and resident at once | Essentially **one at a time** — upload → activate → delete the previous `content_id` (plus a cleanup service keeping the last 3) |
| **Image source** | Local disk only | Pluggable **libraries** — local SQLite gallery **+ Immich** (streamed originals), blended with count-proportional weighting |
| **Selection** | Fair round-robin playlist cursor + shuffle | **Filter-driven** (react-querybuilder filters) + weighted-random across libraries |
| **Reconnect** | 3× retry on broken pipe, per run | Continuous **ICMP ping** loop re-arms on disconnect; reconnect on `go_to_standby` |
| **Pairing quirk handled** | `get_api_version` hang; fire-and-forget slideshow | Recent firmware won't pair on the art channel → pairs on the **remote channel first**, reuses token for art channel |
| **Metadata / plaques** | AI location lookup, composited plaques, Years histogram | None of this — no plaques, no AI, no capture-year UI |
| **Matte** | `shadowbox_polar` for portrait, `none` landscape | `none` for 16:9, `shadowbox_black` otherwise; crop pipeline for 3:2 / 4:3 |
| **Real-time UI** | Poll/refresh; live log on Rotate page | **SSE** (`/api/slideshow/events`) pushes updates to the React app |
| **Auth** | None (by design) | None either — same "trusted LAN" posture |

## Ideas from frame-sync worth considering for framegallery

A few things they do that framegallery genuinely lacks:

1. **AI location + date plaques** — the standout feature.
   Claude Sonnet vision fills in locations for photos with no GPS, cached by file hash,
   composited as a plaque.
   This is a real product differentiator framegallery does not have.
2. **Years histogram / capture-year browsing** — a nice library-navigation feature.
3. **Fairness accounting** — they track per-photo upload counts (`rotation_stats.json`) so you
   can audit that every photo gets equal time.
   framegallery's weighted-random `pick_photo()` gives no such guarantee (a photo can be
   picked twice in a row or starved).
4. **A rotation watchdog** — their `--ensure-rotation` recovers a stuck TV.
   framegallery's equivalent risk is different (it pushes actively), but it is a reminder that
   the Frame drops out of the expected state and needs re-asserting.

Conversely, framegallery is architecturally ahead on **multi-source libraries (Immich)**,
**persistent async connection**, **filter-based selection**, and **SSE real-time updates** —
all things frame-sync does not attempt.

One thing worth flagging: their "let the TV run its own slideshow over 50 resident images"
model is much gentler on the TV (one batch upload per night vs. framegallery re-uploading
every 180 s and deleting).
If wear-and-tear or reliability issues ever show up from constant upload/delete churn, their
model is the proven alternative.
