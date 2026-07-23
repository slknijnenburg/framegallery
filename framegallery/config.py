from pydantic_settings import BaseSettings, SettingsConfigDict

from framegallery.logging_config import setup_logging


class Settings(BaseSettings):
    """Settings for the Frame Gallery app."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "Frame Gallery"
    tv_ip_address: str = "192.168.2.76"
    tv_port: int = 8002
    # Client identity registered on the TV and granted the auth token. Must stay
    # constant across restarts; change it only if you want the TV to re-pair
    # (a new "Allow" prompt) under a different device name.
    tv_client_name: str = "FrameGallery"
    gallery_path: str = "./images"
    db_url: str = "sqlite:///./data/framegallery.db"
    filesystem_refresh_interval: int = 600
    slideshow_interval: int = 180
    log_level: str = "DEBUG"
    # Log level for the WebSocket libraries (``websockets``/``samsungtvws``) that
    # power the Samsung Frame connection. Kept separate from ``log_level`` because
    # they emit very noisy ping/pong/keepalive messages at DEBUG. Raise to DEBUG
    # only when debugging the TV connection.
    websocket_log_level: str = "WARNING"
    images_path: str = "./images"
    data_path: str = "./data"
    logs_path: str = "./logs"
    # Which upload-processor strategy to use for pushing images to the TV. One of
    # "single_async" (default; async WebSocket, one image at a time), "sync_thread"
    # (synchronous client in a thread, with idle-recycle/Wake-on-LAN/retries), or
    # "batch_slideshow" (upload a batch once and let the TV rotate them). Applied at
    # startup; change it and restart to A/B test which mechanism the TV tolerates.
    upload_processor: str = "single_async"
    # TV MAC address, used by the "sync_thread" processor to send a Wake-on-LAN
    # packet before retrying a failed connection. Optional; find it with
    # `arp -n <tv-ip>`. Only helps when the TV is asleep, not for art-mode crashes.
    tv_mac_address: str | None = None
    # Settle delay (seconds) inserted between consecutive TV commands in the
    # single-image processors (single_async / sync_thread): after upload before
    # select_image, and before deleting the previous image. The Frame needs a moment
    # to finish digesting an upload before it reliably accepts the follow-up command;
    # issuing them back-to-back can crash Art Mode back to regular TV. Set to 0 to
    # disable (original back-to-back behaviour).
    tv_command_delay: float = 5.0
    # "batch_slideshow" processor: how many images to upload to the TV in one batch,
    # and the TV's own rotation interval in whole minutes (the TV API only accepts
    # minutes, so the 180s slideshow_interval doesn't apply in this mode).
    batch_size: int = 50
    batch_rotation_minutes: int = 3

    @property
    def database_path(self) -> str:
        """Extract the database file path from the database URL."""
        if self.db_url.startswith("sqlite:///"):
            return self.db_url[10:]  # Remove "sqlite:///" prefix
        msg = f"Unsupported database URL format: {self.db_url}"
        raise ValueError(msg)


settings = Settings()

logger = setup_logging(
    log_level=settings.log_level,
    websocket_log_level=settings.websocket_log_level,
    logs_path=settings.logs_path,
)
logger.warning("Settings at boot: %s", settings.model_dump())
