"""
LedgerService: Implements the immutable stock movement ledger architecture.
Stock is NEVER stored as a mutable count on the product table.
Instead, all inventory changes are strictly appended to the `stock_movements` table,
and active balances are mathematically aggregated on demand or cached in Redis.
"""

from typing import Dict, List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.models.ledger import StockMovement, MovementTypeEnum
from app.models.product import Product

class LedgerService:
    @staticmethod
    async def get_current_stock(
        db: AsyncSession,
        tenant_id: UUID,
        product_id: UUID,
        location_id: Optional[UUID] = None,
    ) -> float:
        """
        Deterministically aggregates inventory from the immutable ledger.
        IN movements add stock.
        OUT movements deduct stock.
        ADJUST movements apply signed delta.
        TRANSFER movements deduct from source and add to destination.
        """
        # 1. Direct location movements
        query = select(StockMovement).where(
            and_(
                StockMovement.tenant_id == tenant_id,
                StockMovement.product_id == product_id,
            )
        )
        if location_id:
            query = query.where(
                (StockMovement.location_id == location_id) | (StockMovement.target_location_id == location_id)
            )

        result = await db.execute(query)
        movements = result.scalars().all()

        total = 0.0
        for m in movements:
            qty = float(m.quantity)
            if location_id:
                # Specific location calculation
                if m.movement_type == MovementTypeEnum.IN and m.location_id == location_id:
                    total += qty
                elif m.movement_type == MovementTypeEnum.OUT and m.location_id == location_id:
                    total -= qty
                elif m.movement_type == MovementTypeEnum.ADJUST and m.location_id == location_id:
                    total += qty
                elif m.movement_type == MovementTypeEnum.TRANSFER:
                    if m.location_id == location_id:
                        total -= qty
                    elif m.target_location_id == location_id:
                        total += qty
            else:
                # Global total calculation
                if m.movement_type == MovementTypeEnum.IN:
                    total += qty
                elif m.movement_type == MovementTypeEnum.OUT:
                    total -= qty
                elif m.movement_type == MovementTypeEnum.ADJUST:
                    total += qty
                # Inter-warehouse transfer is net-zero globally

        return max(0.0, total)

    @staticmethod
    async def record_movement(
        db: AsyncSession,
        tenant_id: UUID,
        product_id: UUID,
        location_id: UUID,
        movement_type: MovementTypeEnum,
        quantity: float,
        unit_cost: float,
        reference_type: str,
        reference_id: str,
        performed_by: str,
        target_location_id: Optional[UUID] = None,
        reason_code: Optional[str] = None,
    ) -> StockMovement:
        """
        Appends an immutable movement record.
        """
        movement = StockMovement(
            tenant_id=tenant_id,
            product_id=product_id,
            location_id=location_id,
            target_location_id=target_location_id,
            movement_type=movement_type,
            quantity=quantity,
            unit_cost=unit_cost,
            reference_type=reference_type,
            reference_id=reference_id,
            reason_code=reason_code,
            performed_by=performed_by,
        )
        db.add(movement)
        await db.flush()
        return movement
