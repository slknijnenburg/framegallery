import logging

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings for the Frame Gallery application."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "Frame Gallery"
    tv_ip_address: str = "192.168.2.76"
    tv_port: int = 8002
    gallery_path: str = "./images"
    db_url: str = "sqlite:///./data/framegallery.db"
    filesystem_refresh_interval: int = 600
    slideshow_interval: int = 180
    log_level: str = "DEBUG"


settings = Settings()

logging.warning("Settings at boot: %s", settings.model_dump())
