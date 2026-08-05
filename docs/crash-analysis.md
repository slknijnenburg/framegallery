# Art-mode crash and upload-failure analysis

Status as of August 2026.
This documents a multi-week investigation into two related problems observed on a 2023 32" Frame (`QE32LS03CBUXXN`, 1080p panel): roughly a third of image uploads fail, and Art Mode crashes back to regular TV a few times a day.
It exists so the conclusions — several of which invalidated earlier assumptions — don't have to be re-derived, and so the open leads are written down.

## How an upload actually works

The image bytes never travel over the WebSocket.
`samsungtvws` art `upload()` performs a four-step dance:

1. Send a `send_image` **announcement** over the art WebSocket (`com.samsung.art-app`), containing only `file_type`, `file_size`, `matte_id`, and a date — no pixels.
2. Wait for the TV to reply `ready_to_use` with an ip/port/key for a **separate raw TCP socket**.
3. Stream the image bytes over that TCP socket in 64 KB chunks (TLS-wrapped when the TV asks for it).
4. Wait back on the WebSocket for `image_added`, which carries the new `content_id`.

Any analysis of upload failures has to say *which step* failed; they have very different meanings.

## Finding 1: the port does not matter

Both `wss://:8002` (TLS + token) and `ws://:8001` (plain, no auth) are served by current Frame firmware.
A full day of production traffic on each port — several hundred uploads per day, identical conditions — produced statistically identical failure rates (roughly a third on both).
The only difference is how the failure surfaces: `Invalid close opcode 1005` (a malformed close frame) on 8002 becomes `[Errno 32] Broken pipe` on 8001.
Same event, different transport error.

Two earlier recommendations were made from ~20-upload samples and both were wrong, one costing a working display for an evening.
**A full day of data is the minimum for any claim about upload reliability.**

## Finding 2: there are two distinct failure classes

Classifying every upload-failure traceback from two full days (153 failures across 465 attempts, one day per port):

| Failure point | Count | Meaning |
|---|---|---|
| Step 2 — waiting for `ready_to_use` | ~90% | The TV kills the WebSocket in response to the announcement, **before any image byte is sent** |
| Step 3 — during the byte stream | 0 | Never observed |
| Step 4 — waiting for `image_added` | ~10% | Bytes fully delivered; the TV didn't confirm within the 10 s socket timeout |

### Class A: the ~30% announcement kill (unsolved)

The TV slams the art channel shut the moment it is asked to open a file-transfer socket, roughly 1 in 3 times.
Evidence that this is **not** image-related:

- It fires before the TV has seen a single pixel.
- The local gallery is homogeneous (all JPEG, 1–3 MB, <8 MP) and fails at a flat ~30% with mixed per-image outcomes — the same image succeeds and fails on different attempts, in proportions matching an independent coin flip.
- `get_artmode` requests run over equally cold connections (the watchdog poll always exceeds the 30 s idle-recycle) and fail only ~2–3% of the time.

So it is not the port, not the connection freshness, not the payload — it is the `send_image`/d2d request *specifically* that the TV's art service intermittently answers by dying.
This looks like Frame firmware behaviour and is the remaining mystery.
It is also the prime suspect for the Art Mode crashes, since a dying art service and an Art Mode crash are plausibly the same underlying event.

### Class B: big payloads time out after delivery (fixed)

Libraries that serve original files (Immich) were sending full-resolution phone photos — 3–13 MB, up to 32 MP — to a 1080p panel.
Every 32 MP original failed on every attempt (11/11 over two days), all in step 4: the bytes arrived, but the TV needs more than 10 seconds to ingest a large JPEG, and the client's 10 s socket timeout expired first.
Upstream users report confirmations taking 30+ seconds for large files.
Worse, the TV usually *had* added the image, so each of these stranded an untracked orphan for the cleanup service.

Fixed two ways (August 2026):

