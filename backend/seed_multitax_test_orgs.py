"""
Multi-Currency / Multi-Tax Seed & Verification Script:
Provisions three cross-region test organizations and exercises the centralized
tax engine end-to-end through the REAL invoice service path:

- RHEINWERK  (Rheinland Werkzeugbau GmbH)  — Germany / EUR / VAT 19%
- PACCREST   (Pacific Crest Distribution Inc.) — US-California / USD / Sales Tax 7.25%
- FIRSTDL    (First State Logistics LLC)   — US-Delaware / USD / Sales Tax 0% (zero-rate edge case)

For each org it marks the setup fee paid via create_gst_invoice_for_billing and
asserts tax_type / rate / currency / totals, then renders the invoice PDF.

Finally it regression-checks an existing Indian GST org (CRESTLINE): its invoice
count and grand-total sum must be byte-identical before and after this run.

Run:  cd backend && python seed_multitax_test_orgs.py
Requires: database reachable (see .env / app/core/config.py), schema initialized
          (python app/db/init_db.py first — also seeds the tax_reference table).
"""

import asyncio
import sys
from pathlib import Path
from uuid import uuid4
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from sqlalchemy import select, func, text
from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.db.init_db import seed_tax_reference_table
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.models.location import Location
from app.models.product import Product
from app.models.ledger import StockMovement, MovementTypeEnum
from app.models.invoice import TenantSettings, TenantInvoiceSequence, Invoice, InvoiceItem
from app.models.billing import TenantBillingProfile, OrgSetupFee, OrgMaintenancePlan, OrgMaintenanceCycle
from app.models.audit_log import AuditLog
from app.api.v1.endpoints.billing import create_gst_invoice_for_billing, build_pdf_invoice_dict_from_tax
from app.services.invoice_pdf_generator import InvoicePdfGenerator

DEFAULT_PASSWORD = get_password_hash("Password123!")

# code, name, country, state_name, state_code, currency, industry, location,
# setup_fee, monthly_rate, expected (tax_type, rate, tax, grand)
ORGS = [
    {
        "code": "RHEINWERK", "name": "Rheinland Werkzeugbau GmbH",
        "country": "DE", "state_name": None, "state_code": "DE", "currency": "EUR",
        "industry": "Manufacturing & Assembly", "location": "Düsseldorf, Germany",
        "admin_email": "admin@rheinwerk.test", "admin_name": "Klaus Brandt",
        "setup_fee": 2400.00, "monthly_rate": 390.00,
        "expect": {"tax_type": "VAT", "rate": 19.00, "tax": 456.00, "grand": 2856.00},
    },
    {
        "code": "PACCREST", "name": "Pacific Crest Distribution Inc.",
        "country": "US", "state_name": "California", "state_code": "CA", "currency": "USD",
        "industry": "Logistics & Warehousing", "location": "Sacramento, California",
        "admin_email": "admin@paccrest.test", "admin_name": "Maria Santos",
        "setup_fee": 3000.00, "monthly_rate": 450.00,
        "expect": {"tax_type": "SALES_TAX", "rate": 7.25, "tax": 217.50, "grand": 3218.00},
    },
    {
        "code": "FIRSTDL", "name": "First State Logistics LLC",
        "country": "US", "state_name": "Delaware", "state_code": "DE", "currency": "USD",
        "industry": "Logistics & Warehousing", "location": "Wilmington, Delaware",
        "admin_email": "admin@firstdl.test", "admin_name": "James Halloran",
        "setup_fee": 2800.00, "monthly_rate": 420.00,
        "expect": {"tax_type": "SALES_TAX", "rate": 0.00, "tax": 0.00, "grand": 2800.00},
    },
]

INR_REGRESSION_CODE = "CRESTLINE"  # existing Indian GST org — must be untouched


def approx(a, b, tol=0.011):
    return abs(float(a) - float(b)) <= tol


async def cleanup_code(session, code: str):
    t_res = await session.execute(select(Tenant).where(Tenant.unique_code == code))
    t = t_res.scalar_one_or_none()
    if not t:
        return
    stmts = [
        "DELETE FROM invoice_items WHERE invoice_id IN (SELECT id FROM invoices WHERE tenant_id = '{id}')",
        "DELETE FROM invoices WHERE tenant_id = '{id}'",
        "DELETE FROM stock_movements WHERE tenant_id = '{id}'",
        "DELETE FROM products WHERE tenant_id = '{id}'",
        "DELETE FROM locations WHERE tenant_id = '{id}'",
        "DELETE FROM audit_logs WHERE tenant_id = '{id}'",
        "DELETE FROM org_maintenance_cycle WHERE org_id = '{id}'",
        "DELETE FROM org_maintenance_plan WHERE org_id = '{id}'",
        "DELETE FROM org_setup_fee WHERE org_id = '{id}'",
        "DELETE FROM tenant_billing_profiles WHERE tenant_id = '{id}'",
        "DELETE FROM tenant_invoice_sequences WHERE tenant_id = '{id}'",
        "DELETE FROM tenant_settings WHERE tenant_id = '{id}'",
        "DELETE FROM users WHERE tenant_id = '{id}'",
        "DELETE FROM tenants WHERE id = '{id}'",
    ]
    for s in stmts:
        await session.execute(text(s.format(id=t.id)))
    await session.flush()


