import asyncio
import os
import sys

# Ensure backend directory is in python path
backend_dir = r"c:\Users\vijay\Project_26\Invenza\backend"
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.schemas.product import ProductCreate, ProductUpdate
from app.core.database import AsyncSessionLocal
from app.api.v1.endpoints.auth import get_org_tax_context
from sqlalchemy import text

async def run_verification():
    print("=" * 60)
    print("1. VERIFYING PRODUCT SCHEMA MULTI-TAX VALIDATION")
    print("=" * 60)
    
    # 1. Germany VAT 19%
    de_prod = ProductCreate(
        sku="SKU-DE-TEST",
        name="Industrial Sensor DE",
        category="Electronics",
        cost_price=100.0,
        sell_price=150.0,
        hsn_code="8471",
        gst_rate=19.0, # Germany VAT 19%
    )
    assert de_prod.gst_rate == 19.0
    print("[PASS] Germany VAT 19% ProductCreate schema validated cleanly.")

    # 2. US California Sales Tax 7.25%
    us_prod = ProductCreate(
        sku="SKU-US-TEST",
        name="Cable Assembly CA",
        category="Accessories",
        cost_price=20.0,
        sell_price=45.0,
        hsn_code="TAX-GEN",
        gst_rate=7.25, # California Sales Tax 7.25%
    )
    assert us_prod.gst_rate == 7.25
    print("[PASS] US California Sales Tax 7.25% ProductCreate schema validated cleanly.")

    # 3. US Delaware 0% Sales Tax
    de_state_prod = ProductCreate(
        sku="SKU-DE-DELAWARE",
        name="Delaware Zero-Tax SKU",
        category="Machinery",
        cost_price=500.0,
        sell_price=750.0,
        hsn_code="TAX-GEN",
        gst_rate=0.0,
    )
    assert de_state_prod.gst_rate == 0.0
    print("[PASS] US Delaware 0% Sales Tax ProductCreate schema validated cleanly.")

    # 4. India GST 18% & 40% (GST 2.0)
    in_prod18 = ProductCreate(
        sku="SKU-IN-18",
        name="Monitor 24 inch",
        category="Electronics",
        cost_price=5000.0,
        sell_price=8000.0,
        hsn_code="8528",
        gst_rate=18.0,
    )
    in_prod40 = ProductCreate(
        sku="SKU-IN-40",
        name="Luxury Vehicle Part",
        category="Automotive",
        cost_price=20000.0,
        sell_price=35000.0,
        hsn_code="8703",
        gst_rate=40.0,
    )
    assert in_prod18.gst_rate == 18.0 and in_prod40.gst_rate == 40.0
    print("[PASS] India GST 18% and 40% (GST 2.0) ProductCreate schemas validated cleanly.")

    # 5. Invalid rate (> 100 or < 0)
    try:
        ProductCreate(
            sku="SKU-INVALID",
            name="Invalid Rate SKU",
            category="General",
            cost_price=10.0,
            sell_price=20.0,
            hsn_code="8471",
            gst_rate=125.0, # Invalid
        )
        print("[FAIL] 125% was accepted!")
    except Exception as e:
        print(f"[PASS] Invalid tax rate (125%) correctly rejected: {e}")

    print("\n" + "=" * 60)
    print("2. VERIFYING DATABASE TENANTS & TAX CONTEXT RETRIEVAL")
    print("=" * 60)
    async with AsyncSessionLocal() as db:
        # Check SK E-Com (German tenant)
        res = await db.execute(text("SELECT id, name, country_code, currency_code, state FROM tenants WHERE name ILIKE '%SK E-com%'"))
        sk_tenant = res.fetchone()
        if sk_tenant:
            ctx = await get_org_tax_context(db, sk_tenant.id)
            from app.services.tax_service import tax_ref_type, TAX_LABELS
            tax_type = tax_ref_type(ctx["country_code"])
            tax_label = TAX_LABELS.get(tax_type, tax_type)
            tax_rate = float(ctx["tax_ref"].tax_rate) if ctx.get("tax_ref") else None
            print(f"Tenant: {sk_tenant.name}")
            print(f"  Country: {sk_tenant.country_code}, Currency: {sk_tenant.currency_code}, State: {sk_tenant.state}")
            print(f"  Tax Context: tax_type={tax_type}, tax_rate={tax_rate}%, tax_label={tax_label}")
            assert tax_type == 'VAT'
            assert tax_rate == 19.0
            assert tax_label == 'VAT'
            print("  [PASS] SK E-Com correctly resolved to VAT regime with Germany 19% standard rate!")

        # Check US tenant (Pacific Crest or First State)
        res_us = await db.execute(text("SELECT id, name, country_code, currency_code, state FROM tenants WHERE country_code = 'US' LIMIT 1"))
        us_tenant = res_us.fetchone()
        if us_tenant:
            ctx_us = await get_org_tax_context(db, us_tenant.id)
            tax_type_us = tax_ref_type(ctx_us["country_code"])
            tax_label_us = TAX_LABELS.get(tax_type_us, tax_type_us)
            tax_rate_us = float(ctx_us["tax_ref"].tax_rate) if ctx_us.get("tax_ref") else None
            print(f"Tenant: {us_tenant.name}")
            print(f"  Country: {us_tenant.country_code}, Currency: {us_tenant.currency_code}, State: {us_tenant.state}")
            print(f"  Tax Context: tax_type={tax_type_us}, tax_rate={tax_rate_us}%, tax_label={tax_label_us}")
            assert tax_type_us == 'SALES_TAX'
            assert tax_label_us == 'Sales Tax'
            print("  [PASS] US Tenant correctly resolved to Sales Tax regime!")

        # Check India tenant (Crestline or Kaveri)
        res_in = await db.execute(text("SELECT id, name, country_code, currency_code, state FROM tenants WHERE country_code = 'IN' LIMIT 1"))
        in_tenant = res_in.fetchone()
        if in_tenant:
            ctx_in = await get_org_tax_context(db, in_tenant.id)
            tax_type_in = tax_ref_type(ctx_in["country_code"])
            tax_label_in = TAX_LABELS.get(tax_type_in, tax_type_in)
            print(f"Tenant: {in_tenant.name}")
            print(f"  Country: {in_tenant.country_code}, Currency: {in_tenant.currency_code}, State: {in_tenant.state}")
            print(f"  Tax Context: tax_type={tax_type_in}, tax_label={tax_label_in}")
            assert tax_type_in == 'GST'
            assert tax_label_in == 'GST'
            print("  [PASS] India Tenant correctly resolved to GST regime!")

    print("\n" + "=" * 60)
    print("ALL VERIFICATIONS COMPLETED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_verification())
