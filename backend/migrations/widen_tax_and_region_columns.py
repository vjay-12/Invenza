import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

import asyncio
from sqlalchemy import text
from app.core.database import engine

async def migrate():
    print("Running migration: Widen tax numbers and state/region code columns...")
    async with engine.begin() as conn:
        # Table: invoices
        print("Altering invoices table...")
        await conn.execute(text("ALTER TABLE invoices ALTER COLUMN seller_pan TYPE VARCHAR(50);"))
        await conn.execute(text("ALTER TABLE invoices ALTER COLUMN seller_gstin TYPE VARCHAR(50);"))
        await conn.execute(text("ALTER TABLE invoices ALTER COLUMN seller_state_code TYPE VARCHAR(10);"))
        await conn.execute(text("ALTER TABLE invoices ALTER COLUMN customer_gstin TYPE VARCHAR(50);"))
        await conn.execute(text("ALTER TABLE invoices ALTER COLUMN customer_state_code TYPE VARCHAR(10);"))

        # Table: sales_orders
        print("Altering sales_orders table...")
        await conn.execute(text("ALTER TABLE sales_orders ALTER COLUMN customer_gstin TYPE VARCHAR(50);"))
        await conn.execute(text("ALTER TABLE sales_orders ALTER COLUMN billing_state_code TYPE VARCHAR(10);"))
        await conn.execute(text("ALTER TABLE sales_orders ALTER COLUMN shipping_state_code TYPE VARCHAR(10);"))
        await conn.execute(text("ALTER TABLE sales_orders ALTER COLUMN state_code TYPE VARCHAR(10);"))

        # Table: customers
        print("Altering customers table...")
        await conn.execute(text("ALTER TABLE customers ALTER COLUMN gstin TYPE VARCHAR(50);"))
        await conn.execute(text("ALTER TABLE customers ALTER COLUMN billing_state_code TYPE VARCHAR(10);"))
        await conn.execute(text("ALTER TABLE customers ALTER COLUMN shipping_state_code TYPE VARCHAR(10);"))
        await conn.execute(text("ALTER TABLE customers ALTER COLUMN state_code TYPE VARCHAR(10);"))

    print("Migration completed successfully.")

if __name__ == "__main__":
    asyncio.run(migrate())
