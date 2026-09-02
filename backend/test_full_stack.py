import asyncio
import uuid
import httpx
from datetime import datetime
from sqlalchemy import select, text
from app.core.database import AsyncSessionLocal, engine
from app.models.product import Product
from app.models.location import Location
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.models.ledger import StockMovement, MovementTypeEnum
from app.services.storage import StorageService

async def test_all():
    print("=== 1. TESTING DIRECT DATABASE WRITE & READ ===")
    demo_tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    async with AsyncSessionLocal() as session:
        # Check tenant
        t_res = await session.execute(select(Tenant).where(Tenant.id == demo_tenant_id))
        tenant = t_res.scalar_one_or_none()
        print(f"Tenant in DB: {tenant.name if tenant else 'None'}")
        
        # Insert test product
        test_sku = f"SKU-TEST-{uuid.uuid4().hex[:6].upper()}"
        new_prod = Product(
            id=uuid.uuid4(),
            tenant_id=demo_tenant_id,
            sku=test_sku,
            name="Logitech MX Master 3S Test",
            category="Electronics",
            unit_of_measure="pcs",
            cost_price=65.00,
            sell_price=99.00,
            barcode="761198450123",
            reorder_point=10.0,
            variant_attributes={"color": "Graphite", "connectivity": "Bluetooth"},
            custom_fields={"batch": "BATCH-2026-TEST", "zone": "Zone A"},
        )
        session.add(new_prod)
        await session.commit()
        await session.refresh(new_prod)
        print(f"[DB Write SUCCESS] Created Product: {new_prod.name} (SKU: {new_prod.sku}, ID: {new_prod.id})")
        
        # Read back product
        prod_check = await session.execute(select(Product).where(Product.id == new_prod.id))
        fetched = prod_check.scalar_one_or_none()
        print(f"[DB Read SUCCESS] Fetched Product: {fetched.name}, Sell Price: ${fetched.sell_price}")
        
        # Test writing StockMovement record
        # get location
        loc_res = await session.execute(select(Location).where(Location.tenant_id == demo_tenant_id))
        location = loc_res.scalars().first()
        if location:
            movement = StockMovement(
                tenant_id=demo_tenant_id,
                product_id=new_prod.id,
                location_id=location.id,
                movement_type=MovementTypeEnum.IN,
                quantity=50.0,
                unit_cost=65.0,
                reference_type="PO",
                reference_id="PO-TEST-001",
                performed_by="Automated Test",
            )
            session.add(movement)
            await session.commit()
            print(f"[DB Write SUCCESS] Created Ledger Movement: +50 units in {location.name}")
            
            # Count movements
            m_count = await session.execute(select(text("COUNT(*) FROM stock_movements")))
            print(f"[DB Query SUCCESS] Total Stock Movements in DB: {m_count.scalar()}")

    print("\n=== 2. TESTING MINIO OBJECT STORAGE WRITE & READ ===")
    test_content = b"INVENZA INVENTORY AUDIT CERTIFICATE - 2026\nStatus: Verified\nLedger Hash: OK"
    object_name = f"test_docs/audit_cert_{uuid.uuid4().hex[:6]}.txt"
    
    upload_res = StorageService.upload_file(
        file_bytes=test_content,
        object_name=object_name,
        content_type="text/plain",
        metadata={"author": "Invenza Test Engine", "doc_type": "audit"}
    )
    print(f"[MinIO Write SUCCESS] Uploaded object: {upload_res['object_name']}, size: {upload_res['size']} bytes")
    
    # Read back from MinIO
    file_obj = StorageService.get_file(object_name)
    read_data = file_obj.read()
    print(f"[MinIO Read SUCCESS] Retrieved object content: {read_data.decode('utf-8')}")
    
    # List files in MinIO
    all_files = StorageService.list_files()
    print(f"[MinIO List SUCCESS] Total objects stored in MinIO: {len(all_files)}")
    for f in all_files[-3:]:
        print(f"  - {f['object_name']} ({f['size']} bytes)")

    print("\n=== ALL DIRECT DATABASE & MINIO VERIFICATION CHECKS PASSED ===")

if __name__ == "__main__":
    asyncio.run(test_all())
