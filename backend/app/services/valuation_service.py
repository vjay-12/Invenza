"""
ValuationService: Implements FIFO (First-In, First-Out) and Weighted Average Costing models.
Calculates stock valuation directly from chronological ledger movement batches.
"""

from typing import Dict, List, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models.ledger import StockMovement, MovementTypeEnum
from app.models.product import Product

class ValuationService:
    @staticmethod
    async def calculate_fifo_valuation(
        db: AsyncSession,
        tenant_id: UUID,
        product_id: UUID,
    ) -> float:
        """
        FIFO Costing:
        - Tracks chronological purchase lots (IN movements) with their exact unit costs.
        - Outflows (OUT, transfers, negative adjustments) liquidate the oldest lots first.
        - The remaining balance is valued at the unit cost of the newest unliquidated lots.
        """
        stmt = (
            select(StockMovement)
            .where(
                and_(
                    StockMovement.tenant_id == tenant_id,
                    StockMovement.product_id == product_id,
                )
            )
            .order_by(StockMovement.timestamp.asc())
        )
        res = await db.execute(stmt)
        movements = res.scalars().all()

        # Build incoming lots: list of [remaining_qty, unit_cost]
        lots: List[List[float]] = []

        for m in movements:
            qty = float(m.quantity)
            cost = float(m.unit_cost)

            if m.movement_type == MovementTypeEnum.IN:
                lots.append([qty, cost])
            elif m.movement_type in [MovementTypeEnum.OUT, MovementTypeEnum.ADJUST]:
                # If negative, liquidate from oldest lots
                drain_qty = qty if m.movement_type == MovementTypeEnum.OUT else -qty
                if drain_qty > 0:
                    for lot in lots:
                        if drain_qty <= 0:
                            break
                        if lot[0] <= drain_qty:
                            drain_qty -= lot[0]
                            lot[0] = 0.0
                        else:
                            lot[0] -= drain_qty
                            drain_qty = 0.0
                elif drain_qty < 0:
                    # Positive adjustment behaves like incoming lot
                    lots.append([-drain_qty, cost])

        # Value remaining lots
        fifo_total = sum(lot[0] * lot[1] for lot in lots if lot[0] > 0)
        return round(fifo_total, 2)

    @staticmethod
    async def calculate_weighted_average(
        db: AsyncSession,
        tenant_id: UUID,
        product_id: UUID,
    ) -> float:
        """
        Weighted Average Costing:
        Blends the acquisition costs across all units.
        """
        stmt = select(StockMovement).where(
            and_(
                StockMovement.tenant_id == tenant_id,
                StockMovement.product_id == product_id,
                StockMovement.movement_type == MovementTypeEnum.IN,
            )
        )
        res = await db.execute(stmt)
        in_movements = res.scalars().all()

        total_in_cost = sum(float(m.quantity) * float(m.unit_cost) for m in in_movements)
        total_in_qty = sum(float(m.quantity) for m in in_movements)

        if total_in_qty <= 0:
            return 0.0

        avg_unit_cost = total_in_cost / total_in_qty
        
        # Multiply by current aggregated stock
        from app.services.ledger_service import LedgerService
        current_stock = await LedgerService.get_current_stock(db, tenant_id, product_id)

        return round(current_stock * avg_unit_cost, 2)
