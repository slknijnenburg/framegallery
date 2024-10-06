# Samsung The Frame Gallery

Python project to manage a Samsung The Frame TV as a digital frame and (photo) gallery.

## Running from source

### Requirements

- Python 3.10 or higher
- Poetry
- NodeJS 16 or higher

Run the following commands to install the required dependencies:

```bash
poetry install
cd ui && npm install
```

### Running the project

To run the project, you need to start the backend and the frontend separately:

```bash
poetry run uvicorn framegallery.main:app --reload --port 7999
cd ui && npm start
```