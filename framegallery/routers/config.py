from typing import Annotated

from fastapi import APIRouter, Depends

from framegallery import schemas
from framegallery.dependencies import get_config_repository
from framegallery.repository.config_repository import ConfigKey, ConfigRepository

router = APIRouter(
    prefix="/api/config",
    tags=["config"],
    dependencies=[],
    responses={404: {"description": "Not found"}},
)


@router.get("/active_filter", response_model=schemas.ConfigValue)
def get_active_filter(
    config_repository: Annotated[ConfigRepository, Depends(get_config_repository)],
) -> schemas.ConfigValue:
    """Get the currently active filter."""
    config = config_repository.get(ConfigKey.ACTIVE_FILTER)
    return schemas.ConfigValue(value=config.value if config else None)


@router.post("/active_filter", response_model=schemas.ConfigValue)
def set_active_filter(
    config_value: schemas.ConfigValue, config_repository: Annotated[ConfigRepository, Depends(get_config_repository)]
) -> schemas.ConfigValue:
    """Set the currently active filter."""
    if config_value.value is None:
        config_repository.delete(ConfigKey.ACTIVE_FILTER)
    else:
        config_repository.set(ConfigKey.ACTIVE_FILTER, config_value.value)
    return config_value
