from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

from app.core.database import get_db
from app.api.deps import get_current_tenant_id
from app.models.ledger import StockMovement, MovementTypeEnum
from app.models.product import Product
from app.models.location import Location
from app.schemas.ledger import StockMovementResponse

router = APIRouter()

@router.get("/", response_model=List[StockMovementResponse])
async def list_movements(
    movement_type: Optional[str] = None,
    product_id: Optional[UUID] = None,
    location_id: Optional[UUID] = None,
    limit: int = Query(50, ge=1, le=500),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(
            StockMovement,
            Product.name.label("product_name"),
            Product.sku.label("sku"),
            Location.name.label("location_name"),
        )
        .join(Product, StockMovement.product_id == Product.id)
        .join(Location, StockMovement.location_id == Location.id)
        .where(StockMovement.tenant_id == tenant_id)
        .order_by(desc(StockMovement.timestamp))
        .limit(limit)
    )

    if movement_type and movement_type != "all":
        query = query.where(StockMovement.movement_type == movement_type)
    if product_id:
        query = query.where(StockMovement.product_id == product_id)
    if location_id:
        query = query.where(
            (StockMovement.location_id == location_id) | (StockMovement.target_location_id == location_id)
        )

    result = await db.execute(query)
    rows = result.all()

    movements = []
    for row in rows:
        m: StockMovement = row[0]
        prod_name = row[1]
        sku = row[2]
        loc_name = row[3]

        movements.append(
            StockMovementResponse(
                id=m.id,
                tenant_id=m.tenant_id,
                product_id=m.product_id,
                product_name=prod_name,
                sku=sku,
                location_id=m.location_id,
                location_name=loc_name,
                target_location_id=m.target_location_id,
                movement_type=m.movement_type.value,
                quantity=float(m.quantity),
                unit_cost=float(m.unit_cost),
                reference_type=m.reference_type,
                reference_id=m.reference_id,
                reason_code=m.reason_code,
                performed_by=m.performed_by,
                timestamp=m.timestamp,
            )
        )

    return movements
