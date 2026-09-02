from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.database import get_db
from app.api.deps import get_current_tenant_id
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse
from app.services.ledger_service import LedgerService

router = APIRouter()

@router.get("/", response_model=List[ProductResponse])
async def list_products(
    category: Optional[str] = None,
    search: Optional[str] = None,
    location_id: Optional[UUID] = None,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    query = select(Product).where(Product.tenant_id == tenant_id)
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
    created = []
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
            variant_attributes=p_in.variant_attributes,
            custom_fields=p_in.custom_fields,
        )
        db.add(product)
        created.append(product)

    await db.commit()
    for p in created:
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
            variant_attributes=p.variant_attributes or {},
            custom_fields=p.custom_fields or {},
            is_active=p.is_active,
            current_stock=0.0,
            created_at=p.created_at,
            updated_at=p.updated_at,
        )
        for p in created
    ]

@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Product).where(and_(Product.id == product_id, Product.tenant_id == tenant_id))
    )
    prod = result.scalar_one_or_none()
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found")
    await db.delete(prod)
    await db.commit()
