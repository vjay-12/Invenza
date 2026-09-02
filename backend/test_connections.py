import asyncio
from app.core.database import engine
from sqlalchemy import text
from app.core.config import settings
import httpx

async def main():
    print(f"Testing DB on {settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT} (DB: {settings.POSTGRES_DB})...")
    try:
        async with engine.connect() as conn:
            res = await conn.execute(text("SELECT count(*) FROM products;"))
            count = res.scalar()
            print(f"DATABASE SUCCESS! Found {count} products in database.")
    except Exception as e:
        print(f"DATABASE ERROR: {e}")

    print(f"\nTesting MinIO on http://{settings.MINIO_ENDPOINT}/minio/health/live ...")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"http://{settings.MINIO_ENDPOINT}/minio/health/live")
            print(f"MINIO SUCCESS! Health status code: {resp.status_code}")
    except Exception as e:
        print(f"MINIO ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(main())
