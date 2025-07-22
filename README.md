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
docker-compose up -d
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

Create a `.env` file with your Samsung TV configuration:
```bash
TV_IP_ADDRESS=192.168.1.100
TV_PORT=8002
GALLERY_PATH=/app/images
```

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