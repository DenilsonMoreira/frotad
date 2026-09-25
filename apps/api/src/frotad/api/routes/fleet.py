from uuid import UUID

from fastapi import APIRouter, Depends, Query

from frotad.api.dependencies import get_db, get_tenant
from frotad.models.fleet import Driver, Vehicle
from frotad.schemas.fleet import DriverRead, VehicleRead
from frotad.services.fleet import get_record, list_records

router = APIRouter(tags=["fleet"])


@router.get("/vehicles", response_model=list[VehicleRead])
def vehicles(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db=Depends(get_db),
    context=Depends(get_tenant),
):
    return list_records(db, context, Vehicle, offset, limit)


@router.get("/vehicles/{record_id}", response_model=VehicleRead)
def vehicle(record_id: UUID, db=Depends(get_db), context=Depends(get_tenant)):
    return get_record(db, context, Vehicle, record_id)


@router.get("/drivers", response_model=list[DriverRead])
def drivers(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db=Depends(get_db),
    context=Depends(get_tenant),
):
    return list_records(db, context, Driver, offset, limit)


@router.get("/drivers/{record_id}", response_model=DriverRead)
def driver(record_id: UUID, db=Depends(get_db), context=Depends(get_tenant)):
    return get_record(db, context, Driver, record_id)
