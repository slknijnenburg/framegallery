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

### Importing your images

To import your image, you can put them in the `./images` folder. 
You can use a subfolder structure if you want to, all files will be sent to the TV.

To start the upload synchronization, you can run the following command from the root folder of the project.

```bash
poetry run python3 -m framegallery.importer.importer
```

#### Image configuration

The Frame's aspect ratio is 16:9.  Images with these dimensions can be configured with any matte.
Images with an aspect ratio of 3:2 (e.g. 1920x1280) can also be configured with a matte. When using "none" the image will be slightly cropped to 1920x1080.
Images with an aspect ratio of 4:3 (e.g. 1920x1440) can also be configured with a matte. When using "none" the image will be cropped to 1920x1080

It actually seems you can select any matte style for any image, as long the slideshow mode is disabled.