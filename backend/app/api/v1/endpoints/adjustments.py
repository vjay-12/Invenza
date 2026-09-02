from typing import List
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

from app.core.database import get_db
from app.api.deps import get_current_tenant_id
from app.models.adjustment import StockAdjustment, AdjustmentReason
from app.models.product import Product
from app.models.location import Location
from app.models.ledger import MovementTypeEnum
from app.schemas.adjustment import StockAdjustmentCreate, StockAdjustmentResponse, BulkAdjustmentRequest
from app.services.ledger_service import LedgerService

router = APIRouter()

@router.get("/", response_model=List[StockAdjustmentResponse])
async def list_adjustments(
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(StockAdjustment)
        .where(StockAdjustment.tenant_id == tenant_id)
        .order_by(desc(StockAdjustment.created_at))
    )
    res = await db.execute(stmt)
    adjustments = res.scalars().all()

    output = []
    for adj in adjustments:
        p_res = await db.execute(select(Product.name, Product.sku).where(Product.id == adj.product_id))
        p_row = p_res.first()
        loc_res = await db.execute(select(Location.name).where(Location.id == adj.location_id))
        loc_name = loc_res.scalar_one_or_none() or "Main Hub"

        output.append(
            StockAdjustmentResponse(
                id=adj.id,
                tenant_id=adj.tenant_id,
                adjustment_number=adj.adjustment_number,
                location_id=adj.location_id,
                location_name=loc_name,
                product_id=adj.product_id,
                product_name=p_row[0] if p_row else "Product",
                sku=p_row[1] if p_row else "SKU",
                previous_stock=float(adj.previous_stock),
                new_stock=float(adj.new_stock),
                delta=float(adj.delta),
                reason_code=adj.reason_code,
                notes=adj.notes,
                author=adj.author,
                created_at=adj.created_at,
            )
        )
    return output

@router.post("/", response_model=StockAdjustmentResponse, status_code=status.HTTP_201_CREATED)
async def create_adjustment(
    adj_in: StockAdjustmentCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    previous_stock = await LedgerService.get_current_stock(
        db, tenant_id, adj_in.product_id, adj_in.location_id
    )
    delta = adj_in.new_stock - previous_stock
    if delta == 0:
        raise HTTPException(status_code=400, detail="New stock is identical to current stock. No variance detected.")

    count_res = await db.execute(select(StockAdjustment).where(StockAdjustment.tenant_id == tenant_id))
    count = len(count_res.scalars().all()) + 1
    adj_number = f"ADJ-2026-{count:03d}"

    adjustment = StockAdjustment(
        tenant_id=tenant_id,
        adjustment_number=adj_number,
        location_id=adj_in.location_id,
        product_id=adj_in.product_id,
        previous_stock=previous_stock,
        new_stock=adj_in.new_stock,
        delta=delta,
        reason_code=adj_in.reason_code,
        notes=adj_in.notes,
        author=adj_in.author or "Admin",
    )
    db.add(adjustment)
    await db.flush()

    await LedgerService.record_movement(
        db=db,
        tenant_id=tenant_id,
        product_id=adj_in.product_id,
        location_id=adj_in.location_id,
        movement_type=MovementTypeEnum.ADJUST,
        quantity=delta,
        unit_cost=0.0,
        reference_type="ADJUST",
        reference_id=adj_number,
        reason_code=adj_in.reason_code.value,
        performed_by=adj_in.author or "Admin",
    )

    await db.commit()
    await db.refresh(adjustment)
    return (await list_adjustments(tenant_id, db))[0]

@router.post("/bulk")
async def bulk_adjust_stock(
    payload: BulkAdjustmentRequest,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Batch adjustment across multiple SKUs."""
    for item in payload.adjustments:
        if item.delta == 0:
            continue
        prev = await LedgerService.get_current_stock(db, tenant_id, item.product_id, item.location_id)
        new_stk = max(0.0, prev + item.delta)

        adj = StockAdjustment(
            tenant_id=tenant_id,
            adjustment_number=f"ADJ-BULK-{int(datetime.utcnow().timestamp())}",
            location_id=item.location_id,
            product_id=item.product_id,
            previous_stock=prev,
            new_stock=new_stk,
            delta=item.delta,
            reason_code=item.reason_code,
            notes=item.notes,
            author=payload.author or "Admin",
        )
        db.add(adj)
        await LedgerService.record_movement(
            db=db,
            tenant_id=tenant_id,
            product_id=item.product_id,
            location_id=item.location_id,
            movement_type=MovementTypeEnum.ADJUST,
            quantity=item.delta,
            unit_cost=0.0,
            reference_type="ADJUST",
            reference_id=adj.adjustment_number,
            reason_code=item.reason_code.value,
            performed_by=payload.author or "Admin",
        )
    await db.commit()
    return {"message": f"Successfully applied {len(payload.adjustments)} batch adjustments to ledger"}
