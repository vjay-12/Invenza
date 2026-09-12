import asyncio
from sqlalchemy import text
from app.core.database import engine

async def migrate():
    print("Running migration: add invoice payment columns...")
    async with engine.begin() as conn:
        await conn.execute(text("""
            ALTER TABLE invoices 
            ADD COLUMN IF NOT EXISTS paid_at TIMESTAMP WITHOUT TIME ZONE;
        """))
        await conn.execute(text("""
            ALTER TABLE invoices 
            ADD COLUMN IF NOT EXISTS payment_method VARCHAR(50);
        """))
        await conn.execute(text("""
            ALTER TABLE invoices 
            ADD COLUMN IF NOT EXISTS payment_reference VARCHAR(100);
        """))
    print("Migration completed successfully.")

if __name__ == "__main__":
    asyncio.run(migrate())
