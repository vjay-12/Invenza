from typing import List
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

from app.core.database import get_db
from app.api.deps import get_current_tenant_id
from app.models.transfer import StockTransfer, StockTransferItem
from app.models.product import Product
from app.models.location import Location
from app.models.ledger import MovementTypeEnum
from app.schemas.transfer import StockTransferCreate, StockTransferResponse
from app.services.ledger_service import LedgerService

router = APIRouter()

@router.get("/", response_model=List[StockTransferResponse])
async def list_transfers(
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(StockTransfer)
        .where(StockTransfer.tenant_id == tenant_id)
        .order_by(desc(StockTransfer.transfer_date))
    )
    res = await db.execute(stmt)
    transfers = res.scalars().all()

    output = []
    for tr in transfers:
        src_res = await db.execute(select(Location.name).where(Location.id == tr.source_location_id))
        dst_res = await db.execute(select(Location.name).where(Location.id == tr.target_location_id))
        src_name = src_res.scalar_one_or_none() or "Source Hub"
        dst_name = dst_res.scalar_one_or_none() or "Target Hub"

        items_res = await db.execute(select(StockTransferItem).where(StockTransferItem.transfer_id == tr.id))
        items = items_res.scalars().all()
        item_responses = []
        for it in items:
            p_res = await db.execute(select(Product.name, Product.sku).where(Product.id == it.product_id))
            p_row = p_res.first()
            item_responses.append({
                "id": it.id,
                "product_id": it.product_id,
                "product_name": p_row[0] if p_row else "Item",
                "sku": p_row[1] if p_row else "SKU",
                "quantity": float(it.quantity),
            })

        output.append(
            StockTransferResponse(
                id=tr.id,
                tenant_id=tr.tenant_id,
                transfer_number=tr.transfer_number,
                source_location_id=tr.source_location_id,
                source_location_name=src_name,
                target_location_id=tr.target_location_id,
                target_location_name=dst_name,
                status=tr.status,
                transfer_date=tr.transfer_date,
                notes=tr.notes,
                items=item_responses,
            )
        )
    return output

@router.post("/", response_model=StockTransferResponse, status_code=status.HTTP_201_CREATED)
async def create_stock_transfer(
    transfer_in: StockTransferCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    if transfer_in.source_location_id == transfer_in.target_location_id:
        raise HTTPException(status_code=400, detail="Source and destination locations cannot be identical")

    # Check inventory availability in source location
    for it in transfer_in.items:
        avail = await LedgerService.get_current_stock(
            db, tenant_id, it.product_id, transfer_in.source_location_id
        )
        if avail < it.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock in source location. Available: {avail}, Requested: {it.quantity}",
            )

    count_res = await db.execute(select(StockTransfer).where(StockTransfer.tenant_id == tenant_id))
    count = len(count_res.scalars().all()) + 1
    tr_number = f"TR-2026-{count:03d}"

    transfer = StockTransfer(
        tenant_id=tenant_id,
        transfer_number=tr_number,
        source_location_id=transfer_in.source_location_id,
        target_location_id=transfer_in.target_location_id,
        status="completed",
        notes=transfer_in.notes,
    )
    db.add(transfer)
    await db.flush()

    for it in transfer_in.items:
        t_item = StockTransferItem(
            transfer_id=transfer.id,
            product_id=it.product_id,
            quantity=it.quantity,
        )
        db.add(t_item)

        await LedgerService.record_movement(
            db=db,
            tenant_id=tenant_id,
            product_id=it.product_id,
            location_id=transfer_in.source_location_id,
            target_location_id=transfer_in.target_location_id,
            movement_type=MovementTypeEnum.TRANSFER,
            quantity=it.quantity,
            unit_cost=0.0,
            reference_type="TRANSFER",
            reference_id=tr_number,
            performed_by="Inventory Logistics",
        )

    await db.commit()
    await db.refresh(transfer)
    return (await list_transfers(tenant_id, db))[0]
