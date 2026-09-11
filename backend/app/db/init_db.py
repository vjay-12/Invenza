"""
Database initialization, auto-migration, and enterprise seed script.
Ensures Super Admin, master tenant, and multi-tenant schema are ready.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import asyncio
from datetime import datetime
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, func, and_

from app.core.database import AsyncSessionLocal, engine, Base
from app.core.security import get_password_hash
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.models.location import Location
from app.models.product import Product
from app.models.ledger import StockMovement, MovementTypeEnum
from app.models.invoice import TenantSettings, TenantInvoiceSequence, Customer, Invoice, InvoiceItem
from app.models.lead import LeadInquiry
from app.models.audit_log import AuditLog
from app.models.security_request import SecurityApprovalRequest
from app.models.billing import (
    TenantBillingProfile,
    BillingFeeHistory,
    BillingPaymentRecord,
    OrgSetupFee,
    OrgMaintenancePlan,
    OrgMaintenanceCycle,
)

MASTER_TENANT_ID = UUID("00000000-0000-0000-0000-000000000000")

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
            "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS company_code VARCHAR(50);",
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_tenants_company_code ON tenants (company_code);",
            "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS unique_code VARCHAR(50);",
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_tenants_unique_code ON tenants (unique_code);",
            "UPDATE tenants SET unique_code = company_code WHERE unique_code IS NULL AND company_code IS NOT NULL;",
            "UPDATE tenants SET company_code = unique_code WHERE company_code IS NULL AND unique_code IS NOT NULL;",
            "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS industry VARCHAR(100) DEFAULT 'General Merchandise';",
            "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS location VARCHAR(255) DEFAULT 'Headquarters';",
            "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS enabled_modules JSONB DEFAULT '[\"products\",\"locations\",\"orders\",\"transfers\",\"adjustments\",\"ledger\",\"reports\",\"storage\"]'::jsonb;",
            "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;",
            "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS is_archived BOOLEAN DEFAULT FALSE;",
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

        # Alter products table for GST & HSN fields
        alter_products = [
            "ALTER TABLE products ADD COLUMN IF NOT EXISTS hsn_code VARCHAR(20) DEFAULT '8471';",
            "ALTER TABLE products ADD COLUMN IF NOT EXISTS gst_rate NUMERIC(5,2) DEFAULT 18.00;",
        ]
        for stmt in alter_products:
            try:
                await conn.execute(text(stmt))
            except Exception as e:
                print(f"[Schema Migration Warning - products]: {e}")

        # Alter sales_orders table for customer GST & invoice fields
        alter_orders = [
            "ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS customer_gstin VARCHAR(15);",
            "ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS billing_address TEXT;",
            "ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS billing_state VARCHAR(100);",
            "ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS billing_state_code VARCHAR(2);",
            "ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS shipping_address TEXT;",
            "ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS shipping_state VARCHAR(100);",
            "ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS shipping_state_code VARCHAR(2);",
            "ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS state VARCHAR(100) DEFAULT 'Karnataka';",
            "ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS state_code VARCHAR(2) DEFAULT '29';",
            "ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS invoice_id UUID;",
        ]
        for stmt in alter_orders:
            try:
                await conn.execute(text(stmt))
            except Exception as e:
                print(f"[Schema Migration Warning - sales_orders]: {e}")

        # Alter customers table for bill-to & ship-to state data
        alter_customers = [
            "ALTER TABLE customers ADD COLUMN IF NOT EXISTS billing_state VARCHAR(100);",
            "ALTER TABLE customers ADD COLUMN IF NOT EXISTS billing_state_code VARCHAR(2);",
            "ALTER TABLE customers ADD COLUMN IF NOT EXISTS shipping_state VARCHAR(100);",
            "ALTER TABLE customers ADD COLUMN IF NOT EXISTS shipping_state_code VARCHAR(2);",
        ]
        for stmt in alter_customers:
            try:
                await conn.execute(text(stmt))
            except Exception as e:
                print(f"[Schema Migration Warning - customers]: {e}")

        # Alter tenants for tier, tags, state & pincode
        alter_tenants_v2 = [
            "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS tier VARCHAR(100) DEFAULT 'Growth Suite';",
            "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS tags JSONB DEFAULT '[]'::jsonb;",
            "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS state VARCHAR(100);",
            "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS pincode VARCHAR(10);",
        ]
        for stmt in alter_tenants_v2:
            try:
                await conn.execute(text(stmt))
            except Exception as e:
                print(f"[Schema Migration Warning - tenants v2]: {e}")

        # Alter lead_inquiries for quoted_amount, converted_tenant_id, state & pincode
        alter_leads = [
            "ALTER TABLE lead_inquiries ADD COLUMN IF NOT EXISTS quoted_amount NUMERIC(12,2) DEFAULT 0.00;",
            "ALTER TABLE lead_inquiries ADD COLUMN IF NOT EXISTS converted_tenant_id UUID;",
            "ALTER TABLE lead_inquiries ADD COLUMN IF NOT EXISTS state VARCHAR(100);",
            "ALTER TABLE lead_inquiries ADD COLUMN IF NOT EXISTS pincode VARCHAR(10);",
        ]
        for stmt in alter_leads:
            try:
                await conn.execute(text(stmt))
            except Exception as e:
                print(f"[Schema Migration Warning - lead_inquiries]: {e}")

        # Alter tenant_settings for pincode
        try:
            await conn.execute(text("ALTER TABLE tenant_settings ADD COLUMN IF NOT EXISTS pincode VARCHAR(10) DEFAULT '560103';"))
        except Exception as e:
            print(f"[Schema Migration Warning - tenant_settings pincode]: {e}")

        # Alter billing_payment_records for GST tax and sequential invoice fields
        alter_billing_payments = [
            "ALTER TABLE billing_payment_records ADD COLUMN IF NOT EXISTS invoice_number VARCHAR(100);",
            "CREATE INDEX IF NOT EXISTS ix_billing_payment_records_invoice_number ON billing_payment_records (invoice_number);",
            "ALTER TABLE billing_payment_records ADD COLUMN IF NOT EXISTS invoice_date TIMESTAMP;",
            "ALTER TABLE billing_payment_records ADD COLUMN IF NOT EXISTS taxable_amount NUMERIC(12,2) DEFAULT 0.00;",
            "ALTER TABLE billing_payment_records ADD COLUMN IF NOT EXISTS gst_rate NUMERIC(5,2) DEFAULT 18.00;",
            "ALTER TABLE billing_payment_records ADD COLUMN IF NOT EXISTS cgst_amount NUMERIC(12,2) DEFAULT 0.00;",
            "ALTER TABLE billing_payment_records ADD COLUMN IF NOT EXISTS sgst_amount NUMERIC(12,2) DEFAULT 0.00;",
            "ALTER TABLE billing_payment_records ADD COLUMN IF NOT EXISTS igst_amount NUMERIC(12,2) DEFAULT 0.00;",
            "ALTER TABLE billing_payment_records ADD COLUMN IF NOT EXISTS total_amount NUMERIC(12,2) DEFAULT 0.00;",
            "ALTER TABLE billing_payment_records ADD COLUMN IF NOT EXISTS sac_code VARCHAR(20) DEFAULT '998313';",
        ]
        for stmt in alter_billing_payments:
            try:
                await conn.execute(text(stmt))
            except Exception as e:
                print(f"[Schema Migration Warning - billing_payment_records]: {e}")

        # Explicit Distinct Billing Tables: org_setup_fee, org_maintenance_plan, org_maintenance_cycle
        create_billing_tables = [
            """
            CREATE TABLE IF NOT EXISTS org_setup_fee (
                id UUID PRIMARY KEY,
                org_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
                status VARCHAR(50) NOT NULL DEFAULT 'Pending',
                date_paid TIMESTAMP,
                payment_mode VARCHAR(50),
                recorded_by VARCHAR(255),
                note TEXT,
                gst_invoice_id UUID REFERENCES invoices(id) ON DELETE SET NULL,
                invoice_number VARCHAR(100),
                gateway_transaction_id VARCHAR(255),
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """,
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_org_setup_fee_org_id ON org_setup_fee (org_id);",
            "CREATE INDEX IF NOT EXISTS ix_org_setup_fee_status ON org_setup_fee (status);",
            "CREATE INDEX IF NOT EXISTS ix_org_setup_fee_invoice_number ON org_setup_fee (invoice_number);",
            """
            CREATE TABLE IF NOT EXISTS org_maintenance_plan (
                id UUID PRIMARY KEY,
                org_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                current_rate NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
                effective_from TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                changed_by VARCHAR(255),
                reason TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """,
            "CREATE INDEX IF NOT EXISTS ix_org_maintenance_plan_org_id ON org_maintenance_plan (org_id);",
            "CREATE INDEX IF NOT EXISTS ix_org_maintenance_plan_effective_from ON org_maintenance_plan (effective_from);",
            """
            CREATE TABLE IF NOT EXISTS org_maintenance_cycle (
                id UUID PRIMARY KEY,
                org_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                cycle_month VARCHAR(20) NOT NULL,
                amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
                status VARCHAR(50) NOT NULL DEFAULT 'Pending',
                date_paid TIMESTAMP,
                payment_mode VARCHAR(50),
                recorded_by VARCHAR(255),
                note TEXT,
                gst_invoice_id UUID REFERENCES invoices(id) ON DELETE SET NULL,
                invoice_number VARCHAR(100),
                gateway_transaction_id VARCHAR(255),
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """,
            "CREATE INDEX IF NOT EXISTS ix_org_maintenance_cycle_org_id ON org_maintenance_cycle (org_id);",
            "CREATE INDEX IF NOT EXISTS ix_org_maintenance_cycle_cycle_month ON org_maintenance_cycle (cycle_month);",
            "CREATE INDEX IF NOT EXISTS ix_org_maintenance_cycle_status ON org_maintenance_cycle (status);",
            "CREATE INDEX IF NOT EXISTS ix_org_maintenance_cycle_invoice_number ON org_maintenance_cycle (invoice_number);",
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_org_maintenance_cycle_org_month ON org_maintenance_cycle (org_id, cycle_month);",
        ]
        for stmt in create_billing_tables:
            try:
                await conn.execute(text(stmt))
            except Exception as e:
                print(f"[Schema Migration Warning - create_billing_tables]: {e}")


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
                company_code="INVENZAM",
                unique_code="INVENZAM",
                industry="Enterprise Platform",
                location="Global Cloud Core",
                currency_code="INR",
                enabled_modules=["companies", "analytics", "reports", "settings"],
                is_active=True,
            )
            session.add(master_tenant)
            await session.flush()
        else:
            if not master_tenant.company_code:
                master_tenant.company_code = "INVENZAM"
            if not master_tenant.unique_code:
                master_tenant.unique_code = master_tenant.company_code

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

        # 3. Seed TenantSettings and InvoiceSequence for all existing tenants
        all_tenants_res = await session.execute(select(Tenant))
        all_tenants = all_tenants_res.scalars().all()
        for t in all_tenants:
            sett_res = await session.execute(select(TenantSettings).where(TenantSettings.tenant_id == t.id))
            if not sett_res.scalar_one_or_none():
                session.add(TenantSettings(
                    tenant_id=t.id,
                    legal_business_name=f"{t.name} Pvt Ltd",
                    gstin="29AABCI1234F1Z5",
                    pan="AABCI1234F",
                    registered_address=f"Plot 42, {t.name} Complex, Tech Zone, Outer Ring Road, Bengaluru, Karnataka 560103",
                    state="Karnataka",
                    state_code="29",
                    authorized_signatory_name="Vijay B",
                    bank_name="HDFC Bank",
                    bank_account_number="50200012345678",
                    bank_ifsc_code="HDFC0001234",
                    bank_branch="Koramangala 5th Block, Bengaluru",
                    account_holder_name=f"{t.name} Pvt Ltd",
                    invoice_prefix="INV",
                    auto_email_invoice=False,
                ))

            seq_res = await session.execute(select(TenantInvoiceSequence).where(TenantInvoiceSequence.tenant_id == t.id))
            if not seq_res.scalar_one_or_none():
                session.add(TenantInvoiceSequence(
                    tenant_id=t.id,
                    fiscal_year="2026-27",
                    current_number=0,
                ))

            # 7. Seed TenantBillingProfile
            billing_res = await session.execute(select(TenantBillingProfile).where(TenantBillingProfile.tenant_id == t.id))
            billing_prof = billing_res.scalar_one_or_none()
            if not billing_prof:
                if t.id == MASTER_TENANT_ID:
                    session.add(TenantBillingProfile(
                        tenant_id=t.id,
                        setup_fee=0.00,
                        setup_fee_status="waived",
                        monthly_maintenance_fee=0.00,
                        maintenance_currency="INR",
                        billing_cycle_day=1,
                    ))
                else:
                    setup_val = 25000.00
                    maint_val = 4500.00
                    session.add(TenantBillingProfile(
                        tenant_id=t.id,
                        setup_fee=setup_val,
                        setup_fee_status="paid",
                        setup_fee_paid_at=datetime.utcnow(),
                        setup_fee_payment_mode="manual",
                        setup_fee_recorded_by="Super Admin (Billing Engine)",
                        monthly_maintenance_fee=maint_val,
                        maintenance_currency="INR",
                        billing_cycle_day=1,
                        last_payment_date=datetime.utcnow(),
                        next_due_date=datetime(2026, 10, 1),
                    ))
                    # Seed cycle payment record
                    session.add(BillingPaymentRecord(
                        tenant_id=t.id,
                        cycle_month="2026-09",
                        charge_type="monthly_maintenance",
                        amount=maint_val,
                        status="paid",
                        payment_mode="manual",
                        payment_reference=f"PAY-{t.company_code or 'INV'}-202609",
                        paid_at=datetime.utcnow(),
                        recorded_by="Super Admin",
                        line_items=[{
                            "description": "Enterprise Core Monthly Maintenance & Infrastructure Telemetry",
                            "amount": float(maint_val),
                            "type": "monthly_maintenance",
                        }],
                        notes="Cycle settled on-time via NEFT transfer.",
                    ))

        # 7b. Seed / Migrate to distinct Billing Tables (org_setup_fee, org_maintenance_plan, org_maintenance_cycle)
        all_tenants_res = await session.execute(select(Tenant).where(Tenant.id != MASTER_TENANT_ID))
        all_non_master_tenants = all_tenants_res.scalars().all()
        current_month_str = datetime.utcnow().strftime("%Y-%m")

        for t in all_non_master_tenants:
            # 1. OrgSetupFee
            sf_res = await session.execute(select(OrgSetupFee).where(OrgSetupFee.org_id == t.id))
            sf = sf_res.scalar_one_or_none()
            if not sf:
                bp_res = await session.execute(select(TenantBillingProfile).where(TenantBillingProfile.tenant_id == t.id))
                bp = bp_res.scalar_one_or_none()
                sf_amt = float(bp.setup_fee) if bp else 25000.0
                sf_st = "Paid" if (bp and bp.setup_fee_status == "paid") else "Pending"
                session.add(OrgSetupFee(
                    org_id=t.id,
                    amount=sf_amt,
                    status=sf_st,
                    date_paid=bp.setup_fee_paid_at if (bp and sf_st == "Paid") else None,
                    payment_mode=bp.setup_fee_payment_mode if (bp and sf_st == "Paid") else None,
                    recorded_by=bp.setup_fee_recorded_by if bp else "Super Admin",
                    note="Initial enterprise setup fee",
                ))

            # 2. OrgMaintenancePlan
            mp_res = await session.execute(select(OrgMaintenancePlan).where(OrgMaintenancePlan.org_id == t.id))
            if not mp_res.scalars().first():
                bp_res = await session.execute(select(TenantBillingProfile).where(TenantBillingProfile.tenant_id == t.id))
                bp = bp_res.scalar_one_or_none()
                plan_rate = float(bp.monthly_maintenance_fee) if bp else 4500.0
                session.add(OrgMaintenancePlan(
                    org_id=t.id,
                    current_rate=plan_rate,
                    effective_from=t.created_at or datetime.utcnow(),
                    changed_by="Super Admin",
                    reason="Initial agreed maintenance rate",
                ))

            # 3. OrgMaintenanceCycle
            mc_res = await session.execute(
                select(OrgMaintenanceCycle).where(
                    and_(OrgMaintenanceCycle.org_id == t.id, OrgMaintenanceCycle.cycle_month == current_month_str)
                )
            )
            if not mc_res.scalar_one_or_none():
                bp_res = await session.execute(select(TenantBillingProfile).where(TenantBillingProfile.tenant_id == t.id))
                bp = bp_res.scalar_one_or_none()
                cycle_amt = float(bp.monthly_maintenance_fee) if bp else 4500.0
                session.add(OrgMaintenanceCycle(
                    org_id=t.id,
                    cycle_month=current_month_str,
                    amount=cycle_amt,
                    status="Pending",
                    recorded_by="System Auto-Billing",
                    note=f"Monthly maintenance cycle for {current_month_str}",
                ))


        # 8. Seed initial AuditLog entries if table is empty
        audit_count_res = await session.execute(select(func.count(AuditLog.id)))
        if (audit_count_res.scalar_one() or 0) == 0:
            session.add(AuditLog(
                actor_name="Super Administrator",
                actor_email="superadmin@invenza.internal",
                action_type="system_initialized",
                target_type="system",
                target_id="00000000-0000-0000-0000-000000000000",
                tenant_id=MASTER_TENANT_ID,
                tenant_name="Invenza Master Platform",
                description="Invenza platform database and security safeguards initialized.",
                after_values={"status": "ready"},
            ))

        await session.commit()
        print("Invenza database initialization, Super Admin seeding, and schema migration complete.")

if __name__ == "__main__":
    asyncio.run(init_db())
