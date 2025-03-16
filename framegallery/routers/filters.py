from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from framegallery import schemas
from framegallery.dependencies import get_filter_repository
from framegallery.models import Filter
from framegallery.repository.filter_repository import FilterRepository

router = APIRouter(
    prefix="/filters",
    tags=["filters"],
    dependencies=[],
    responses={404: {"description": "Not found"}},
)

@router.post("/", response_model=Filter)
def create_filter(filter_to_create: schemas.FilterCreate,
                  filter_repository: Annotated[FilterRepository, Depends(get_filter_repository)]) -> schemas.Filter:
    """Add a new filter to the database."""
    return filter_repository.create_filter(name=filter_to_create.name, query=filter_to_create.query)

@router.get("/", response_model=list[schemas.Filter])
def read_filters(filter_repository: Annotated[FilterRepository, Depends(get_filter_repository)],
                 skip: int = 0, limit: int = 100
                 ) -> Sequence[schemas.Filter]:
    """Get all filters from the database."""
    return filter_repository.get_filters(skip=skip, limit=limit)

@router.get("/{filter_id}", response_model=schemas.Filter)
def read_filter(filter_id: int,
                filter_repository: Annotated[FilterRepository, Depends(get_filter_repository)]
                ) -> schemas.Filter:
    """Get a filter by its ID."""
    db_filter = filter_repository.get_filter(filter_id)
    if db_filter is None:
        raise HTTPException(status_code=404, detail="Filter not found")
    return db_filter

@router.put("/{filter_id}", response_model=schemas.Filter)
def update_filter(
        filter_id: int,
        updated_filter: schemas.FilterUpdate,
        filter_repository: Annotated[FilterRepository, Depends(get_filter_repository)]
) -> schemas.Filter:
    """Update a filter by its ID."""
    db_filter = filter_repository.get_filter(filter_id=filter_id)

    if db_filter is None:
        raise HTTPException(status_code=404, detail="Filter not found")

    db_filter.name = updated_filter.name
    db_filter.query = updated_filter.query

    return filter_repository.update_filter(filter_to_update=db_filter, filter_id=filter_id)

@router.delete("/{filter_id}")
def delete_filter(
        filter_id: int,
        filter_repository: Annotated[FilterRepository, Depends(get_filter_repository)]
) -> None:
    """Delete a filter by its ID."""
    db_filter = filter_repository.get_filter(filter_id=filter_id)
    if db_filter is None:
        raise HTTPException(status_code=404, detail="Filter not found")

    filter_repository.delete_filter(filter_id=filter_id)
