from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.database import get_db
from app.api.deps import get_current_tenant_id, get_optional_current_user
from app.models.user import User
from app.models.product import Product
from app.models.ledger import StockMovement, MovementTypeEnum
from app.models.location import Location
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse
from app.services.ledger_service import LedgerService

router = APIRouter()

@router.get("/", response_model=List[ProductResponse])
async def list_products(
    category: Optional[str] = None,
    search: Optional[str] = None,
    location_id: Optional[UUID] = None,
    active_only: Optional[bool] = None,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    query = select(Product).where(Product.tenant_id == tenant_id)
    if active_only is not None:
        query = query.where(Product.is_active == active_only)
    if category and category != "all":
        query = query.where(Product.category == category)
    if search:
        s = f"%{search}%"
        query = query.where((Product.name.ilike(s)) | (Product.sku.ilike(s)) | (Product.barcode.ilike(s)))

    result = await db.execute(query)
    products = result.scalars().all()

    # Calculate aggregated stock from immutable ledger for each product
    response = []
    for p in products:
        current_stock = await LedgerService.get_current_stock(
            db=db,
            tenant_id=tenant_id,
            product_id=p.id,
            location_id=location_id,
        )
        p_dict = {
            "id": p.id,
            "tenant_id": p.tenant_id,
            "sku": p.sku,
            "name": p.name,
            "category": p.category,
            "unit_of_measure": p.unit_of_measure,
            "cost_price": float(p.cost_price),
            "sell_price": float(p.sell_price),
            "barcode": p.barcode,
            "reorder_point": float(p.reorder_point),
            "max_stock": float(p.max_stock) if p.max_stock is not None else None,
            "hsn_code": p.hsn_code or "8471",
            "gst_rate": float(p.gst_rate if p.gst_rate is not None else 18.0),
            "variant_attributes": p.variant_attributes or {},
            "custom_fields": p.custom_fields or {},
            "is_active": p.is_active,
            "current_stock": current_stock,
            "created_at": p.created_at,
            "updated_at": p.updated_at,
        }
        response.append(ProductResponse(**p_dict))

    return response

@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_in: ProductCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    # Check SKU uniqueness within tenant
    existing = await db.execute(
        select(Product).where(
            and_(Product.tenant_id == tenant_id, Product.sku == product_in.sku)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Product with SKU '{product_in.sku}' already exists",
        )

    product = Product(
        tenant_id=tenant_id,
        sku=product_in.sku,
        name=product_in.name,
        category=product_in.category,
        unit_of_measure=product_in.unit_of_measure,
        cost_price=product_in.cost_price,
        sell_price=product_in.sell_price,
        barcode=product_in.barcode,
        reorder_point=product_in.reorder_point,
        max_stock=product_in.max_stock,
        hsn_code=product_in.hsn_code,
        gst_rate=product_in.gst_rate,
        variant_attributes=product_in.variant_attributes,
        custom_fields=product_in.custom_fields,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)

    return ProductResponse(
        id=product.id,
        tenant_id=product.tenant_id,
        sku=product.sku,
        name=product.name,
        category=product.category,
        unit_of_measure=product.unit_of_measure,
        cost_price=float(product.cost_price),
        sell_price=float(product.sell_price),
        barcode=product.barcode,
        reorder_point=float(product.reorder_point),
        max_stock=float(product.max_stock) if product.max_stock is not None else None,
        hsn_code=product.hsn_code or "8471",
        gst_rate=float(product.gst_rate if product.gst_rate is not None else 18.0),
        variant_attributes=product.variant_attributes or {},
        custom_fields=product.custom_fields or {},
        is_active=product.is_active,
        current_stock=0.0,
        created_at=product.created_at,
        updated_at=product.updated_at,
    )

@router.post("/bulk-import", response_model=List[ProductResponse], status_code=status.HTTP_201_CREATED)
async def bulk_create_products(
    products_in: List[ProductCreate],
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    from app.models.location import Location
    from app.models.ledger import StockMovement, MovementTypeEnum

    # Resolve a default location for initial stock allocation
    loc_res = await db.execute(
        select(Location).where(Location.tenant_id == tenant_id).limit(1)
    )
    default_loc = loc_res.scalar_one_or_none()
    if not default_loc:
        default_loc = Location(
            tenant_id=tenant_id,
            name="Main Fulfillment Center",
            code="WH-MAIN",
        )
        db.add(default_loc)
        await db.flush()

    created_pairs = []
    for p_in in products_in:
        existing = await db.execute(
            select(Product).where(
                and_(Product.tenant_id == tenant_id, Product.sku == p_in.sku)
            )
        )
        if existing.scalar_one_or_none():
            continue

        product = Product(
            tenant_id=tenant_id,
            sku=p_in.sku,
            name=p_in.name,
            category=p_in.category,
            unit_of_measure=p_in.unit_of_measure,
            cost_price=p_in.cost_price,
            sell_price=p_in.sell_price,
            barcode=p_in.barcode,
            reorder_point=p_in.reorder_point,
            max_stock=p_in.max_stock,
            hsn_code=p_in.hsn_code,
            gst_rate=p_in.gst_rate,
            variant_attributes=p_in.variant_attributes,
            custom_fields=p_in.custom_fields,
        )
        db.add(product)
        await db.flush()

        initial_qty = float(p_in.initial_stock or 0.0)
        if initial_qty > 0 and default_loc:
            opening_mov = StockMovement(
                tenant_id=tenant_id,
                product_id=product.id,
                location_id=default_loc.id,
                movement_type=MovementTypeEnum.IN,
                quantity=initial_qty,
                reference_type="INITIAL",
                reference_id="OPENING-BALANCE",
                performed_by="Administrator",
                unit_cost=float(p_in.cost_price),
            )
            db.add(opening_mov)

        created_pairs.append((product, initial_qty))

    await db.commit()
    for p, _ in created_pairs:
        await db.refresh(p)

    return [
        ProductResponse(
            id=p.id,
            tenant_id=p.tenant_id,
            sku=p.sku,
            name=p.name,
            category=p.category,
            unit_of_measure=p.unit_of_measure,
            cost_price=float(p.cost_price),
            sell_price=float(p.sell_price),
            barcode=p.barcode,
            reorder_point=float(p.reorder_point),
            max_stock=float(p.max_stock) if p.max_stock is not None else None,
            hsn_code=p.hsn_code or "8471",
            gst_rate=float(p.gst_rate if p.gst_rate is not None else 18.0),
            variant_attributes=p.variant_attributes or {},
            custom_fields=p.custom_fields or {},
            is_active=p.is_active,
            current_stock=stock,
            created_at=p.created_at,
            updated_at=p.updated_at,
        )
        for p, stock in created_pairs
    ]

@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: UUID,
    product_in: ProductUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Product).where(and_(Product.id == product_id, Product.tenant_id == tenant_id))
    )
    prod = result.scalar_one_or_none()
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found")

    update_data = product_in.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(prod, field, val)

    await db.commit()
    await db.refresh(prod)

    current_stock = await LedgerService.get_current_stock(
        db=db,
        tenant_id=tenant_id,
        product_id=prod.id,
    )

    return ProductResponse(
        id=prod.id,
        tenant_id=prod.tenant_id,
        sku=prod.sku,
        name=prod.name,
        category=prod.category,
        unit_of_measure=prod.unit_of_measure,
        cost_price=float(prod.cost_price),
        sell_price=float(prod.sell_price),
        barcode=prod.barcode,
        reorder_point=float(prod.reorder_point),
        max_stock=float(prod.max_stock) if prod.max_stock is not None else None,
        hsn_code=prod.hsn_code or "8471",
        gst_rate=float(prod.gst_rate if prod.gst_rate is not None else 18.0),
        variant_attributes=prod.variant_attributes or {},
        custom_fields=prod.custom_fields or {},
        is_active=prod.is_active,
        current_stock=current_stock,
        created_at=prod.created_at,
        updated_at=prod.updated_at,
    )

@router.delete("/clear-all", status_code=status.HTTP_200_OK)
async def clear_all_products(
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    from app.models.ledger import StockMovement
    from app.models.order import PurchaseOrderItem, SalesOrderItem
    from app.models.transfer import StockTransferItem
    from app.models.adjustment import StockAdjustment
    from sqlalchemy import delete

    # Remove all related items to respect foreign keys
    await db.execute(delete(StockMovement).where(StockMovement.tenant_id == tenant_id))
    await db.execute(delete(StockAdjustment).where(StockAdjustment.tenant_id == tenant_id))
    await db.execute(delete(Product).where(Product.tenant_id == tenant_id))
    await db.commit()
    return {"message": "All products and related stock movements cleared from database."}

@router.delete("/{product_id}", status_code=status.HTTP_200_OK)
async def delete_product(
    product_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Product).where(and_(Product.id == product_id, Product.tenant_id == tenant_id, Product.is_active == True))
    )
    prod = result.scalar_one_or_none()
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found")

    # Determine current stock balance to deduct
    current_stock = await LedgerService.get_current_stock(
        db=db,
        tenant_id=tenant_id,
        product_id=prod.id,
    )

    # Find active location to bind the audit entry
    loc_res = await db.execute(
        select(Location).where(and_(Location.tenant_id == tenant_id, Location.is_active == True)).limit(1)
    )
    loc = loc_res.scalar_one_or_none()
    loc_id = loc.id if loc else None

    operator_name = (current_user.full_name or current_user.email) if current_user else "Administrator"

    if loc_id:
        # Record immutable audit trail movement for product removal
        await LedgerService.record_movement(
            db=db,
            tenant_id=tenant_id,
            product_id=prod.id,
            location_id=loc_id,
            movement_type=MovementTypeEnum.OUT,
            quantity=float(current_stock) if current_stock > 0 else 0.0,
            unit_cost=float(prod.cost_price or 0.0),
            reference_type="ADJUST",
            reference_id=f"DEL-{prod.sku}",
            reason_code="product removed",
            performed_by=operator_name,
        )

    # Soft delete: de-activate product while preserving historical audit & foreign key integrity
    prod.is_active = False
    await db.commit()
    return {"message": f"Product '{prod.name}' removed and audit trail recorded."}
