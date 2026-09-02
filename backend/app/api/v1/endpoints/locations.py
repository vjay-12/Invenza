from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.database import get_db
from app.api.deps import get_current_tenant_id
from app.models.location import Location
from app.models.product import Product
from app.schemas.location import LocationCreate, LocationResponse
from app.services.ledger_service import LedgerService

router = APIRouter()

@router.get("/", response_model=List[LocationResponse])
async def list_locations(
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Location).where(Location.tenant_id == tenant_id)
    res = await db.execute(stmt)
    locations = res.scalars().all()

    # Fetch all products to aggregate location totals
    prod_res = await db.execute(select(Product).where(Product.tenant_id == tenant_id))
    products = prod_res.scalars().all()

    output = []
    for loc in locations:
        stored_units = 0.0
        active_skus = 0
        for p in products:
            p_stock = await LedgerService.get_current_stock(db, tenant_id, p.id, loc.id)
            if p_stock > 0:
                stored_units += p_stock
                active_skus += 1

        output.append(
            LocationResponse(
                id=loc.id,
                tenant_id=loc.tenant_id,
                name=loc.name,
                code=loc.code,
                address=loc.address,
                capacity=loc.capacity or 10000,
                is_active=loc.is_active,
                total_stored_units=stored_units,
                active_skus_count=active_skus,
                created_at=loc.created_at,
            )
        )
    return output

@router.post("/", response_model=LocationResponse, status_code=status.HTTP_201_CREATED)
async def create_location(
    loc_in: LocationCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(Location).where(and_(Location.tenant_id == tenant_id, Location.code == loc_in.code))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Location code '{loc_in.code}' already registered")

    loc = Location(
        tenant_id=tenant_id,
        name=loc_in.name,
        code=loc_in.code,
        address=loc_in.address,
        capacity=loc_in.capacity,
    )
    db.add(loc)
    await db.commit()
    await db.refresh(loc)

    return LocationResponse(
        id=loc.id,
        tenant_id=loc.tenant_id,
        name=loc.name,
        code=loc.code,
        address=loc.address,
        capacity=loc.capacity or 10000,
        is_active=loc.is_active,
        total_stored_units=0.0,
        active_skus_count=0,
        created_at=loc.created_at,
    )
