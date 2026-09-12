import sys
sys.path.insert(0, r'c:\Users\vijay\Project_26\Invenza\backend')
import asyncio
from uuid import UUID
from fastapi import HTTPException
from app.core.database import AsyncSessionLocal
from app.models.tenant import Tenant
from app.models.product import Product
from app.models.ledger import StockMovement
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse
from app.services.tax_service import get_org_tax_context, validate_product_tax_for_org
from app.api.v1.endpoints.products import create_product, bulk_create_products, update_product
from sqlalchemy import select, delete

async def cleanup_skus(db, tenant_id, skus):
    prods = (await db.execute(select(Product).where(Product.tenant_id == tenant_id, Product.sku.in_(skus)))).scalars().all()
    if prods:
        p_ids = [p.id for p in prods]
        await db.execute(delete(StockMovement).where(StockMovement.tenant_id == tenant_id, StockMovement.product_id.in_(p_ids)))
        await db.execute(delete(Product).where(Product.tenant_id == tenant_id, Product.id.in_(p_ids)))
        await db.commit()

async def run_regression_tests():
    print("=== STARTING TAX IMPORT & COLUMN RENAME REGRESSION TESTS ===")

    # -------------------------------------------------------------
    # 1. Pydantic Schema Cross-Population & Aliasing Tests
    # -------------------------------------------------------------
    print("\n--- 1. Schema Cross-Population & Aliasing Tests ---")

    # 1a. New generic column names: tax_code & tax_rate
    p_generic = ProductCreate(sku="SKU-GEN-1", name="Generic Item", tax_code="8471.30", tax_rate=19.0)
    assert p_generic.tax_code == "8471.30"
    assert p_generic.hsn_code == "8471.30"
    assert p_generic.tax_rate == 19.0
    assert p_generic.gst_rate == 19.0
    print("  [PASS] ProductCreate correctly cross-populates tax_code -> hsn_code and tax_rate -> gst_rate")

    # 1b. Legacy column names: hsn_code & gst_rate
    p_legacy = ProductCreate(sku="SKU-LEG-1", name="Legacy Item", hsn_code="8528", gst_rate=18.0)
    assert p_legacy.tax_code == "8528"
    assert p_legacy.hsn_code == "8528"
    assert p_legacy.tax_rate == 18.0
    assert p_legacy.gst_rate == 18.0
    print("  [PASS] ProductCreate correctly cross-populates hsn_code -> tax_code and gst_rate -> tax_rate")

    # 1c. Blank tax_code (allowed for EU and US)
    p_blank = ProductCreate(sku="SKU-BLANK-1", name="Blank Code Item", tax_rate=7.25)
    assert p_blank.tax_code is None
    assert p_blank.hsn_code is None
    assert p_blank.tax_rate == 7.25
    assert p_blank.gst_rate == 7.25
    print("  [PASS] ProductCreate allows blank/None tax_code without forcing '8471'")

    # 1d. ProductUpdate aliasing
    u1 = ProductUpdate(tax_code="9401.30", tax_rate=7.0)
    assert u1.hsn_code == "9401.30"
    assert u1.gst_rate == 7.0
    u2 = ProductUpdate(hsn_code="9401.30", gst_rate=7.0)
    assert u2.tax_code == "9401.30"
    assert u2.tax_rate == 7.0
    print("  [PASS] ProductUpdate cross-populates bidirectionally")

    # -------------------------------------------------------------
    # 2. Database & Endpoint-Level Integration Tests
    # -------------------------------------------------------------
    print("\n--- 2. Database & Endpoint Integration Tests ---")
    async with AsyncSessionLocal() as db:
        tenants = (await db.execute(select(Tenant))).scalars().all()
        by_country = {}
        for t in tenants:
            by_country.setdefault(t.country_code or "IN", t)

        in_tenant = by_country.get("IN")
        de_tenant = by_country.get("DE")
        us_tenant = by_country.get("US")

        # --- A. India GST Organization ---
        if in_tenant:
            print(f"\n[Testing India GST Org: '{in_tenant.name}' ({in_tenant.id})]")
            in_skus = ["TEST-IN-01", "TEST-IN-02", "TEST-IN-03", "TEST-IN-04", "TEST-IN-BULK-01", "TEST-IN-BULK-02"]
            await cleanup_skus(db, in_tenant.id, in_skus)

            # A1: Create product with new tax_code & tax_rate
            res1 = await create_product(
                product_in=ProductCreate(sku="TEST-IN-01", name="GST Mouse", tax_code="8471", tax_rate=18.0, cost_price=500.0, sell_price=999.0),
                tenant_id=in_tenant.id,
                db=db,
            )
            assert res1.hsn_code == "8471"
            assert res1.tax_code == "8471"
            assert res1.gst_rate == 18.0
            assert res1.tax_rate == 18.0
            print("  [PASS] India create_product with tax_code='8471' and tax_rate=18.0 succeeded")

            # A2: Create product with legacy hsn_code & gst_rate
            res2 = await create_product(
                product_in=ProductCreate(sku="TEST-IN-02", name="GST Keyboard", hsn_code="8471", gst_rate=18.0, cost_price=600.0, sell_price=1200.0),
                tenant_id=in_tenant.id,
                db=db,
            )
            assert res2.hsn_code == "8471"
            assert res2.tax_code == "8471"
            assert res2.gst_rate == 18.0
            assert res2.tax_rate == 18.0
            print("  [PASS] India create_product with legacy hsn_code='8471' and gst_rate=18.0 succeeded (Regression Check Passed)")

            # A3: Bulk import for India org
            bulk_res = await bulk_create_products(
                products_in=[
                    ProductCreate(sku="TEST-IN-BULK-01", name="Bulk Monitor", tax_code="8528", tax_rate=18.0, initial_stock=10),
                    ProductCreate(sku="TEST-IN-BULK-02", name="Bulk Cable", tax_code="8544", tax_rate=5.0, initial_stock=50),
                ],
                tenant_id=in_tenant.id,
                db=db,
            )
            assert len(bulk_res) == 2
            assert bulk_res[0].tax_code == "8528" and bulk_res[0].tax_rate == 18.0
            assert bulk_res[1].tax_code == "8544" and bulk_res[1].tax_rate == 5.0
            print("  [PASS] India bulk_create_products with tax_code & tax_rate succeeded")

            # A4: Missing tax_code for India -> MUST BE REJECTED
            try:
                await create_product(
                    product_in=ProductCreate(sku="TEST-IN-03", name="Missing Tax Code", tax_rate=18.0),
                    tenant_id=in_tenant.id,
                    db=db,
                )
                assert False, "Should have rejected missing tax_code for India"
            except HTTPException as e:
                assert e.status_code == 400
                assert "tax_code" in e.detail or "HSN" in e.detail
                print(f"  [PASS] India rejected missing tax_code correctly: '{e.detail}'")

            # A5: Invalid GST slab (e.g. 17.0%) -> MUST BE REJECTED
            try:
                await create_product(
                    product_in=ProductCreate(sku="TEST-IN-04", name="Invalid Slab", tax_code="8471", tax_rate=17.0),
                    tenant_id=in_tenant.id,
                    db=db,
                )
                assert False, "Should have rejected 17% for India"
            except HTTPException as e:
                assert e.status_code == 400
                assert "Allowed GST rates" in e.detail
                print(f"  [PASS] India rejected invalid GST rate (17%) correctly: '{e.detail}'")

            # Cleanup India test SKUs
            await cleanup_skus(db, in_tenant.id, in_skus)

        # --- B. Germany (EU VAT) Organization (e.g. SK E-Com) ---
        if de_tenant:
            print(f"\n[Testing Germany VAT Org: '{de_tenant.name}' ({de_tenant.id})]")
            de_skus = ["TEST-DE-01", "TEST-DE-02", "TEST-DE-03", "TEST-DE-BULK-01", "TEST-DE-BULK-02"]
            await cleanup_skus(db, de_tenant.id, de_skus)

            # B1: Create with blank tax_code and standard 19% VAT
            res_de1 = await create_product(
                product_in=ProductCreate(sku="TEST-DE-01", name="German Laser Mouse", tax_rate=19.0, cost_price=40.0, sell_price=79.99),
                tenant_id=de_tenant.id,
                db=db,
            )
            assert res_de1.tax_code is None or res_de1.tax_code == ""
            assert res_de1.tax_rate == 19.0
            print("  [PASS] Germany create_product with blank tax_code and 19% VAT succeeded")

            # B2: Create with Taric commodity code and reduced 7% VAT
            res_de2 = await create_product(
                product_in=ProductCreate(sku="TEST-DE-02", name="Technical Documentation", tax_code="4901.99", tax_rate=7.0, cost_price=10.0, sell_price=25.0),
                tenant_id=de_tenant.id,
                db=db,
            )
            assert res_de2.tax_code == "4901.99"
            assert res_de2.tax_rate == 7.0
            print("  [PASS] Germany create_product with Taric code '4901.99' and reduced rate 7% succeeded")

            # B3: Bulk import with mixed Taric and blank tax_codes
            bulk_res_de = await bulk_create_products(
                products_in=[
                    ProductCreate(sku="TEST-DE-BULK-01", name="EU Monitor", tax_code="8528.52", tax_rate=19.0, initial_stock=5),
                    ProductCreate(sku="TEST-DE-BULK-02", name="EU Cable (No Code)", tax_rate=19.0, initial_stock=20),
                ],
                tenant_id=de_tenant.id,
                db=db,
            )
            assert len(bulk_res_de) == 2
            assert bulk_res_de[0].tax_code == "8528.52" and bulk_res_de[0].tax_rate == 19.0
            assert (bulk_res_de[1].tax_code is None or bulk_res_de[1].tax_code == "") and bulk_res_de[1].tax_rate == 19.0
            print("  [PASS] Germany bulk_create_products with optional tax_code succeeded")

            # B4: Invalid VAT rate (e.g. 50%) -> MUST BE REJECTED
            try:
                await create_product(
                    product_in=ProductCreate(sku="TEST-DE-03", name="Invalid Rate Item", tax_rate=50.0),
                    tenant_id=de_tenant.id,
                    db=db,
                )
                assert False, "Should have rejected 50% VAT rate"
            except HTTPException as e:
                assert e.status_code == 400
                assert "Applicable VAT rates" in e.detail
                print(f"  [PASS] Germany rejected invalid VAT rate (50%) correctly: '{e.detail}'")

            # Cleanup Germany test SKUs
            await cleanup_skus(db, de_tenant.id, de_skus)

        # --- C. US (Sales Tax) Organization ---
        if us_tenant:
            print(f"\n[Testing US Sales Tax Org: '{us_tenant.name}' ({us_tenant.id})]")
            us_ctx = await get_org_tax_context(db, us_tenant.id)
            std_rate = float(us_ctx["tax_ref"].tax_rate) if us_ctx.get("tax_ref") else 0.0

            us_skus = ["TEST-US-01", "TEST-US-02"]
            await cleanup_skus(db, us_tenant.id, us_skus)

            # C1: Create with blank tax_code and valid sales tax rate
            res_us1 = await create_product(
                product_in=ProductCreate(sku="TEST-US-01", name="US Wireless Mouse", tax_rate=std_rate, cost_price=25.0, sell_price=49.99),
                tenant_id=us_tenant.id,
                db=db,
            )
            assert res_us1.tax_code is None or res_us1.tax_code == ""
            assert res_us1.tax_rate == std_rate
            print(f"  [PASS] US create_product with blank tax_code and {std_rate}% rate succeeded")

            # C2: Invalid Sales Tax rate (e.g. 35%) -> MUST BE REJECTED
            try:
                await create_product(
                    product_in=ProductCreate(sku="TEST-US-02", name="US High Tax", tax_rate=35.0),
                    tenant_id=us_tenant.id,
                    db=db,
                )
                assert False, "Should have rejected 35% sales tax"
            except HTTPException as e:
                assert e.status_code == 400
                print(f"  [PASS] US rejected invalid Sales Tax rate (35%) correctly: '{e.detail}'")

            # Cleanup US test SKUs
            await cleanup_skus(db, us_tenant.id, us_skus)

    print("\n=======================================================")
    print("ALL REGRESSION & INTEGRATION TESTS COMPLETED SUCCESSFULLY!")
    print("=======================================================")

if __name__ == '__main__':
    asyncio.run(run_regression_tests())