- **Upload normalization**: every payload is downscaled to fit `upload_max_width` x `upload_max_height` (default 1920x1080 — the 32" panel is 1080p, so 4K payloads are pure overhead) and re-encoded as JPEG; EXIF rotation is baked in; already-fitting JPEGs pass through untouched.
- **`sync_thread` widens the socket timeout to 60 s for the upload op only** (`UPLOAD_CONFIRM_TIMEOUT`), so a slow confirmation is awaited rather than abandoned; `single_async` already passed `timeout=60`.

Each upload now logs one `Upload payload for ...` line with the exact size/dimensions sent, so future failure/size correlations are answerable from the log alone.
Setting `upload_debug_keep=N` additionally keeps the last N exact payloads in `$DATA_PATH/upload_debug/`.

## Finding 3: the TV wedge

Independent of uploads, the art service wedges hard a few times a day: REST (`/api/v2/`) keeps answering on both ports, the WebSocket still accepts connections and sends `ms.channel.connect`, but `ms.channel.ready` never arrives.
It sometimes clears itself in 5–10 minutes; otherwise the remote or a power cycle is needed.
The watchdog detects this state (`art_unavailable`) and recycles the connection, which recovers everything recoverable from our side.

## API-version notes (Frame generations)

- **API 2.x** (≤2020 models): different request names (`get_api_version` vs `api_version`, `auto_rotation` vs `slideshow`).
- **API 4.x** (2021–22): the current mechanism — `send_image` announcement + separate d2d TCP socket; `request_id` must accompany `id`.
- **2022 (LS03B)**: the art WebSocket API was removed by firmware, then restored in firmware 1622 with renamed commands.
- **API 5.x** (2023+ models, reported as `5.0.1.0`): the upload mechanism is unchanged, but *event* payloads renamed `value` to `status` (`artmode_status` events). Upstream `samsung-tv-ws-api` fixed this in Dec 2025 (commit `f821d0d2`); our fork (v3.0.5) predates that fix. It only affects the async client's event tracking, so it is dormant while `sync_thread` is in use — but it must be pulled in before relying on `single_async` event handling.
- **2025 non-Pro Frames**: reported JPEG-only for uploads (one more reason normalization always re-encodes to JPEG).

## Follow-up leads

1. **Warm-channel experiment against class A** *(implemented, results pending)*.
   Every upload used to ride a brand-new connection: the 30 s idle-recycle always fires between 180 s slideshow ticks.
   Both mature TypeScript implementations (`balmli/com.samsung.smart`, `tavicu/homebridge-samsung-tizen`) instead hold one persistent socket with a keepalive.
   The `tv_keepalive_interval` setting (August 2026) sends a WebSocket ping whenever the `sync_thread` connection has been idle that many seconds and disables the idle-recycle, so uploads run on a long-lived connection.
   Note the ping only *sends*; no pong is awaited, so a "successful" ping proves the socket accepted the bytes, not that the TV is healthy — a dead peer still surfaces on the next real op, which owns reconnection.
   Judgement criteria: a full day with `tv_keepalive_interval=15`, comparing the announcement-kill rate (failures at the `ready_to_use` wait) against the ~30% baseline.
   A fallback variant if the ping alone changes nothing: send one benign art request before `send_image`.
2. **Trial the `single_async` processor.**
   The upstream maintainer states the async art interface "works much better than the sync interface".
   Prerequisites: pull upstream commit `f821d0d2` (API 5.x event fix) into the fork, then a full-day A/B against `sync_thread`.
   While there, log `get_api_version` at connect time — we currently assume rather than know what the TV reports (the hardcoded `4.3.4.0` in `processors/base.py` is likely wrong for 2023+ models).

## Ground rules learned the hard way

- One day of data (hundreds of uploads) is the minimum sample for any reliability claim; every short-sample conclusion made during this investigation was wrong.
- Classify failures by *where* in the four-step upload they occur before theorising; "upload failed" conflates at least two unrelated phenomena.
- A second art-channel client disrupts the first (`clientConnect`/`clientDisconnect` are treated as fatal), so live probing alongside the running app contaminates both measurements.
