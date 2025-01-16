import json
from typing import Optional

from sqlalchemy import BinaryExpression, delete, func, select
from sqlalchemy.orm import Session

from framegallery.models import Config, Image

# @TODO make Key an Enum/class
class ConfigRepository:
    def __init__(self, db: Session):
        self._db = db

    def get(self, key: str) -> Optional[Config]:
        stmt = select(Config).where(Config.key == key)

        return self._db.execute(stmt).scalar_one_or_none()

    def get_or(self, key: str, default_value = None) -> Config:
        value_from_db = self.get(key)
        if value_from_db is None:
            return Config(key=key, value=default_value)

        return value_from_db

    def set(self, key: str, value) -> Config:
        config = self.get_or(key)

        # if value is a string, store it directly, otherwise json encode it
        if isinstance(value, str):
            config.value = value
        else:
            config.value = json.dumps(value)

        self._db.add(config)
        self._db.commit()

        return config

    def delete(self, key: str) -> None:
        stmt = delete(Config).where(Config.key == key)
        self._db.execute(stmt)
        self._db.commit()

    def has(self, key: str) -> bool:
        return self.get(key) is not None