async def snapshot_invoices(session, code: str):
    t_res = await session.execute(select(Tenant).where(Tenant.unique_code == code))
    t = t_res.scalar_one_or_none()
    if not t:
        return None
    cnt = await session.execute(select(func.count(Invoice.id)).where(Invoice.tenant_id == t.id))
    total = await session.execute(select(func.coalesce(func.sum(Invoice.grand_total), 0)).where(Invoice.tenant_id == t.id))
    snap = {"count": cnt.scalar_one(), "grand_sum": float(total.scalar_one() or 0.0)}
    print(f"[REGRESSION-SNAPSHOT] {code}: {snap['count']} invoices, grand_total sum = {snap['grand_sum']}")
    return snap


async def main():
    print("=== Multi-Currency / Multi-Tax Seed & Verification ===")
    async with AsyncSessionLocal() as session:
        # 0. Ensure the Tax Reference table is seeded (idempotent)
        await seed_tax_reference_table(session)
        await session.commit()

        # 1. Regression snapshot of an existing INR org BEFORE any changes
        before = await snapshot_invoices(session, INR_REGRESSION_CODE)

        # 2. Clean prior runs of the three multitax orgs
        for o in ORGS:
            await cleanup_code(session, o["code"])
        await session.commit()

        now = datetime.utcnow()
        current_month = now.strftime("%Y-%m")

        # 3. Provision each org + exercise the real invoice service path
        for o in ORGS:
            print(f"\n--- Provisioning {o['code']} ({o['country']}/{o['currency']}) ---")
            tid = uuid4()
            settings_state = o["state_name"] or ("Germany" if o["country"] == "DE" else o["country"])
            reg_addr = o["location"]
            tenant = Tenant(
                id=tid, name=o["name"], slug=o["code"].lower(),
                company_code=o["code"], unique_code=o["code"],
                industry=o["industry"], location=o["location"],
                state=o["state_name"], pincode=None,
                country_code=o["country"], currency_code=o["currency"],
                tier="Growth Suite",
                enabled_modules=["products", "locations", "orders", "transfers", "adjustments", "ledger", "reports", "storage"],
                is_active=True,
            )
            session.add(tenant)
            # NOTE: flush the Tenant BEFORE adding FK children — the UOW in this
            # codebase does not order tenants ahead of billing children within a
            # single flush (same reason app provisioning flushes the tenant first).
            await session.flush()
            session.add(User(
                tenant_id=tid, email=o["admin_email"], full_name=o["admin_name"],
                role=UserRole.ADMIN.value, hashed_password=DEFAULT_PASSWORD,
                permissions=["inventory:read", "inventory:write", "orders:manage", "team:manage", "reports:view", "storage:manage", "invoicing:manage"],
                is_active=True,
            ))
            session.add(TenantSettings(
                tenant_id=tid, legal_business_name=o["name"], gstin="",
                registered_address=reg_addr, state=settings_state,
                state_code=o["state_code"], pincode="",
                authorized_signatory_name=o["admin_name"], invoice_prefix="INV",
                bank_name="", bank_account_number="", bank_ifsc_code="",
                bank_branch="", account_holder_name="",
            ))
            session.add(TenantInvoiceSequence(tenant_id=tid, fiscal_year="2026-27", current_number=0))
            session.add(Location(
                id=uuid4(), tenant_id=tid, name="Primary Facility",
                code=f"{o['code']}-WH1", address=reg_addr, capacity=5000, is_active=True,
            ))
            for i, (sku, pname, price) in enumerate([
                ("SVC-PLATFORM", "Invenza Platform Subscription", o["monthly_rate"]),
                ("SKU-001", "Standard Stock-Keeping Unit", 100.0),
                ("SKU-002", "Secondary Stock-Keeping Unit", 250.0),
            ], 1):
                session.add(Product(
                    id=uuid4(), tenant_id=tid, sku=sku, name=pname,
                    category="Platform", unit_of_measure="pcs",
                    cost_price=price, sell_price=price, hsn_code="8471", gst_rate=18.00,
                    is_active=True,
                ))
            session.add(TenantBillingProfile(
                tenant_id=tid, setup_fee=o["setup_fee"], setup_fee_status="pending",
                monthly_maintenance_fee=o["monthly_rate"], maintenance_currency=o["currency"],
                billing_cycle_day=1,
            ))
            setup_fee_rec = OrgSetupFee(
                org_id=tid, amount=o["setup_fee"], status="Pending",
                recorded_by="Multi-Tax Seed Script", note="Cross-region setup fee",
            )
            session.add(setup_fee_rec)
            session.add(OrgMaintenancePlan(
                org_id=tid, current_rate=o["monthly_rate"], effective_from=now,
                changed_by="Multi-Tax Seed Script", reason="Initial agreed maintenance rate",
            ))
            session.add(OrgMaintenanceCycle(
                org_id=tid, cycle_month=current_month, amount=o["monthly_rate"],
                status="Pending", recorded_by="Multi-Tax Seed Script",
                note=f"Initial provisioning monthly cycle for {current_month}",
            ))
            session.add(AuditLog(
                actor_name="Multi-Tax Seed Script", actor_email="seed@invenza.internal",
                action_type="company_provisioned", target_type="tenant", target_id=str(tid),
                tenant_id=tid, tenant_name=o["name"],
                description=f"Provisioned cross-region test org {o['name']} ({o['country']}/{o['currency']})",
            ))
            await session.flush()

            # --- Exercise the REAL billing invoice path (same service the API uses) ---
            inv, inv_num = await create_gst_invoice_for_billing(
                db=session, tenant_id=tid, amount=o["setup_fee"],
                charge_type="setup_fee", description="Invenza Dedicated Platform Setup & Architecture Deployment",
                payment_date=now,
            )
            setup_fee_rec.status = "Paid"
            setup_fee_rec.date_paid = now
            setup_fee_rec.payment_mode = "Bank Transfer"
            setup_fee_rec.gst_invoice_id = inv.id
            setup_fee_rec.invoice_number = inv_num
            await session.flush()

            ex = o["expect"]
            items_res = await session.execute(select(InvoiceItem).where(InvoiceItem.invoice_id == inv.id))
            item = items_res.scalars().first()
            checks = [
                ("tax_type", inv.tax_type == ex["tax_type"], inv.tax_type),
                ("currency_code", inv.currency_code == o["currency"], inv.currency_code),
                ("taxable", approx(inv.total_taxable_value, o["setup_fee"]), float(inv.total_taxable_value)),
                ("single_tax", approx(inv.total_single_tax, ex["tax"]), float(inv.total_single_tax)),
                ("grand_total", approx(inv.grand_total, ex["grand"]), float(inv.grand_total)),
                ("item.single_tax_rate", approx(item.single_tax_rate, ex["rate"]), float(item.single_tax_rate)),
                ("zero GST cols", float(inv.total_cgst) == 0.0 and float(inv.total_igst) == 0.0, f"{inv.total_cgst}/{inv.total_igst}"),
            ]
            for label, ok, val in checks:
                status = "PASS" if ok else "FAIL"
                print(f"  [{status}] {label}: {val}")
                assert ok, f"{o['code']} assertion failed: {label} = {val}"
            print(f"  Invoice {inv_num}: {o['currency']} {float(inv.total_taxable_value):,.2f} + {ex['tax_type']} {float(inv.total_single_tax):,.2f} = {o['currency']} {float(inv.grand_total):,.2f}")

            # --- Render the actual PDF and persist for manual inspection ---
            pdf_dict = await build_pdf_invoice_dict_from_tax(
                db=session, tenant_id=tid, amount=o["setup_fee"], charge_type="setup_fee",
                desc="Invenza Dedicated Platform Setup & Architecture Deployment",
                invoice_number=inv_num, payment_date=now,
            )
            pdf_bytes = InvoicePdfGenerator.generate_invoice_pdf(pdf_dict)
            assert pdf_bytes and len(pdf_bytes) > 1000, f"PDF generation failed for {o['code']}"
            scratch = Path(__file__).resolve().parent / "scratch"
            scratch.mkdir(exist_ok=True)
            out = scratch / f"multitax_invoice_{o['code']}.pdf"
            out.write_bytes(pdf_bytes)
            print(f"  [PASS] PDF rendered ({len(pdf_bytes)} bytes) -> {out}")

        await session.commit()

        # 4. Regression: existing INR org must be untouched
        if before:
            after = await snapshot_invoices(session, INR_REGRESSION_CODE)
            assert after == before, f"REGRESSION: {INR_REGRESSION_CODE} invoices changed! {before} -> {after}"
            print(f"\n[REGRESSION-PASS] {INR_REGRESSION_CODE} invoices byte-identical after multitax seeding")

        print("\n=== Multi-Tax seed & verification COMPLETE ===")


if __name__ == "__main__":
    asyncio.run(main())
