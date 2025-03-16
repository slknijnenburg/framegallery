from fastapi import APIRouter, Depends, HTTPException

from models import Filter
from repository.filter_repository import FilterRepository

router = APIRouter(
    prefix="/filters",
    tags=["filters"],
    dependencies=[],
    responses={404: {"description": "Not found"}},
)

from sqlalchemy.orm import Session
from typing import List
from .. import crud, schemas

@router.post("/", response_model=Filter)
def create_filter(filter: schemas.FilterCreate, filter_repository: FilterRepository =  Depends(get_filterrepository)):
    filter_repository
    return crud.create_filter(db=db, filter=filter)

@router.get("/", response_model=List[schemas.Filter])
def read_filters(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    filters = crud.get_filters(db, skip=skip, limit=limit)
    return filters

@router.get("/{filter_id}", response_model=schemas.Filter)
def read_filter(filter_id: int, db: Session = Depends(get_db)):
    db_filter = crud.get_filter(db, filter_id=filter_id)
    if db_filter is None:
        raise HTTPException(status_code=404, detail="Filter not found")
    return db_filter

@router.put("/{filter_id}", response_model=schemas.Filter)
def update_filter(filter_id: int, filter: schemas.FilterUpdate, db: Session = Depends(get_db)):
    db_filter = crud.get_filter(db, filter_id=filter_id)
    if db_filter is None:
        raise HTTPException(status_code=404, detail="Filter not found")
    return crud.update_filter(db=db, filter=filter, filter_id=filter_id)

@router.delete("/{filter_id}", response_model=schemas.Filter)
def delete_filter(filter_id: int, db: Session = Depends(get_db)):
    db_filter = crud.get_filter(db, filter_id=filter_id)
    if db_filter is None:
        raise HTTPException(status_code=404, detail="Filter not found")
    return crud.delete_filter(db=db, filter_id=filter_id)