"""
Phase 1 Cleanup Script: Cleans PostgreSQL and MinIO.
Preserves ONLY:
- Hapkonic (and all its related data)
- Marketza (and all its related data)
- Super Admin login credentials (under Invenza Master Platform)
"""

import asyncio
import sys
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sqlalchemy import text
from app.core.database import AsyncSessionLocal
from app.services.storage import StorageService, BUCKET_NAME

MASTER_ID = "00000000-0000-0000-0000-000000000000"
HAPKONIC_ID = "14df4ac7-cd5c-4baa-a6d6-cc6f62445e4e"
MARKETZA_ID = "0079e16f-0ce9-425b-a069-78e268da1913"

PRESERVED_TENANTS = (MASTER_ID, HAPKONIC_ID, MARKETZA_ID)
PRESERVED_CLIENT_ORGS = (HAPKONIC_ID, MARKETZA_ID)

async def cleanup_postgres():
    print("\n--- Cleaning PostgreSQL ---")
    async with AsyncSessionLocal() as session:
        # Step 1: Stock transfers & items
        await session.execute(text("""
            DELETE FROM stock_transfer_items 
            WHERE transfer_id IN (
                SELECT id FROM stock_transfers 
                WHERE tenant_id NOT IN ('14df4ac7-cd5c-4baa-a6d6-cc6f62445e4e', '0079e16f-0ce9-425b-a069-78e268da1913')
            )
        """))
        res = await session.execute(text("""
            DELETE FROM stock_transfers 
            WHERE tenant_id NOT IN ('14df4ac7-cd5c-4baa-a6d6-cc6f62445e4e', '0079e16f-0ce9-425b-a069-78e268da1913')
        """))
        print(f"Deleted stock_transfers: {res.rowcount}")

        # Step 2: Sales orders & items
        await session.execute(text("""
            DELETE FROM sales_order_items 
            WHERE order_id IN (
                SELECT id FROM sales_orders 
                WHERE tenant_id NOT IN ('14df4ac7-cd5c-4baa-a6d6-cc6f62445e4e', '0079e16f-0ce9-425b-a069-78e268da1913')
            )
        """))
        res = await session.execute(text("""
            DELETE FROM sales_orders 
            WHERE tenant_id NOT IN ('14df4ac7-cd5c-4baa-a6d6-cc6f62445e4e', '0079e16f-0ce9-425b-a069-78e268da1913')
        """))
        print(f"Deleted sales_orders: {res.rowcount}")

        # Step 3: Purchase orders & items
        await session.execute(text("""
            DELETE FROM purchase_order_items 
            WHERE order_id IN (
                SELECT id FROM purchase_orders 
                WHERE tenant_id NOT IN ('14df4ac7-cd5c-4baa-a6d6-cc6f62445e4e', '0079e16f-0ce9-425b-a069-78e268da1913')
            )
        """))
        res = await session.execute(text("""
            DELETE FROM purchase_orders 
            WHERE tenant_id NOT IN ('14df4ac7-cd5c-4baa-a6d6-cc6f62445e4e', '0079e16f-0ce9-425b-a069-78e268da1913')
        """))
        print(f"Deleted purchase_orders: {res.rowcount}")

        # Step 4: Stock adjustments & movements
        res = await session.execute(text("""
            DELETE FROM stock_adjustments 
            WHERE tenant_id NOT IN ('14df4ac7-cd5c-4baa-a6d6-cc6f62445e4e', '0079e16f-0ce9-425b-a069-78e268da1913')
        """))
        print(f"Deleted stock_adjustments: {res.rowcount}")

        res = await session.execute(text("""
            DELETE FROM stock_movements 
            WHERE tenant_id NOT IN ('14df4ac7-cd5c-4baa-a6d6-cc6f62445e4e', '0079e16f-0ce9-425b-a069-78e268da1913')
        """))
        print(f"Deleted stock_movements: {res.rowcount}")

        # Step 5: Invoices & items
        await session.execute(text("""
            DELETE FROM invoice_items 
            WHERE invoice_id IN (
                SELECT id FROM invoices 
                WHERE tenant_id NOT IN ('14df4ac7-cd5c-4baa-a6d6-cc6f62445e4e', '0079e16f-0ce9-425b-a069-78e268da1913')
            )
        """))
        res = await session.execute(text("""
            DELETE FROM invoices 
            WHERE tenant_id NOT IN ('14df4ac7-cd5c-4baa-a6d6-cc6f62445e4e', '0079e16f-0ce9-425b-a069-78e268da1913')
        """))
        print(f"Deleted invoices: {res.rowcount}")

        # Step 6: Products, locations, customers
        res = await session.execute(text("""
            DELETE FROM products 
            WHERE tenant_id NOT IN ('14df4ac7-cd5c-4baa-a6d6-cc6f62445e4e', '0079e16f-0ce9-425b-a069-78e268da1913')
        """))
        print(f"Deleted products: {res.rowcount}")

        res = await session.execute(text("""
            DELETE FROM locations 
            WHERE tenant_id NOT IN ('14df4ac7-cd5c-4baa-a6d6-cc6f62445e4e', '0079e16f-0ce9-425b-a069-78e268da1913')
        """))
        print(f"Deleted locations: {res.rowcount}")

        res = await session.execute(text("""
            DELETE FROM customers 
            WHERE tenant_id NOT IN ('14df4ac7-cd5c-4baa-a6d6-cc6f62445e4e', '0079e16f-0ce9-425b-a069-78e268da1913')
        """))
        print(f"Deleted customers: {res.rowcount}")

        # Step 7: Email changes, security requests, audit logs
        try:
            res = await session.execute(text("""
                DELETE FROM email_change_requests 
                WHERE tenant_id NOT IN ('14df4ac7-cd5c-4baa-a6d6-cc6f62445e4e', '0079e16f-0ce9-425b-a069-78e268da1913')
            """))
            print(f"Deleted email_change_requests: {res.rowcount}")
        except Exception as e:
            print(f"email_change_requests notice: {e}")

        res = await session.execute(text("""
            DELETE FROM security_approval_requests 
            WHERE tenant_id NOT IN ('14df4ac7-cd5c-4baa-a6d6-cc6f62445e4e', '0079e16f-0ce9-425b-a069-78e268da1913')
        """))
        print(f"Deleted security_approval_requests: {res.rowcount}")

        res = await session.execute(text("""
            DELETE FROM audit_logs 
            WHERE tenant_id IS NOT NULL 
              AND tenant_id NOT IN ('00000000-0000-0000-0000-000000000000', '14df4ac7-cd5c-4baa-a6d6-cc6f62445e4e', '0079e16f-0ce9-425b-a069-78e268da1913')
        """))
        print(f"Deleted audit_logs: {res.rowcount}")

        # Step 8: Lead inquiries (preserve Marketza / Hapkonic)
        res = await session.execute(text("""
            DELETE FROM lead_inquiries 
            WHERE company_name NOT ILIKE '%marketza%' 
              AND company_name NOT ILIKE '%hapkonic%'
        """))
        print(f"Deleted lead_inquiries: {res.rowcount}")

        # Step 9: Billing tables
        res = await session.execute(text("""
            DELETE FROM org_maintenance_cycle 
            WHERE org_id NOT IN ('14df4ac7-cd5c-4baa-a6d6-cc6f62445e4e', '0079e16f-0ce9-425b-a069-78e268da1913')
        """))
        print(f"Deleted org_maintenance_cycle: {res.rowcount}")

        res = await session.execute(text("""
            DELETE FROM org_maintenance_plan 
            WHERE org_id NOT IN ('14df4ac7-cd5c-4baa-a6d6-cc6f62445e4e', '0079e16f-0ce9-425b-a069-78e268da1913')
        """))
        print(f"Deleted org_maintenance_plan: {res.rowcount}")

        res = await session.execute(text("""
            DELETE FROM org_setup_fee 
            WHERE org_id NOT IN ('14df4ac7-cd5c-4baa-a6d6-cc6f62445e4e', '0079e16f-0ce9-425b-a069-78e268da1913')
        """))
        print(f"Deleted org_setup_fee: {res.rowcount}")

        res = await session.execute(text("""
            DELETE FROM billing_payment_records 
            WHERE tenant_id NOT IN ('14df4ac7-cd5c-4baa-a6d6-cc6f62445e4e', '0079e16f-0ce9-425b-a069-78e268da1913')
        """))
        print(f"Deleted billing_payment_records: {res.rowcount}")

        res = await session.execute(text("""
            DELETE FROM tenant_billing_profiles 
            WHERE tenant_id NOT IN ('00000000-0000-0000-0000-000000000000', '14df4ac7-cd5c-4baa-a6d6-cc6f62445e4e', '0079e16f-0ce9-425b-a069-78e268da1913')
        """))
        print(f"Deleted tenant_billing_profiles: {res.rowcount}")

        try:
            await session.execute(text("""
                DELETE FROM billing_fee_history 
                WHERE tenant_id NOT IN ('00000000-0000-0000-0000-000000000000', '14df4ac7-cd5c-4baa-a6d6-cc6f62445e4e', '0079e16f-0ce9-425b-a069-78e268da1913')
            """))
        except Exception:
            pass

        # Step 10: Sequences & settings
        res = await session.execute(text("""
            DELETE FROM tenant_invoice_sequences 
            WHERE tenant_id NOT IN ('00000000-0000-0000-0000-000000000000', '14df4ac7-cd5c-4baa-a6d6-cc6f62445e4e', '0079e16f-0ce9-425b-a069-78e268da1913')
        """))
        print(f"Deleted tenant_invoice_sequences: {res.rowcount}")

        res = await session.execute(text("""
            DELETE FROM tenant_settings 
            WHERE tenant_id NOT IN ('00000000-0000-0000-0000-000000000000', '14df4ac7-cd5c-4baa-a6d6-cc6f62445e4e', '0079e16f-0ce9-425b-a069-78e268da1913')
        """))
        print(f"Deleted tenant_settings: {res.rowcount}")

        try:
            await session.execute(text("""
                DELETE FROM outbound_webhooks 
                WHERE tenant_id NOT IN ('14df4ac7-cd5c-4baa-a6d6-cc6f62445e4e', '0079e16f-0ce9-425b-a069-78e268da1913')
            """))
        except Exception:
            pass

        # Step 11: Users (preserve Super Admin, Hapkonic users, Marketza users)
        res = await session.execute(text("""
            DELETE FROM users 
            WHERE tenant_id NOT IN ('00000000-0000-0000-0000-000000000000', '14df4ac7-cd5c-4baa-a6d6-cc6f62445e4e', '0079e16f-0ce9-425b-a069-78e268da1913')
        """))
        print(f"Deleted users: {res.rowcount}")

        # Step 12: Tenants (preserve Master Platform, Hapkonic, Marketza)
        res = await session.execute(text("""
            DELETE FROM tenants 
            WHERE id NOT IN ('00000000-0000-0000-0000-000000000000', '14df4ac7-cd5c-4baa-a6d6-cc6f62445e4e', '0079e16f-0ce9-425b-a069-78e268da1913')
        """))
        print(f"Deleted tenants: {res.rowcount}")

        await session.commit()
        print("PostgreSQL cleanup committed successfully.")

