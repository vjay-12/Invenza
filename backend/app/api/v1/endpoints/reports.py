from typing import Dict, Any, List
from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.api.deps import get_current_tenant_id
from app.models.product import Product
from app.services.ledger_service import LedgerService
from app.services.valuation_service import ValuationService

router = APIRouter()

@router.get("/valuation")
async def get_valuation_report(
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Computes total inventory asset valuation using both
    FIFO and Weighted Average Costing models.
    """
    res = await db.execute(select(Product).where(Product.tenant_id == tenant_id))
    products = res.scalars().all()

    total_fifo = 0.0
    total_weighted_avg = 0.0
    total_units = 0.0
    category_breakdown: Dict[str, Dict[str, float]] = {}

    for p in products:
        stock = await LedgerService.get_current_stock(db, tenant_id, p.id)
        total_units += stock

        fifo_val = await ValuationService.calculate_fifo_valuation(db, tenant_id, p.id)
        weighted_val = await ValuationService.calculate_weighted_average(db, tenant_id, p.id)

        # Fallback if no incoming movement history
        if fifo_val == 0.0 and stock > 0:
            fifo_val = round(stock * float(p.cost_price), 2)
        if weighted_val == 0.0 and stock > 0:
            weighted_val = round(stock * float(p.cost_price), 2)

        total_fifo += fifo_val
        total_weighted_avg += weighted_val

        cat = p.category or "General"
        if cat not in category_breakdown:
            category_breakdown[cat] = {"valuation": 0.0, "units": 0.0}
        category_breakdown[cat]["valuation"] += weighted_val
        category_breakdown[cat]["units"] += stock

    return {
        "fifo_total_valuation": round(total_fifo, 2),
        "weighted_avg_total_valuation": round(total_weighted_avg, 2),
        "total_units": total_units,
        "total_skus": len(products),
        "category_breakdown": [
            {"category": k, "valuation": round(v["valuation"], 2), "units": v["units"]}
            for k, v in category_breakdown.items()
        ],
    }
