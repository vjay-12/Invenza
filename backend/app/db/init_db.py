"""
Database initialization, auto-migration, and enterprise seed script.
Ensures Super Admin, master tenant, and multi-tenant schema are ready.
"""

import asyncio
from datetime import datetime
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.core.database import AsyncSessionLocal, engine, Base
from app.core.security import get_password_hash
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.models.location import Location
from app.models.product import Product
from app.models.ledger import StockMovement, MovementTypeEnum

MASTER_TENANT_ID = UUID("00000000-0000-0000-0000-000000000000")
DEMO_TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")

DEFAULT_MODULES = [
    "products",
    "locations",
    "orders",
    "transfers",
    "adjustments",
    "ledger",
    "reports",
    "storage",
]

async def migrate_columns():
    """
    Idempotent schema updates to add new columns to existing PostgreSQL tables.
    """
    async with engine.begin() as conn:
        # Create all tables defined in metadata if not yet created
        await conn.run_sync(Base.metadata.create_all)

        # Alter tenants table for new multi-tenant fields
        alter_tenants = [
            "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS industry VARCHAR(100) DEFAULT 'General Merchandise';",
            "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS location VARCHAR(255) DEFAULT 'Headquarters';",
            "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS enabled_modules JSONB DEFAULT '[\"products\",\"locations\",\"orders\",\"transfers\",\"adjustments\",\"ledger\",\"reports\",\"storage\"]'::jsonb;",
            "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;",
        ]
        for stmt in alter_tenants:
            try:
                await conn.execute(text(stmt))
            except Exception as e:
                print(f"[Schema Migration Warning - tenants]: {e}")

        # Alter users table for permissions and role
        alter_users = [
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS permissions JSONB DEFAULT '[]'::jsonb;",
            "ALTER TABLE users ALTER COLUMN role TYPE VARCHAR(50);",
        ]
        for stmt in alter_users:
            try:
                await conn.execute(text(stmt))
            except Exception as e:
                print(f"[Schema Migration Warning - users]: {e}")

async def init_db():
    await migrate_columns()

    async with AsyncSessionLocal() as session:
        # 1. Master System Tenant (for Super Admin)
        master_res = await session.execute(select(Tenant).where(Tenant.id == MASTER_TENANT_ID))
        master_tenant = master_res.scalar_one_or_none()
        if not master_tenant:
            master_tenant = Tenant(
                id=MASTER_TENANT_ID,
                name="Invenza Master Platform",
                slug="invenza-master",
                industry="Enterprise Platform",
                location="Global Cloud Core",
                currency_code="USD",
                enabled_modules=["companies", "analytics", "reports", "settings"],
                is_active=True,
            )
            session.add(master_tenant)
            await session.flush()

        # 2. Super Admin User
        super_res = await session.execute(select(User).where(User.email == "superadmin@invenza.internal"))
        super_user = super_res.scalar_one_or_none()
        if not super_user:
            super_user = User(
                tenant_id=MASTER_TENANT_ID,
                email="superadmin@invenza.internal",
                hashed_password=get_password_hash("superadmin2026"),
                full_name="Invenza Super Administrator",
                role=UserRole.SUPER_ADMIN.value,
                permissions=["all"],
                is_active=True,
            )
            session.add(super_user)
        else:
            # Ensure role and password are up to date
            super_user.role = UserRole.SUPER_ADMIN.value
            super_user.hashed_password = get_password_hash("superadmin2026")
            super_user.is_active = True

        # 3. Demo Tenant (Sample Company)
        tenant_res = await session.execute(select(Tenant).where(Tenant.id == DEMO_TENANT_ID))
        demo_tenant = tenant_res.scalar_one_or_none()
        if not demo_tenant:
            demo_tenant = Tenant(
                id=DEMO_TENANT_ID,
                name="Apex Global Logistics",
                slug="apex-logistics",
                industry="Logistics & Supply Chain",
                location="Chicago, IL, USA",
                currency_code="USD",
                enabled_modules=DEFAULT_MODULES,
                is_active=True,
            )
            session.add(demo_tenant)
            await session.flush()
        else:
            demo_tenant.industry = "Logistics & Supply Chain"
            demo_tenant.location = "Chicago, IL, USA"
            demo_tenant.enabled_modules = DEFAULT_MODULES

        # 4. Demo Company Admin
        demo_admin_res = await session.execute(select(User).where(User.email == "admin@invenza.internal"))
        demo_admin = demo_admin_res.scalar_one_or_none()
        if not demo_admin:
            demo_admin = User(
                tenant_id=DEMO_TENANT_ID,
                email="admin@invenza.internal",
                hashed_password=get_password_hash("adminpassword2026"),
                full_name="Sarah Connor (Admin)",
                role=UserRole.ADMIN.value,
                permissions=["inventory:read", "inventory:write", "orders:manage", "team:manage", "reports:view"],
                is_active=True,
            )
            session.add(demo_admin)
        else:
            demo_admin.role = UserRole.ADMIN.value
            demo_admin.hashed_password = get_password_hash("adminpassword2026")

        # 5. Seed sample warehouse & product for demo tenant if empty
        loc1_id = UUID("00000000-0000-0000-0000-000000000011")
        loc_res = await session.execute(select(Location).where(Location.id == loc1_id))
        if not loc_res.scalar_one_or_none():
            session.add(Location(
                id=loc1_id,
                tenant_id=DEMO_TENANT_ID,
                name="Central Logistics Hub",
                code="HUB-01",
                address="404 Logistics Blvd, Chicago, IL",
                capacity=25000,
            ))
            await session.flush()

        prod1_id = UUID("00000000-0000-0000-0000-000000000021")
        p_res = await session.execute(select(Product).where(Product.id == prod1_id))
        if not p_res.scalar_one_or_none():
            prod1 = Product(
                id=prod1_id,
                tenant_id=DEMO_TENANT_ID,
                sku="SKU-ERG-CHAIR",
                name="AeroPro Ergonomic Executive Chair",
                category="Office Furniture",
                unit_of_measure="pcs",
                cost_price=145.00,
                sell_price=320.00,
                barcode="890123450012",
                reorder_point=15,
                variant_attributes={"Color": "Space Gray", "Material": "Mesh"},
                custom_fields={"batchNumber": "LOT-2026-A1", "storageZone": "High Rack R4"},
            )
            session.add(prod1)

        await session.commit()
        print("Invenza database initialization, Super Admin seeding, and schema migration complete.")

if __name__ == "__main__":
    asyncio.run(init_db())