def cleanup_minio():
    print("\n--- Cleaning MinIO ---")
    client = StorageService.get_client()
    objects = list(client.list_objects(BUCKET_NAME, recursive=True))
    print(f"Total MinIO objects before cleanup: {len(objects)}")
    
    deleted_count = 0
    preserved_count = 0
    for obj in objects:
        name = obj.object_name
        # Preserve Hapkonic and Marketza objects
        if (name.startswith("HAPKONIC/") or 
            name.startswith("invoices/14df4ac7-cd5c-4baa-a6d6-cc6f62445e4e/") or 
            name.startswith("MARKETZA/") or 
            name.startswith("invoices/0079e16f-0ce9-425b-a069-78e268da1913/")):
            print(f"  [PRESERVE] {name}")
            preserved_count += 1
        else:
            print(f"  [DELETE] {name}")
            client.remove_object(BUCKET_NAME, name)
            deleted_count += 1

    print(f"MinIO cleanup finished. Deleted: {deleted_count}, Preserved: {preserved_count}")

async def verify_checkpoint():
    print("\n--- Phase 1 Verification Checkpoint ---")
    async with AsyncSessionLocal() as session:
        # Tenants
        tenants = (await session.execute(text("SELECT id, name, slug, company_code FROM tenants ORDER BY name"))).fetchall()
        print(f"Remaining Tenants in DB ({len(tenants)}):")
        for t in tenants:
            print(f"  - id={t[0]} name='{t[1]}' slug='{t[2]}' code='{t[3]}'")

        # Users
        users = (await session.execute(text("SELECT u.id, u.email, u.full_name, u.role, t.name FROM users u JOIN tenants t ON u.tenant_id = t.id ORDER BY t.name, u.email"))).fetchall()
        print(f"\nRemaining Users in DB ({len(users)}):")
        for u in users:
            print(f"  - email='{u[1]}' name='{u[2]}' role='{u[3]}' tenant='{u[4]}'")

        # Leads
        leads = (await session.execute(text("SELECT id, company_name, contact_name, status FROM lead_inquiries"))).fetchall()
        print(f"\nRemaining Lead Inquiries ({len(leads)}):")
        for l in leads:
            print(f"  - id={l[0]} company='{l[1]}' contact='{l[2]}' status='{l[3]}'")

    # MinIO
    client = StorageService.get_client()
    remaining_objs = list(client.list_objects(BUCKET_NAME, recursive=True))
    print(f"\nRemaining MinIO Objects ({len(remaining_objs)}):")
    for o in remaining_objs:
        print(f"  - {o.object_name} ({o.size} bytes)")

    print("\n--- Checkpoint 1.4 Status ---")
    assert len(tenants) == 3, f"Expected exactly 3 tenants (Master, Hapkonic, Marketza), got {len(tenants)}"
    assert len(users) == 4, f"Expected exactly 4 users (Super Admin, 2 Hapkonic, 1 Marketza), got {len(users)}"
    assert len(remaining_objs) == 8, f"Expected exactly 8 objects in MinIO, got {len(remaining_objs)}"
    print("SUCCESS: Checkpoint 1.4 PASSED! Only Hapkonic, Marketza, and Super Admin exist.")

async def main():
    await cleanup_postgres()
    cleanup_minio()
    await verify_checkpoint()

if __name__ == "__main__":
    asyncio.run(main())
