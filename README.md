# Samsung The Frame Gallery

This project is a web application to manage photos for a Samsung The Frame television. It consists of a Python FastAPI backend and a React/TypeScript frontend.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

You need to have [uv](https://github.com/astral-sh/uv) installed. `uv` is an extremely fast Python package installer and resolver, written in Rust.

### Installation

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/slknijnenburg/framegallery.git
    cd framegallery
    ```

2.  **Backend Setup (in `/framegallery`):**

    Navigate to the backend directory:
    ```bash
    cd framegallery
    ```

    Create a virtual environment and install the dependencies:
    ```bash
    uv venv
    uv sync
    ```

3.  **Frontend Setup (in `/ui`):**

    Navigate to the frontend directory from the root:
    ```bash
    cd ui
    ```

    Install the dependencies using your preferred package manager (e.g., `npm`, `yarn`, or `pnpm`):
    ```bash
    npm install
    ```

### Running the application

1.  **Run the backend server:**

    From the `/framegallery` directory, activate the virtual environment and start the FastAPI server:
    ```bash
    uv run uvicorn --port 7999 --reload framegallery.main:app
    ```
    The backend will be running at `http://127.0.0.1:7999`.

2.  **Run the frontend development server:**

    From the `/ui` directory, start the Vite development server:
    ```bash
    npm run dev
    ```
    The frontend will be accessible at `http://localhost:3000` and will proxy API requests to the backend.

### Running the application via Docker

#### Using Pre-built Images from GitHub Container Registry (Recommended)

You can pull and run the latest pre-built image directly from GitHub Container Registry:

```bash
# Pull the latest image
docker pull ghcr.io/slknijnenburg/framegallery:latest

# Create directories for data and images
mkdir -p ./images ./data

# Run the container
docker run -d --name framegallery \
  -p 7999:7999 \
  -v $(pwd)/images:/app/images \
  -v $(pwd)/data:/app/data \
  --env-file .env \
  ghcr.io/slknijnenburg/framegallery:latest
```

Or using Docker Compose:

```bash
# Update docker-compose.yml to use the pre-built image
docker compose up -d
```

#### Building Locally

If you prefer to build the image locally:

```bash
docker build -f Dockerfile -t framegallery:local .
```

Then run it with:
```bash
docker run -it --rm -p 127.0.0.1:7999:7999 -v $(pwd)/images:/app/images -v $(pwd)/data:/app/data framegallery:local
```

#### Configuration

On start-up, the app will import all images from the `images` directory and create a database in the `data` directory.
It will also generate thumbnails for display in the browser for each image, so you'll need to ensure that the images folder is writeable by the container.

Create a `.env` file with your configuration. See `.env.dist` for all available options:

```bash
# Samsung TV Configuration
tv_ip_address=192.168.1.100
tv_port=8002                  # 8002 = TLS + token auth; 8001 = plain WebSockets, no pairing. See "TV port" below
tv_client_name=FrameGallery   # device name registered on the TV; keep stable to avoid re-pairing

# Application Settings
gallery_path="./images"
db_url="sqlite:///./data/framegallery.db"
log_level=INFO
# Log level for the WebSocket libraries (websockets/samsungtvws) driving the TV
# connection. Kept separate from log_level because they emit very noisy
# ping/pong/keepalive messages at DEBUG. Raise to DEBUG only to debug the TV link.
websocket_log_level=WARNING
slideshow_interval=180
filesystem_refresh_interval=600
# Upload-processor strategy for pushing images to the TV (applied at startup —
# restart to change). One of: single_async (default), sync_thread, batch_slideshow.
# Useful for A/B testing which mechanism your TV tolerates without crashing. See
# the "Upload processors" section below.
upload_processor=single_async
# Settle delay (seconds) between consecutive TV commands in the single-image
# processors (single_async/sync_thread). Guards against Art Mode crashing when the
# switch command is sent before the TV has finished digesting the upload. 0 disables.
tv_command_delay=5.0
# Art-mode watchdog: periodically checks whether the TV is reachable and still in art
# mode. See the "Art-mode watchdog" section below.
art_mode_watchdog_enabled=true
art_mode_poll_interval=60

# Docker Volume Mount Paths (customize for your setup)
IMAGES_PATH=./images
DATA_PATH=./data
LOGS_PATH=./logs

# CORS Security Configuration (optional)
# CORS_ALLOW_ALL=true          # Use permissive CORS (less secure, good for development/testing)
# CORS_ORIGINS=http://localhost:3000,http://your-domain.com  # Custom allowed origins
```

#### Docker Volume Configuration

The Docker setup now supports configurable volume mount paths via environment variables:

- `IMAGES_PATH`: Path to your images directory (default: `./images`)
- `DATA_PATH`: Path to application data directory (default: `./data`)
- `LOGS_PATH`: Path to logs directory (default: `./logs`)

Example with custom paths:
```bash
# In your .env file
IMAGES_PATH=/home/user/photos
DATA_PATH=/home/user/framegallery-data
LOGS_PATH=/var/log/framegallery

# Then run normally
docker compose up -d
```

#### Log Rotation

Logs are written to two places, and both are capped so they cannot grow without bound:

- `$LOGS_PATH/framegallery.log` is rotated by the application at midnight UTC, keeping 7 days of history (`framegallery.log.YYYY-MM-DD`).
- The container's stdout is captured by Docker and capped by the `logging` options in `docker-compose.yml` (7 files of 20 MB).

Note that the Docker-side limits only apply when the container is **recreated** (`docker compose up -d`); `docker compose restart` reuses the existing container and its current log settings.

Running at `log_level=DEBUG` produces roughly 15k lines per day, the bulk of it HTTP client chatter from `httpcore`/`urllib3`. Set `log_level=INFO` to reduce this substantially; `websocket_log_level` remains a separate knob so the TV connection can still be debugged independently.

#### TV port

`tv_port` selects the whole transport, not just the port number. `samsungtvws` derives
everything from it:

| | `8002` (default) | `8001` |
|---|---|---|
| WebSocket | `wss://` | `ws://` |
| Auth | token in the URL | none |
| Pairing | one-time "Allow" prompt on the TV | not required, and skipped automatically |
| REST probe | `https` | `http` |

Both are served by current Frame firmware — 8001 is not a legacy-only option. Switching is
a one-line change; the app detects that 8001 needs no token and skips pairing. Note that
8001 is unencrypted and unauthenticated on your LAN.

**Why you might switch.** Some Frames abort uploads by closing the WebSocket with status
1005, which surfaces as:

```
sync_thread: TV op 'upload local:1234' failed: ('Invalid close opcode %r', 1005)
```

1005 is reserved by RFC 6455 and must never appear on the wire, so the TV is sending a
malformed close frame. On at least one 2023 Frame (`QE32LS03CBUXXN`) these failures were
frequent on 8002 and absent on 8001 across a same-window comparison, which suggests they
relate to the token-authenticated channel rather than to uploading itself. The sample was
small, so treat 8001 as an experiment worth measuring rather than a guaranteed fix: switch,
then compare `grep -c "upload failed for" logs/framegallery.log` over a day.

#### Database Migrations

In case changes were made to the database schema, migrations will need to be executed manually when running the updated container:

```bash
docker run -it --rm -v $(pwd)/images:/app/images -v $(pwd)/data:/app/data ghcr.io/slknijnenburg/framegallery:latest uv run alembic upgrade head
```

#### Available Image Tags

- `latest` - Latest stable release from the main branch
- `main` - Latest development build from the main branch
- `v1.0.0` - Specific version tags (when available)

#### Image configuration

The Frame's aspect ratio is 16:9.  Images with these dimensions can be configured with any matte.
Images with an aspect ratio of 3:2 (e.g. 1920x1280) can also be configured with a matte. When using "none" the image will be slightly cropped to 1920x1080.
Images with an aspect ratio of 4:3 (e.g. 1920x1440) can also be configured with a matte. When using "none" the image will be cropped to 1920x1080

It actually seems you can select any matte style for any image, as long the slideshow mode is disabled.

## Upload processors

The way images are pushed to the TV is pluggable, selected at startup with the `upload_processor`
setting (restart to apply).
This exists mainly as a diagnostic tool: some Frame TVs crash in Art Mode during uploads/photo
changes, and switching the mechanism helps isolate the cause.

| `upload_processor` | Behaviour |
|---|---|
| `single_async` (default) | Persistent async WebSocket. On each slideshow tick, uploads one image, activates it, and deletes the previously-active image. |
| `sync_thread` | Same one-image-at-a-time behaviour, but via the synchronous `samsungtvws` client run in a background thread, with idle-connection recycling, Wake-on-LAN before retry, and bounded retries. |
| `batch_slideshow` | Uploads a batch of images to the TV once and hands rotation to the TV's own slideshow; the app stops pushing an image every interval. |

If you experience TV crashes, try switching from `single_async` to `sync_thread` (or
`batch_slideshow`) and observe whether the crashes stop.

Related settings:

| Variable | Default | Applies to | Description |
|---|---|---|---|
| `tv_mac_address` | *(unset)* | `sync_thread` | TV MAC address; when set, a Wake-on-LAN packet is sent before retrying a failed connection (`arp -n <tv-ip>` to find it). |
| `tv_command_delay` | `5.0` | `single_async`, `sync_thread` | Settle delay in seconds inserted between consecutive TV commands: after `upload` before `select_image`, and before deleting the previous image. The Frame needs a moment to finish digesting an upload before it reliably accepts the next command; issuing them back-to-back can crash Art Mode back to regular TV. Set to `0` for the original back-to-back behaviour. |
| `batch_size` | `50` | `batch_slideshow` | How many images to upload to the TV in one batch. |
| `batch_rotation_minutes` | `3` | `batch_slideshow` | The TV's own rotation interval, in whole minutes (the TV API only accepts minutes, so `slideshow_interval` does not apply in this mode). |

In `batch_slideshow` mode the app-driven slideshow loop and the TV auto-cleanup service are
both suppressed, since the TV owns rotation and the processor manages its own batch.

### Images left on the TV

The single-image processors upload a photo, activate it, and delete the one it replaced,
so the TV should only ever hold one of our images. Every image uploaded is tracked in the
database (`latest_tv_content_id`, `pending_tv_deletions`) until the TV confirms it is gone:

- **Tracking is persisted**, so a restart does not abandon whichever image was live at the
  time. This was the largest source of leaks: each restart used to strand one image on the
  TV with nothing able to identify or delete it.
- **A new image is recorded before it is activated**, so a failed `select_image` or delete
  cannot leave it untracked.
- **Failed deletes stay queued** and are retried on the next slideshow tick, in a single
  batched `delete_list` call rather than one command per image.
- **Uploads are never retried.** `upload()` streams the whole image and only then waits for
  the TV's reply, so a timeout usually means the TV *has* the image but we never learned
  its id. Retrying re-sends it, turning one failed cycle into several untracked copies.

Anything that still slips through — including images left by older versions — is swept up
by the **TV Auto-cleanup** service on the Settings page, which keeps only the most recent
few files. Use **Run Cleanup Now** there to clear an existing backlog in one go.

## Art-mode Watchdog

The Frame leaves art mode for two very different reasons: somebody picks up the remote to
watch television, or the art system crashes and the TV falls back to regular TV (typically
Samsung TV Plus). Both look identical from the outside — `get_artmode` simply reports `off`.

The watchdog therefore does **not** try to guess which happened. It probes on an interval and:

- **Pauses slideshow pushes** while art mode is off. Uploads are invisible on regular TV, and
  issuing them is itself a common way to wedge the Frame. Pushing resumes automatically when
  art mode comes back — i.e. when you finish watching and switch back.
- **Detects a wedged art channel and rebuilds the connection.** It probes power state over
  REST (`/api/v2/`, a plain HTTP GET) *separately* from the art WebSocket. That is what
  distinguishes "the TV is fine but art mode has crashed" from "the TV is gone entirely" —
  a distinction ICMP cannot make, since a Frame in standby still answers ping.

| Health | Meaning |
|---|---|
| `art_on` | Reachable and displaying art. The normal state. |
| `tv_mode` | Reachable, art mode off. Someone is watching TV, or art mode crashed. |
| `standby` | Reachable but powered down. Normal overnight. |
| `art_unavailable` | REST answers but the art channel does not — the art system has wedged. |
| `unreachable` | No response at all: powered off, rebooting, or off the network. |

**Art mode is only forced back on immediately after our own writes.** After each
upload/select/delete sequence the processor re-checks art mode; finding it off at that
moment means *we* knocked the TV out of it, so restoring cannot be fighting a person who
just reached for the remote. The periodic poll deliberately never restores art mode.

The trade-off: an art-mode crash that happens *between* writes is indistinguishable from
someone watching TV, so the Frame will stay on regular TV until you switch it back. Making
the poll restore art mode too would close that gap at the cost of overriding you every time
you sit down to watch something.

| Variable | Default | Description |
|---|---|---|
| `art_mode_watchdog_enabled` | `true` | Enable the watchdog. With it off, nothing observes art mode and `/api/status` reports the art-mode fields as unknown. |
| `art_mode_poll_interval` | `60` | Seconds between probes. |

### TV Watch Mode

The **Settings** page has a **TV Watch Mode** toggle for when you want to watch television
and be certain the app will not interfere. While it is on:

- no images are pushed to the TV at all, and
- art mode is **never** restored — including immediately after our own writes, the one
  case where the app would otherwise be confident it should intervene.

It is checked *before* the art-mode state, so it does not depend on art-mode detection
being accurate or up to date. Turn it off and the slideshow resumes on the next tick.

This is a runtime setting stored in the database (`tv_watch_mode_enabled`), not an
environment variable, so it can be toggled without a restart. It is also available at
`GET`/`POST /api/config/tv_watch_mode_enabled`.

## Photo Libraries

The slideshow can draw photos from multiple **libraries** at once, managed on the **Libraries** page.

- **Local Gallery** — the always-present default library, backed by the `images/` folder and the SQLite database.
Its selection is controlled by the active filter (configured on the Filters page).
- **Immich** — one or more external [Immich](https://immich.app) servers.
Add one on the Libraries page by entering the server's base URL (e.g. `http://immich.local:2283`) and an API key,
testing the connection, and selecting one or more albums.

Each enabled library has a **weight**.
The slideshow picks a source with probability proportional to `weight × (number of matching photos)`,
so with equal weights every photo across all libraries is equally likely (a true random pick over the union).
Increase a library's weight to make it appear more often relative to its size.

External photos are fetched **on demand**: when a photo is chosen, its bytes are downloaded from the source
just-in-time and uploaded to the TV. Nothing is mirrored locally. If a library is unreachable, it is skipped for
that tick and the slideshow continues with the other libraries.

Each library on the Libraries page shows a live status chip — its number of matching photos, `0 matching photos`,
or `Unavailable: …` when the server can't be reached. A warning banner appears when no enabled library has any
photos, so the "nothing to display" condition is visible in the UI rather than only in the server logs.

### Immich API keys

Create an API key in Immich under *Account Settings → API Keys*. It needs read access to albums and assets plus the
ability to download originals:

| Permission | Used for |
|---|---|
| `album.read` | Listing albums and reading album contents |
| `asset.read` | Reading asset metadata (dimensions, filename) |
| `asset.download` | Downloading the original photo to send to the TV |
| `server.about` | Reporting the Immich version on "Test connection" (optional) |

The minimal set is `album.read`, `asset.read`, `asset.download`. An unrestricted key also works. (Immich versions
older than ~v1.118 have all-or-nothing keys, so any valid key works there.)

The key is stored in the application's SQLite database (in the mounted `data/` volume, alongside the TV auth token)
and is **never returned by the API** — treat the `data/` directory as sensitive. Because it is stored, you don't
need to re-enter it to change a library's album selection: opening a saved library reloads its albums with the
stored key, and you only type a key when you want to rotate it.

Crop and matte editing are only available for local images; external photos are displayed as-is (16:9 photos
without a matte, others with a shadowbox).

### How album selection works with Immich

Recent Immich releases stopped embedding assets in `GET /api/albums/{id}`, so album contents are enumerated with
`POST /api/search/metadata` (paged), and the union across the selected albums is de-duplicated. A random asset is
chosen client-side rather than via Immich's `/search/random`, which has been unreliable across releases.
