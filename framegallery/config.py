from pydantic import BaseSettings

class Settings(BaseSettings):
    app_name: str = "Frame Gallery"
    ip_address: str = "192.168.2.76"

    class Config:
        env_file = ".env"

settings = Settings()