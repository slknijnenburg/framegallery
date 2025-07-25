import logging

from blinker import signal

from framegallery.models import Filter, Image
from framegallery.repository.config_repository import ConfigKey, ConfigRepository
from framegallery.repository.filter_repository import FilterRepository
from framegallery.repository.filters.query_builder import QueryBuilder
from framegallery.repository.image_repository import ImageRepository, NoImagesError

logger = logging.getLogger("framegallery")


class Slideshow:
    """A class that manages the active image in the slideshow."""

    def __init__(
        self,
        image_repository: ImageRepository,
        config_repository: ConfigRepository,
        filter_repository: FilterRepository,
    ) -> None:
        self._active_image = None
        self._image_repository = image_repository
        self._config_repository = config_repository
        self._filter_repository = filter_repository

    async def update_slideshow(self) -> Image:
        """Update the slideshow with a new image that matches the active filter."""
        active_filter = self._get_active_filter()

        if active_filter is None:
            logger.debug("No active filter")
        else:
            logger.debug("Active filter: %s", active_filter.query)

        query_builder = QueryBuilder(active_filter.query) if active_filter is not None else None
        query_expression = query_builder.build() if query_builder is not None else None
        image = self._image_repository.get_image_matching_filter(query_expression)

        if image is None:
            raise NoImagesError

        logger.debug("Updating slideshow with image: %s", image.filepath)
        await self.set_slideshow_active_image(image)
        return image

    def _get_active_filter(self) -> Filter | None:
        active_filter_id = self._config_repository.get(ConfigKey.ACTIVE_FILTER)
        if active_filter_id is None:
            return None

        return self._filter_repository.get_filter(int(active_filter_id.value))

    async def set_slideshow_active_image(self, image: Image) -> None:
        """
        Send a signal that the active image has been updated,
        so that other parts of the system can react to that.
        """
        self._active_image = image
        active_image_updated = signal("active_image_updated")
        await active_image_updated.send_async(self, active_image=self._active_image)

        logger.info("Active image: %s", self._active_image.filepath)
