from typing import List, Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

from app.core.database import get_db
from app.api.deps import get_current_tenant_id
from app.models.order import PurchaseOrder, PurchaseOrderItem, SalesOrder, SalesOrderItem, OrderStatus
from app.models.product import Product
from app.models.location import Location
from app.models.ledger import MovementTypeEnum
from app.schemas.order import (
    PurchaseOrderCreate,
    PurchaseOrderResponse,
    SalesOrderCreate,
    SalesOrderResponse,
    ReceiveGoodsRequest,
    FulfillOrderRequest,
)
from app.services.ledger_service import LedgerService

router = APIRouter()

# --- Purchase Orders & GRN ---

@router.get("/purchase-orders", response_model=List[PurchaseOrderResponse])
async def list_purchase_orders(
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(PurchaseOrder)
        .where(PurchaseOrder.tenant_id == tenant_id)
        .order_by(desc(PurchaseOrder.order_date))
    )
    res = await db.execute(stmt)
    orders = res.scalars().all()

    output = []
    for o in orders:
        loc_res = await db.execute(select(Location.name).where(Location.id == o.target_location_id))
        loc_name = loc_res.scalar_one_or_none() or "Main Hub"

        items_res = await db.execute(select(PurchaseOrderItem).where(PurchaseOrderItem.order_id == o.id))
        items = items_res.scalars().all()

        item_responses = []
        for it in items:
            p_res = await db.execute(select(Product.name, Product.sku).where(Product.id == it.product_id))
            p_row = p_res.first()
            item_responses.append({
                "id": it.id,
                "product_id": it.product_id,
                "product_name": p_row[0] if p_row else "Unknown",
                "sku": p_row[1] if p_row else "SKU",
                "ordered_qty": float(it.ordered_qty),
                "received_qty": float(it.received_qty),
                "unit_cost": float(it.unit_cost),
            })

        output.append(
            PurchaseOrderResponse(
                id=o.id,
                tenant_id=o.tenant_id,
                po_number=o.po_number,
                supplier_name=o.supplier_name,
                status=o.status,
                target_location_id=o.target_location_id,
                target_location_name=loc_name,
                total_amount=float(o.total_amount),
                notes=o.notes,
                order_date=o.order_date,
                received_date=o.received_date,
                items=item_responses,
            )
        )
    return output

@router.post("/purchase-orders", response_model=PurchaseOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_purchase_order(
    po_in: PurchaseOrderCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    count_res = await db.execute(select(PurchaseOrder).where(PurchaseOrder.tenant_id == tenant_id))
    count = len(count_res.scalars().all()) + 1
    po_number = f"PO-2026-{count:03d}"

    total_amount = sum(it.ordered_qty * it.unit_cost for it in po_in.items)

    po = PurchaseOrder(
        tenant_id=tenant_id,
        po_number=po_number,
        supplier_name=po_in.supplier_name,
        target_location_id=po_in.target_location_id,
        total_amount=total_amount,
        notes=po_in.notes,
        order_date=po_in.order_date or datetime.utcnow(),
    )
    db.add(po)
    await db.flush()

    items_out = []
    for it in po_in.items:
        line = PurchaseOrderItem(
            order_id=po.id,
            product_id=it.product_id,
            ordered_qty=it.ordered_qty,
            received_qty=0.0,
            unit_cost=it.unit_cost,
        )
        db.add(line)
        await db.flush()
        items_out.append({
            "id": line.id,
            "product_id": line.product_id,
            "ordered_qty": float(line.ordered_qty),
            "received_qty": 0.0,
            "unit_cost": float(line.unit_cost),
        })

    await db.commit()
    await db.refresh(po)

    return PurchaseOrderResponse(
        id=po.id,
        tenant_id=po.tenant_id,
        po_number=po.po_number,
        supplier_name=po.supplier_name,
        status=po.status,
        target_location_id=po.target_location_id,
        total_amount=float(po.total_amount),
        notes=po.notes,
        order_date=po.order_date,
        items=items_out,
    )

@router.post("/purchase-orders/{po_id}/receive", response_model=PurchaseOrderResponse)
async def receive_goods_grn(
    po_id: UUID,
    payload: ReceiveGoodsRequest,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(PurchaseOrder).where(and_(PurchaseOrder.id == po_id, PurchaseOrder.tenant_id == tenant_id)))
    po = res.scalar_one_or_none()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase Order not found")
    if po.status == OrderStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="PO already received")

    items_res = await db.execute(select(PurchaseOrderItem).where(PurchaseOrderItem.order_id == po.id))
    items = items_res.scalars().all()

    for it in items:
        it.received_qty = it.ordered_qty
        await LedgerService.record_movement(
            db=db,
            tenant_id=po.tenant_id,
            product_id=it.product_id,
            location_id=po.target_location_id,
            movement_type=MovementTypeEnum.IN,
            quantity=float(it.ordered_qty),
            unit_cost=float(it.unit_cost),
            reference_type="PO",
            reference_id=po.po_number,
            performed_by=payload.received_by or "Admin",
        )

    po.status = OrderStatus.COMPLETED
    po.received_date = datetime.utcnow()
    if payload.notes:
        po.notes = f"{po.notes or ''} [GRN: {payload.notes}]"

    await db.commit()
    await db.refresh(po)
    return await list_purchase_orders(tenant_id, db)

# --- Sales Orders & Fulfillment ---

@router.post("/sales-orders/{so_id}/fulfill")
async def fulfill_sales_order(
    so_id: UUID,
    payload: FulfillOrderRequest,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(SalesOrder).where(and_(SalesOrder.id == so_id, SalesOrder.tenant_id == tenant_id)))
    so = res.scalar_one_or_none()
    if not so:
        raise HTTPException(status_code=404, detail="Sales order not found")
    if so.status == OrderStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Sales order already fulfilled")

    items_res = await db.execute(select(SalesOrderItem).where(SalesOrderItem.order_id == so.id))
    items = items_res.scalars().all()

    for it in items:
        avail = await LedgerService.get_current_stock(db, so.tenant_id, it.product_id, so.source_location_id)
        if avail < float(it.ordered_qty):
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for product. Available: {avail}, Ordered: {it.ordered_qty}",
            )

    for it in items:
        it.fulfilled_qty = it.ordered_qty
        await LedgerService.record_movement(
            db=db,
            tenant_id=so.tenant_id,
            product_id=it.product_id,
            location_id=so.source_location_id,
            movement_type=MovementTypeEnum.OUT,
            quantity=float(it.ordered_qty),
            unit_cost=0.0,
            reference_type="SO",
            reference_id=so.so_number,
            performed_by=payload.dispatched_by or "Dispatch Lead",
        )

    so.status = OrderStatus.COMPLETED
    so.fulfilled_date = datetime.utcnow()
    await db.commit()
    return {"message": f"Sales Order {so.so_number} fulfilled and OUT movements recorded in ledger"}
