"""
Phase 2 Provisioning Script:
Creates exactly 5 specialized test organizations with realistic seed data:
- Org A: AeroTech Dynamics (Inventory & SKU catalog)
- Org B: BlueDart Logistics Hub (Stock Transfers & Movement Ledger)
- Org C: Crestline Global Trade (POs, SOs, GST Invoicing)
- Org D: Delta Health Diagnostics (Role Management & RBAC Safeguards)
- Org E: E-Commerce Express (Billing Engine & Security Safeguards)

Verifies total client organizations count = 7 (Hapkonic + Marketza + 5 new).
"""

import asyncio
import sys
from pathlib import Path
from uuid import uuid4, UUID
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sqlalchemy import select, text
from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.models.location import Location
from app.models.product import Product
from app.models.ledger import StockMovement, MovementTypeEnum
from app.models.order import (
    PurchaseOrder,
    PurchaseOrderItem,
    SalesOrder,
    SalesOrderItem,
    OrderStatus,
)
from app.models.transfer import StockTransfer, StockTransferItem
from app.models.invoice import TenantSettings, TenantInvoiceSequence, Invoice, InvoiceItem, InvoiceStatus
from app.models.billing import (
    TenantBillingProfile,
    OrgSetupFee,
    OrgMaintenancePlan,
    OrgMaintenanceCycle,
)
from app.models.security_request import SecurityApprovalRequest
from app.models.audit_log import AuditLog

DEFAULT_PASSWORD = get_password_hash("Password123!")

TEST_CODES = ("AEROTECH", "BLUEDART", "CRESTLINE", "DELTAHLTH", "ECOMMEXP")

async def seed_orgs():
    print("\n--- Provisioning 5 Fresh Test Organizations ---")
    async with AsyncSessionLocal() as session:
        # Clean any prior partial test orgs by code
        for code in TEST_CODES:
            t_res = await session.execute(select(Tenant).where(Tenant.unique_code == code))
            t = t_res.scalar_one_or_none()
            if t:
                # delete cascading
                await session.execute(text(f"DELETE FROM stock_transfer_items WHERE transfer_id IN (SELECT id FROM stock_transfers WHERE tenant_id = '{t.id}')"))
                await session.execute(text(f"DELETE FROM stock_transfers WHERE tenant_id = '{t.id}'"))
                await session.execute(text(f"DELETE FROM sales_order_items WHERE order_id IN (SELECT id FROM sales_orders WHERE tenant_id = '{t.id}')"))
                await session.execute(text(f"DELETE FROM sales_orders WHERE tenant_id = '{t.id}'"))
                await session.execute(text(f"DELETE FROM purchase_order_items WHERE order_id IN (SELECT id FROM purchase_orders WHERE tenant_id = '{t.id}')"))
                await session.execute(text(f"DELETE FROM purchase_orders WHERE tenant_id = '{t.id}'"))
                await session.execute(text(f"DELETE FROM stock_adjustments WHERE tenant_id = '{t.id}'"))
                await session.execute(text(f"DELETE FROM stock_movements WHERE tenant_id = '{t.id}'"))
                await session.execute(text(f"DELETE FROM invoice_items WHERE invoice_id IN (SELECT id FROM invoices WHERE tenant_id = '{t.id}')"))
                await session.execute(text(f"DELETE FROM invoices WHERE tenant_id = '{t.id}'"))
                await session.execute(text(f"DELETE FROM products WHERE tenant_id = '{t.id}'"))
                await session.execute(text(f"DELETE FROM locations WHERE tenant_id = '{t.id}'"))
                await session.execute(text(f"DELETE FROM security_approval_requests WHERE tenant_id = '{t.id}'"))
                await session.execute(text(f"DELETE FROM audit_logs WHERE tenant_id = '{t.id}'"))
                await session.execute(text(f"DELETE FROM org_maintenance_cycle WHERE org_id = '{t.id}'"))
                await session.execute(text(f"DELETE FROM org_maintenance_plan WHERE org_id = '{t.id}'"))
                await session.execute(text(f"DELETE FROM org_setup_fee WHERE org_id = '{t.id}'"))
                await session.execute(text(f"DELETE FROM tenant_billing_profiles WHERE tenant_id = '{t.id}'"))
                await session.execute(text(f"DELETE FROM tenant_invoice_sequences WHERE tenant_id = '{t.id}'"))
                await session.execute(text(f"DELETE FROM tenant_settings WHERE tenant_id = '{t.id}'"))
                await session.execute(text(f"DELETE FROM users WHERE tenant_id = '{t.id}'"))
                await session.execute(text(f"DELETE FROM tenants WHERE id = '{t.id}'"))
                await session.flush()

        now = datetime.utcnow()
        current_month = now.strftime("%Y-%m")

        # ==========================================================
        # ORG A: AeroTech Dynamics (Core Inventory & SKU Management)
        # ==========================================================
        org_a_id = uuid4()
        org_a = Tenant(
            id=org_a_id,
            name="AeroTech Dynamics",
            slug="aerotech-dynamics",
            company_code="AEROTECH",
            unique_code="AEROTECH",
            industry="Aerospace & Defense",
            location="Whitefield Tech Hub, Bengaluru, Karnataka",
            tier="Enterprise Global",
            currency_code="INR",
            is_active=True,
            enabled_modules=["products", "locations", "orders", "transfers", "adjustments", "ledger", "reports", "storage"],
        )
        session.add(org_a)
        await session.flush()

        session.add(User(
            tenant_id=org_a_id,
            email="admin@aerotech.test",
            full_name="Vikram Sarabhai",
            role=UserRole.ADMIN.value,
            hashed_password=DEFAULT_PASSWORD,
            permissions=["inventory:read", "inventory:write", "orders:manage", "team:manage", "reports:view", "settings:manage"],
            is_active=True,
        ))
        session.add(User(
            tenant_id=org_a_id,
            email="ops@aerotech.test",
            full_name="Ananya Rao",
            role=UserRole.MANAGER.value,
            hashed_password=DEFAULT_PASSWORD,
            permissions=["inventory:read", "inventory:write", "orders:manage", "reports:view"],
            is_active=True,
        ))

        loc_a_id = uuid4()
        loc_a = Location(
            id=loc_a_id,
            tenant_id=org_a_id,
            name="AeroTech Central Depot",
            code="ATC-01",
            address="Plot 18, EPIP Zone, Whitefield, Bengaluru",
            capacity=50000,
            is_active=True,
        )
        session.add(loc_a)
        await session.flush()

        skus_a = [
            ("SKU-AT-TITAN", "Titanium Alloy Fastener Grade-5", "Fasteners", "pcs", 120.0, 280.0, "890123451001", 50, "7318", 18.0, 250),
            ("SKU-AT-MICRO", "Radiation-Hardened Microcontroller", "Semiconductors", "pcs", 450.0, 980.0, "890123451002", 20, "8542", 18.0, 85),
            ("SKU-AT-FIBER", "Carbon Fiber Composite Panel 2x1m", "Raw Materials", "pcs", 850.0, 1650.0, "890123451003", 15, "6815", 18.0, 40),
            ("SKU-AT-OPTIC", "Fiber Optic Gyroscope Assembly", "Avionics", "pcs", 2400.0, 5200.0, "890123451004", 5, "9014", 18.0, 12),
            ("SKU-AT-RELAY", "High-Voltage Solid State Relay", "Electrical", "pcs", 65.0, 145.0, "890123451005", 40, "8536", 18.0, 180),
            ("SKU-AT-HYDR", "Hydraulic Actuator Piston 24V", "Mechanical", "pcs", 380.0, 820.0, "890123451006", 10, "8412", 18.0, 28),
            ("SKU-AT-SENSOR", "MEMS Inertial Sensor Dual-Axis", "Avionics", "pcs", 110.0, 260.0, "890123451007", 30, "9031", 18.0, 95),
            ("SKU-AT-SEAL", "Fluorosilicone O-Ring Seal Set", "Hardware", "set", 15.0, 45.0, "890123451008", 100, "4016", 18.0, 500),
            ("SKU-AT-WIRE", "PTFE Insulated Aerospace Wire 100m", "Electrical", "roll", 85.0, 195.0, "890123451009", 25, "8544", 18.0, 60),
            ("SKU-AT-CONN", "Circular Military Connector 16-Pin", "Connectors", "pcs", 42.0, 98.0, "890123451010", 50, "8536", 18.0, 220),
            ("SKU-AT-HEAT", "Beryllium Thermal Interface Pad", "Thermal", "pcs", 28.0, 70.0, "890123451011", 60, "6806", 18.0, 310),
            ("SKU-AT-BATT", "Lithium-Sulfur Satellite Battery Pack", "Power", "pcs", 1200.0, 2650.0, "890123451012", 8, "8507", 18.0, 15),
            ("SKU-AT-VALVE", "Precision Cryogenic Solenoid Valve", "Mechanical", "pcs", 520.0, 1150.0, "890123451013", 12, "8481", 18.0, 32),
            ("SKU-AT-FILTER", "High-Purity Fuel Filter Cartridge", "Filtration", "pcs", 75.0, 165.0, "890123451014", 35, "8421", 18.0, 110),
            ("SKU-AT-BOLT", "Inconel 718 Hex Bolt M8x40", "Fasteners", "pcs", 18.0, 42.0, "890123451015", 80, "7318", 18.0, 420),
            ("SKU-AT-RADAR", "Ka-Band Transceiver Radar Module", "Avionics", "pcs", 3100.0, 6800.0, "890123451016", 4, "8526", 18.0, 8),
        ]
        a_movements = []
        for sku, name, cat, uom, cost, sell, bar, reorder, hsn, gst, qty in skus_a:
            p_id = uuid4()
            session.add(Product(
                id=p_id,
                tenant_id=org_a_id,
                sku=sku,
                name=name,
                category=cat,
                unit_of_measure=uom,
                cost_price=cost,
                sell_price=sell,
                barcode=bar,
                reorder_point=reorder,
                hsn_code=hsn,
                gst_rate=gst,
                is_active=True,
            ))
            a_movements.append((p_id, loc_a_id, qty, cost))

        await session.flush()

        for pid, lid, qty, cost in a_movements:
            session.add(StockMovement(
                tenant_id=org_a_id,
                product_id=pid,
                location_id=lid,
                movement_type=MovementTypeEnum.IN,
                quantity=qty,
                unit_cost=cost,
                reference_type="INITIAL",
                reference_id="OPENING-BALANCE",
                performed_by="System Initializer",
                timestamp=now,
            ))

        session.add(TenantSettings(
            tenant_id=org_a_id,
            legal_business_name="AeroTech Dynamics Pvt Ltd",
            gstin="29AABCA1234F1Z8",
            pan="AABCA1234F",
            registered_address="Plot 18, EPIP Zone, Whitefield, Bengaluru, Karnataka 560066",
            state="Karnataka",
            state_code="29",
            authorized_signatory_name="Vikram Sarabhai",
            invoice_prefix="AERO",
        ))
        session.add(TenantInvoiceSequence(tenant_id=org_a_id, fiscal_year="2026-27", current_number=0))
        session.add(TenantBillingProfile(tenant_id=org_a_id, setup_fee=35000.0, setup_fee_status="paid", monthly_maintenance_fee=6500.0))
        session.add(OrgSetupFee(org_id=org_a_id, amount=35000.0, status="Paid", date_paid=now, payment_mode="bank_transfer", recorded_by="Super Admin", invoice_number="INV-TEN/2026-27/00030"))
        session.add(OrgMaintenancePlan(org_id=org_a_id, current_rate=6500.0, effective_from=now, changed_by="Super Admin", reason="Initial agreement"))
        session.add(OrgMaintenanceCycle(org_id=org_a_id, cycle_month=current_month, amount=6500.0, status="Pending", recorded_by="System Auto-Billing"))

        # ==========================================================
        # ORG B: BlueDart Logistics Hub (Stock Transfers & Ledger)
        # ==========================================================
        org_b_id = uuid4()
        org_b = Tenant(
            id=org_b_id,
            name="BlueDart Logistics Hub",
            slug="bluedart-logistics",
            company_code="BLUEDART",
            unique_code="BLUEDART",
            industry="Logistics & Supply Chain",
            location="Goregaon East, Mumbai, Maharashtra",
            tier="Enterprise Global",
            currency_code="INR",
            is_active=True,
            enabled_modules=["products", "locations", "orders", "transfers", "adjustments", "ledger", "reports", "storage"],
        )
        session.add(org_b)
        await session.flush()

        session.add(User(
            tenant_id=org_b_id,
            email="admin@bluedart.test",
            full_name="Rajesh Kulkarni",
            role=UserRole.ADMIN.value,
            hashed_password=DEFAULT_PASSWORD,
            permissions=["inventory:read", "inventory:write", "orders:manage", "team:manage", "reports:view", "settings:manage"],
            is_active=True,
        ))
        session.add(User(
            tenant_id=org_b_id,
            email="dispatch@bluedart.test",
            full_name="Sunil Deshmukh",
            role=UserRole.STAFF.value,
            hashed_password=DEFAULT_PASSWORD,
            permissions=["inventory:read", "inventory:write", "orders:manage"],
            is_active=True,
        ))

        loc_b1_id = uuid4()
        loc_b2_id = uuid4()
        session.add(Location(id=loc_b1_id, tenant_id=org_b_id, name="North Mumbai Hub", code="BD-NMH", address="Goregaon East Hub, Mumbai", capacity=40000, is_active=True))
        session.add(Location(id=loc_b2_id, tenant_id=org_b_id, name="South Pune Depot", code="BD-SPD", address="Chakan Industrial Zone, Pune", capacity=25000, is_active=True))
        await session.flush()

        skus_b = [
            ("SKU-BD-PALLET", "Industrial Heavy Duty Plastic Pallet", "Packaging", "pcs", 450.0, 850.0, "890123452001", 30, "3923", 18.0, 200),
            ("SKU-BD-STRETCH", "Cast Stretch Wrap Film 500mm 23mic", "Packaging", "roll", 85.0, 160.0, "890123452002", 50, "3920", 18.0, 450),
            ("SKU-BD-STRAP", "Polypropylene Strapping Roll 12mm", "Packaging", "roll", 65.0, 130.0, "890123452003", 40, "3920", 18.0, 300),
            ("SKU-BD-BOX-L", "Heavy Duty Corrugated Box Large", "Boxes", "pcs", 18.0, 42.0, "890123452004", 100, "4819", 18.0, 1200),
            ("SKU-BD-BOX-M", "Corrugated Shipping Carton Medium", "Boxes", "pcs", 12.0, 28.0, "890123452005", 150, "4819", 18.0, 1800),
            ("SKU-BD-CRATE", "Collapsible Vented Plastic Crate", "Packaging", "pcs", 120.0, 260.0, "890123452006", 25, "3923", 18.0, 150),
            ("SKU-BD-SEAL-BAR", "Security Tamper-Proof Bolt Seal", "Security", "pcs", 4.5, 12.0, "890123452007", 500, "8301", 18.0, 2500),
            ("SKU-BD-GPS-TAG", "Cargo Real-Time GPS Tracking Beacon", "Electronics", "pcs", 650.0, 1250.0, "890123452008", 20, "8526", 18.0, 80),
            ("SKU-BD-TEMP-REC", "Cold Chain USB Temperature Logger", "Electronics", "pcs", 180.0, 390.0, "890123452009", 30, "9025", 18.0, 120),
            ("SKU-BD-DRY-ICE", "Insulated Thermal Dry Ice Container", "Cold Chain", "pcs", 320.0, 680.0, "890123452010", 15, "3923", 18.0, 45),
            ("SKU-BD-BUBBLE", "Air Bubble Cushioning Roll 100m", "Packaging", "roll", 45.0, 95.0, "890123452011", 40, "3920", 18.0, 220),
            ("SKU-BD-TAPE-HV", "Reinforced Filament Tape 50mm", "Packaging", "roll", 22.0, 52.0, "890123452012", 80, "3919", 18.0, 380),
        ]
        b_movements = []
        first_b_prod = None
        for sku, name, cat, uom, cost, sell, bar, reorder, hsn, gst, qty in skus_b:
            p_id = uuid4()
            if not first_b_prod:
                first_b_prod = (p_id, cost)
            session.add(Product(
                id=p_id,
                tenant_id=org_b_id,
                sku=sku,
                name=name,
                category=cat,
                unit_of_measure=uom,
                cost_price=cost,
                sell_price=sell,
                barcode=bar,
                reorder_point=reorder,
                hsn_code=hsn,
                gst_rate=gst,
                is_active=True,
            ))
            b_movements.append((p_id, loc_b1_id, qty, cost))

        await session.flush()

        for pid, lid, qty, cost in b_movements:
            session.add(StockMovement(
                tenant_id=org_b_id,
                product_id=pid,
                location_id=lid,
                movement_type=MovementTypeEnum.IN,
                quantity=qty,
                unit_cost=cost,
                reference_type="INITIAL",
                reference_id="OPENING-BALANCE",
                performed_by="System Initializer",
                timestamp=now,
            ))

        await session.flush()

        # Stock Transfer
        transfer_id = uuid4()
        session.add(StockTransfer(
            id=transfer_id,
            tenant_id=org_b_id,
            transfer_number="TRF-2026-001",
            source_location_id=loc_b1_id,
            target_location_id=loc_b2_id,
            status="completed",
            notes="Scheduled replenishment: Mumbai Hub -> Pune Depot",
            transfer_date=now,
        ))
        t_prod_id, t_cost = first_b_prod
        session.add(StockTransferItem(
            id=uuid4(),
            transfer_id=transfer_id,
            product_id=t_prod_id,
            quantity=20,
        ))
        session.add(StockMovement(
            tenant_id=org_b_id,
            product_id=t_prod_id,
            location_id=loc_b1_id,
            target_location_id=loc_b2_id,
            movement_type=MovementTypeEnum.TRANSFER,
            quantity=20,
            unit_cost=t_cost,
            reference_type="TRANSFER",
            reference_id=str(transfer_id),
            performed_by="Sunil Deshmukh",
            timestamp=now,
        ))

        session.add(TenantSettings(
            tenant_id=org_b_id,
            legal_business_name="BlueDart Logistics Hub Pvt Ltd",
            gstin="27AABCB1234F1Z7",
            pan="AABCB1234F",
            registered_address="Goregaon East Hub, Western Express Hwy, Mumbai, Maharashtra 400063",
            state="Maharashtra",
            state_code="27",
            authorized_signatory_name="Rajesh Kulkarni",
            invoice_prefix="BLU",
        ))
        session.add(TenantInvoiceSequence(tenant_id=org_b_id, fiscal_year="2026-27", current_number=0))
        session.add(TenantBillingProfile(tenant_id=org_b_id, setup_fee=35000.0, setup_fee_status="paid", monthly_maintenance_fee=6500.0))
        session.add(OrgSetupFee(org_id=org_b_id, amount=35000.0, status="Paid", date_paid=now, payment_mode="bank_transfer", recorded_by="Super Admin", invoice_number="INV-TEN/2026-27/00031"))
        session.add(OrgMaintenancePlan(org_id=org_b_id, current_rate=6500.0, effective_from=now, changed_by="Super Admin", reason="Initial agreement"))
        session.add(OrgMaintenanceCycle(org_id=org_b_id, cycle_month=current_month, amount=6500.0, status="Pending", recorded_by="System Auto-Billing"))

        # ==========================================================
        # ORG C: Crestline Global Trade (POs, SOs, GST Invoicing)
        # ==========================================================
        org_c_id = uuid4()
        org_c = Tenant(
            id=org_c_id,
            name="Crestline Global Trade",
            slug="crestline-trade",
            company_code="CRESTLINE",
            unique_code="CRESTLINE",
            industry="Wholesale & Distribution",
            location="Sector 62, Noida, Uttar Pradesh",
            tier="Growth Suite",
            currency_code="INR",
            is_active=True,
            enabled_modules=["products", "locations", "orders", "transfers", "adjustments", "ledger", "reports", "storage"],
        )
        session.add(org_c)
        await session.flush()

        session.add(User(
            tenant_id=org_c_id,
            email="admin@crestline.test",
            full_name="Amitabh Sen",
            role=UserRole.ADMIN.value,
            hashed_password=DEFAULT_PASSWORD,
            permissions=["inventory:read", "inventory:write", "orders:manage", "team:manage", "reports:view", "settings:manage"],
            is_active=True,
        ))
        session.add(User(
            tenant_id=org_c_id,
            email="sales@crestline.test",
            full_name="Neha Gupta",
            role=UserRole.STAFF.value,
            hashed_password=DEFAULT_PASSWORD,
            permissions=["inventory:read", "inventory:write", "orders:manage"],
            is_active=True,
        ))

        loc_c_id = uuid4()
        session.add(Location(id=loc_c_id, tenant_id=org_c_id, name="Noida Distribution Terminal", code="CGT-NDT", address="Sector 62, Noida, UP", capacity=30000, is_active=True))
        await session.flush()

        skus_c = [
            ("SKU-CG-CABLE-USBC", "Braided USB-C to USB-C Cable 100W", "Cables", "pcs", 45.0, 110.0, "890123453001", 60, "8544", 18.0, 500),
            ("SKU-CG-HDMI-4K", "Ultra High Speed HDMI 2.1 Cable 2m", "Cables", "pcs", 65.0, 150.0, "890123453002", 40, "8544", 18.0, 350),
            ("SKU-CG-CHG-65W", "GaN Dual-Port Wall Charger 65W", "Chargers", "pcs", 180.0, 390.0, "890123453003", 30, "8504", 18.0, 200),
            ("SKU-CG-PWRBNK-20K", "Power Bank 20000mAh 22.5W Fast Charge", "Chargers", "pcs", 380.0, 780.0, "890123453004", 25, "8507", 18.0, 150),
            ("SKU-CG-EARBUD-PRO", "True Wireless ANC Earbuds V5.3", "Audio", "pcs", 450.0, 950.0, "890123453005", 20, "8518", 18.0, 120),
            ("SKU-CG-SPK-BT", "Portable Waterproof Bluetooth Speaker", "Audio", "pcs", 320.0, 690.0, "890123453006", 15, "8518", 18.0, 90),
            ("SKU-CG-SMART-PLUG", "Wi-Fi Smart Plug with Energy Monitoring", "Smart Home", "pcs", 140.0, 290.0, "890123453007", 35, "8536", 18.0, 180),
            ("SKU-CG-LED-STRIP", "RGBIC Smart LED Light Strip 5m", "Smart Home", "pcs", 120.0, 260.0, "890123453008", 25, "9405", 18.0, 140),
            ("SKU-CG-USB-HUB-7", "7-in-1 Aluminum USB-C Hub HDMI PD", "Peripherals", "pcs", 280.0, 580.0, "890123453009", 20, "8471", 18.0, 110),
            ("SKU-CG-WIFI-ROUTER", "Dual-Band Gigabit Wi-Fi 6 Router", "Networking", "pcs", 850.0, 1750.0, "890123453010", 10, "8517", 18.0, 45),
            ("SKU-CG-WEBCAM-HD", "Full HD 1080P Autofocus Webcam", "Peripherals", "pcs", 210.0, 450.0, "890123453011", 18, "8525", 18.0, 85),
            ("SKU-CG-PAD-DESK", "Extended Anti-Slip Leather Desk Pad", "Accessories", "pcs", 55.0, 130.0, "890123453012", 50, "3926", 18.0, 300),
            ("SKU-CG-MOUNT-PHONE", "MagSafe Magnetic Car Vent Phone Mount", "Accessories", "pcs", 42.0, 98.0, "890123453013", 40, "3926", 18.0, 240),
            ("SKU-CG-CLEAN-KIT", "7-in-1 Electronic Screen Cleaning Kit", "Accessories", "pcs", 18.0, 45.0, "890123453014", 80, "3402", 18.0, 400),
        ]
        c_movements = []
        first_c_prod = None
        for sku, name, cat, uom, cost, sell, bar, reorder, hsn, gst, qty in skus_c:
            p_id = uuid4()
            if not first_c_prod:
                first_c_prod = (p_id, cost, sell)
            session.add(Product(
                id=p_id,
                tenant_id=org_c_id,
                sku=sku,
                name=name,
                category=cat,
                unit_of_measure=uom,
                cost_price=cost,
                sell_price=sell,
                barcode=bar,
                reorder_point=reorder,
                hsn_code=hsn,
                gst_rate=gst,
                is_active=True,
            ))
            c_movements.append((p_id, loc_c_id, qty, cost))

        await session.flush()

        for pid, lid, qty, cost in c_movements:
            session.add(StockMovement(
                tenant_id=org_c_id,
                product_id=pid,
                location_id=lid,
                movement_type=MovementTypeEnum.IN,
                quantity=qty,
                unit_cost=cost,
                reference_type="INITIAL",
                reference_id="OPENING-BALANCE",
                performed_by="System Initializer",
                timestamp=now,
            ))

        await session.flush()

        # Seed 1 Purchase Order (Received)
        po_id = uuid4()
        session.add(PurchaseOrder(
            id=po_id,
            tenant_id=org_c_id,
            po_number="PO-2026-001",
            supplier_name="Shenzhen MicroTech Ltd",
            status=OrderStatus.COMPLETED,
            target_location_id=loc_c_id,
            total_amount=45000.0,
            order_date=now,
            received_date=now,
        ))
        session.add(PurchaseOrderItem(
            id=uuid4(),
            order_id=po_id,
            product_id=first_c_prod[0],
            ordered_qty=1000,
            received_qty=1000,
            unit_cost=45.0,
        ))

        # Seed 1 Sales Order (Completed) + GST Invoice
        so_id = uuid4()
        so_num = "SO-2026-101"
        inv_id = uuid4()
        inv_num = "INV-CREST/2026-27/00001"
        taxable_amt = 27500.0
        cgst_amt = taxable_amt * 0.09
        sgst_amt = taxable_amt * 0.09
        total_inv_amt = taxable_amt + cgst_amt + sgst_amt

        session.add(SalesOrder(
            id=so_id,
            tenant_id=org_c_id,
            so_number=so_num,
            customer_name="Apex Electronics Retail Pvt Ltd",
            customer_gstin="09AABCA9999F1Z1",
            status=OrderStatus.COMPLETED,
            source_location_id=loc_c_id,
            total_amount=total_inv_amt,
            billing_address="Plot 104, Sector 18, Noida, UP 201301",
            shipping_address="Plot 104, Sector 18, Noida, UP 201301",
            billing_state="Uttar Pradesh",
            billing_state_code="09",
            shipping_state="Uttar Pradesh",
            shipping_state_code="09",
            state="Uttar Pradesh",
            state_code="09",
            invoice_id=inv_id,
            order_date=now,
            fulfilled_date=now,
        ))
        session.add(SalesOrderItem(
            id=uuid4(),
            order_id=so_id,
            product_id=first_c_prod[0],
            ordered_qty=250,
            fulfilled_qty=250,
            unit_price=110.0,
        ))
        await session.flush()

        session.add(Invoice(
            id=inv_id,
            tenant_id=org_c_id,
            invoice_number=inv_num,
            sales_order_id=so_id,
            invoice_date=now,
            due_date=now,
            place_of_supply="09-Uttar Pradesh",
            status=InvoiceStatus.PAID,
            seller_legal_name="Crestline Global Trade Pvt Ltd",
            seller_gstin="09AABCC1234F1Z6",
            seller_pan="AABCC1234F",
            seller_address="Sector 62, Commercial Corridor, Noida, Uttar Pradesh 201309",
            seller_state="Uttar Pradesh",
            seller_state_code="09",
            customer_name="Apex Electronics Retail Pvt Ltd",
            customer_gstin="09AABCA9999F1Z1",
            customer_billing_address="Plot 104, Sector 18, Noida, UP 201301",
            customer_shipping_address="Plot 104, Sector 18, Noida, UP 201301",
            customer_state="Uttar Pradesh",
            customer_state_code="09",
            is_inter_state=False,
            payment_terms="Immediate",
            total_taxable_value=taxable_amt,
            total_cgst=cgst_amt,
            total_sgst=sgst_amt,
            total_igst=0.0,
            round_off=0.0,
            grand_total=total_inv_amt,
            grand_total_words="Thirty Two Thousand Four Hundred Fifty Rupees Only",
        ))
        await session.flush()
        session.add(InvoiceItem(
            id=uuid4(),
            invoice_id=inv_id,
            product_id=first_c_prod[0],
            item_description="Braided USB-C to USB-C Cable 100W",
            quantity=250,
            unit_of_measure="pcs",
            unit_price=110.0,
            discount=0.0,
            taxable_value=taxable_amt,
            hsn_code="8544",
            gst_rate=18.0,
            cgst_rate=9.0,
            cgst_amount=cgst_amt,
            sgst_rate=9.0,
            sgst_amount=sgst_amt,
            igst_rate=0.0,
            igst_amount=0.0,
            total=total_inv_amt,
        ))

        session.add(TenantSettings(
            tenant_id=org_c_id,
            legal_business_name="Crestline Global Trade Pvt Ltd",
            gstin="09AABCC1234F1Z6",
            pan="AABCC1234F",
            registered_address="Sector 62, Commercial Corridor, Noida, Uttar Pradesh 201309",
            state="Uttar Pradesh",
            state_code="09",
            authorized_signatory_name="Amitabh Sen",
            invoice_prefix="CREST",
        ))
        session.add(TenantInvoiceSequence(tenant_id=org_c_id, fiscal_year="2026-27", current_number=1))
        session.add(TenantBillingProfile(tenant_id=org_c_id, setup_fee=25000.0, setup_fee_status="paid", monthly_maintenance_fee=4500.0))
        session.add(OrgSetupFee(org_id=org_c_id, amount=25000.0, status="Paid", date_paid=now, payment_mode="bank_transfer", recorded_by="Super Admin", invoice_number="INV-TEN/2026-27/00032"))
        session.add(OrgMaintenancePlan(org_id=org_c_id, current_rate=4500.0, effective_from=now, changed_by="Super Admin", reason="Initial agreement"))
        session.add(OrgMaintenanceCycle(org_id=org_c_id, cycle_month=current_month, amount=4500.0, status="Pending", recorded_by="System Auto-Billing"))

        # ==========================================================
        # ORG D: Delta Health Diagnostics (Role Management & RBAC)
        # ==========================================================
        org_d_id = uuid4()
        org_d = Tenant(
            id=org_d_id,
            name="Delta Health Diagnostics",
            slug="delta-health",
            company_code="DELTAHLTH",
            unique_code="DELTAHLTH",
            industry="Pharmaceuticals & Healthcare",
            location="Genome Valley, Hyderabad, Telangana",
            tier="Growth Suite",
            currency_code="INR",
            is_active=True,
            enabled_modules=["products", "locations", "orders", "transfers", "adjustments", "ledger", "reports", "storage"],
        )
        session.add(org_d)
        await session.flush()

        session.add(User(
            tenant_id=org_d_id,
            email="admin@deltahealth.test",
            full_name="Dr. Srinivas Rao",
            role=UserRole.ADMIN.value,
            hashed_password=DEFAULT_PASSWORD,
            permissions=["inventory:read", "inventory:write", "orders:manage", "team:manage", "reports:view", "settings:manage"],
            is_active=True,
        ))
        session.add(User(
            tenant_id=org_d_id,
            email="auditor@deltahealth.test",
            full_name="Pooja Reddy",
            role=UserRole.VIEWER.value,
            hashed_password=DEFAULT_PASSWORD,
            permissions=["inventory:read", "reports:view"],
            is_active=True,
        ))

        loc_d_id = uuid4()
        session.add(Location(id=loc_d_id, tenant_id=org_d_id, name="Genome Valley Cold Storage", code="DHD-GVC", address="Genome Valley Phase II, Hyderabad", capacity=15000, is_active=True))
        await session.flush()

        skus_d = [
            ("SKU-DH-REAGENT-A", "High-Sensitivity Diagnostic Reagent A", "Reagents", "kit", 850.0, 1800.0, "890123454001", 15, "3822", 12.0, 60),
            ("SKU-DH-ASSAY-KIT", "Immuno-Assay Quantitative Test Kit", "Kits", "kit", 1200.0, 2500.0, "890123454002", 10, "3822", 12.0, 45),
            ("SKU-DH-TEST-STRIP", "Rapid Pathogen Screening Test Strips", "Diagnostics", "pack", 120.0, 280.0, "890123454003", 50, "3822", 12.0, 300),
            ("SKU-DH-PIPETTE-SET", "Precision Micro-Pipette Calibration Set", "Lab Equipment", "set", 650.0, 1400.0, "890123454004", 8, "9027", 18.0, 25),
            ("SKU-DH-VIAL-STERILE", "Cryogenic Sterile Storage Vials 2ml", "Labware", "pack", 45.0, 110.0, "890123454005", 80, "3923", 18.0, 400),
            ("SKU-DH-CENTRI-TUBE", "Polypropylene Centrifuge Tubes 50ml", "Labware", "pack", 35.0, 85.0, "890123454006", 100, "3923", 18.0, 500),
            ("SKU-DH-GLOVE-NITRILE", "Medical Grade Nitrile Gloves Powder-Free", "Consumables", "box", 85.0, 195.0, "890123454007", 120, "4015", 12.0, 600),
            ("SKU-DH-SWAB-DNA", "DNA Free Sterile Collection Swabs", "Consumables", "pack", 25.0, 65.0, "890123454008", 150, "5601", 12.0, 800),
            ("SKU-DH-CULTURE-PLATE", "Treated Cell Culture Plates 96-Well", "Labware", "pack", 95.0, 220.0, "890123454009", 40, "3926", 18.0, 180),
            ("SKU-DH-BUFFER-SOL", "Phosphate Buffered Saline 1X 1L", "Solutions", "bottle", 55.0, 130.0, "890123454010", 60, "3822", 12.0, 240),
        ]
        d_movements = []
        for sku, name, cat, uom, cost, sell, bar, reorder, hsn, gst, qty in skus_d:
            p_id = uuid4()
            session.add(Product(
                id=p_id,
                tenant_id=org_d_id,
                sku=sku,
                name=name,
                category=cat,
                unit_of_measure=uom,
                cost_price=cost,
                sell_price=sell,
                barcode=bar,
                reorder_point=reorder,
                hsn_code=hsn,
                gst_rate=gst,
                is_active=True,
            ))
            d_movements.append((p_id, loc_d_id, qty, cost))

        await session.flush()

        for pid, lid, qty, cost in d_movements:
            session.add(StockMovement(
                tenant_id=org_d_id,
                product_id=pid,
                location_id=lid,
                movement_type=MovementTypeEnum.IN,
                quantity=qty,
                unit_cost=cost,
                reference_type="INITIAL",
                reference_id="OPENING-BALANCE",
                performed_by="System Initializer",
                timestamp=now,
            ))

        session.add(TenantSettings(
            tenant_id=org_d_id,
            legal_business_name="Delta Health Diagnostics Pvt Ltd",
            gstin="36AABCD1234F1Z5",
            pan="AABCD1234F",
            registered_address="Genome Valley Phase II, Shamirpet, Hyderabad, Telangana 500078",
            state="Telangana",
            state_code="36",
            authorized_signatory_name="Dr. Srinivas Rao",
            invoice_prefix="DELTA",
        ))
        session.add(TenantInvoiceSequence(tenant_id=org_d_id, fiscal_year="2026-27", current_number=0))
        session.add(TenantBillingProfile(tenant_id=org_d_id, setup_fee=25000.0, setup_fee_status="paid", monthly_maintenance_fee=4500.0))
        session.add(OrgSetupFee(org_id=org_d_id, amount=25000.0, status="Paid", date_paid=now, payment_mode="manual", recorded_by="Super Admin", invoice_number="INV-TEN/2026-27/00033"))
        session.add(OrgMaintenancePlan(org_id=org_d_id, current_rate=4500.0, effective_from=now, changed_by="Super Admin", reason="Initial agreement"))
        session.add(OrgMaintenanceCycle(org_id=org_d_id, cycle_month=current_month, amount=4500.0, status="Pending", recorded_by="System Auto-Billing"))

        # ==========================================================
        # ORG E: E-Commerce Express (Billing Engine & Safeguards)
        # ==========================================================
        org_e_id = uuid4()
        org_e = Tenant(
            id=org_e_id,
            name="E-Commerce Express",
            slug="ecomm-express",
            company_code="ECOMMEXP",
            unique_code="ECOMMEXP",
            industry="Retail & E-commerce",
            location="OMR IT Corridor, Chennai, Tamil Nadu",
            tier="Enterprise Global",
            currency_code="INR",
            is_active=True,
            enabled_modules=["products", "locations", "orders", "transfers", "adjustments", "ledger", "reports", "storage"],
        )
        session.add(org_e)
        await session.flush()

        session.add(User(
            tenant_id=org_e_id,
            email="admin@ecommexpress.test",
            full_name="Karthik Subramanian",
            role=UserRole.ADMIN.value,
            hashed_password=DEFAULT_PASSWORD,
            permissions=["inventory:read", "inventory:write", "orders:manage", "team:manage", "reports:view", "settings:manage"],
            is_active=True,
        ))
        session.add(User(
            tenant_id=org_e_id,
            email="finance@ecommexpress.test",
            full_name="Divya Krishnan",
            role=UserRole.MANAGER.value,
            hashed_password=DEFAULT_PASSWORD,
            permissions=["inventory:read", "orders:manage", "reports:view"],
            is_active=True,
        ))

        loc_e_id = uuid4()
        session.add(Location(id=loc_e_id, tenant_id=org_e_id, name="Chennai Fulfillment Center", code="ECE-CFC", address="Navalur OMR, Chennai", capacity=45000, is_active=True))
        await session.flush()

        skus_e = [
            ("SKU-EC-TSHIRT-BLK", "Premium Combed Cotton T-Shirt Black", "Apparel", "pcs", 180.0, 499.0, "890123455001", 100, "6109", 5.0, 650),
            ("SKU-EC-HOODIE-GRY", "Heavyweight Fleece Hoodie Heather Grey", "Apparel", "pcs", 450.0, 1299.0, "890123455002", 50, "6110", 12.0, 280),
            ("SKU-EC-JEANS-BLU", "Slim Fit Stretch Denim Jeans Indigo", "Apparel", "pcs", 550.0, 1599.0, "890123455003", 40, "6203", 12.0, 220),
            ("SKU-EC-SNEAKER-WHT", "Classic Canvas Casual Sneakers White", "Footwear", "pair", 420.0, 1199.0, "890123455004", 30, "6404", 12.0, 150),
            ("SKU-EC-BACKPACK-40L", "Waterproof Commuter Backpack 40L", "Bags", "pcs", 650.0, 1799.0, "890123455005", 25, "4202", 18.0, 120),
            ("SKU-EC-CAP-NAVY", "Structured Baseball Cap Navy Blue", "Accessories", "pcs", 85.0, 299.0, "890123455006", 80, "6505", 12.0, 340),
            ("SKU-EC-SOCKS-3PK", "Cushioned Athletic Ankle Socks 3-Pack", "Accessories", "pack", 65.0, 199.0, "890123455007", 120, "6115", 5.0, 500),
            ("SKU-EC-BELT-LTHR", "Genuine Full-Grain Leather Belt Brown", "Accessories", "pcs", 220.0, 699.0, "890123455008", 35, "4203", 18.0, 180),
            ("SKU-EC-WALLET-RFID", "Slim Bifold RFID Blocking Leather Wallet", "Accessories", "pcs", 180.0, 549.0, "890123455009", 45, "4202", 18.0, 210),
            ("SKU-EC-SUNGLASS-POL", "Polarized UV400 Aviator Sunglasses", "Eyewear", "pcs", 280.0, 899.0, "890123455010", 30, "9004", 18.0, 160),
            ("SKU-EC-DUFFLE-TRVL", "Weekend Travel Duffle Bag Olive Green", "Bags", "pcs", 520.0, 1499.0, "890123455011", 20, "4202", 18.0, 95),
            ("SKU-EC-BEANIE-WINT", "Ribbed Knit Acrylic Winter Beanie", "Accessories", "pcs", 75.0, 249.0, "890123455012", 70, "6505", 12.0, 310),
        ]
        e_movements = []
        for sku, name, cat, uom, cost, sell, bar, reorder, hsn, gst, qty in skus_e:
            p_id = uuid4()
            session.add(Product(
                id=p_id,
                tenant_id=org_e_id,
                sku=sku,
                name=name,
                category=cat,
                unit_of_measure=uom,
                cost_price=cost,
                sell_price=sell,
                barcode=bar,
                reorder_point=reorder,
                hsn_code=hsn,
                gst_rate=gst,
                is_active=True,
            ))
            e_movements.append((p_id, loc_e_id, qty, cost))

        await session.flush()

        for pid, lid, qty, cost in e_movements:
            session.add(StockMovement(
                tenant_id=org_e_id,
                product_id=pid,
                location_id=lid,
                movement_type=MovementTypeEnum.IN,
                quantity=qty,
                unit_cost=cost,
                reference_type="INITIAL",
                reference_id="OPENING-BALANCE",
                performed_by="System Initializer",
                timestamp=now,
            ))

        session.add(TenantSettings(
            tenant_id=org_e_id,
            legal_business_name="E-Commerce Express Pvt Ltd",
            gstin="33AABCE1234F1Z4",
            pan="AABCE1234F",
            registered_address="Navalur OMR, IT Corridor, Chennai, Tamil Nadu 600130",
            state="Tamil Nadu",
            state_code="33",
            authorized_signatory_name="Karthik Subramanian",
            invoice_prefix="ECE",
        ))
        session.add(TenantInvoiceSequence(tenant_id=org_e_id, fiscal_year="2026-27", current_number=0))
        session.add(TenantBillingProfile(tenant_id=org_e_id, setup_fee=35000.0, setup_fee_status="paid", monthly_maintenance_fee=6500.0))
        session.add(OrgSetupFee(org_id=org_e_id, amount=35000.0, status="Paid", date_paid=now, payment_mode="bank_transfer", recorded_by="Super Admin", invoice_number="INV-TEN/2026-27/00034"))
        session.add(OrgMaintenancePlan(org_id=org_e_id, current_rate=6500.0, effective_from=now, changed_by="Super Admin", reason="Initial agreement"))
        session.add(OrgMaintenanceCycle(org_id=org_e_id, cycle_month=current_month, amount=6500.0, status="Pending", recorded_by="System Auto-Billing"))

        # Seed 1 Security Approval Request for Org E
        session.add(SecurityApprovalRequest(
            id=uuid4(),
            tenant_id=org_e_id,
            tenant_name="E-Commerce Express",
            requester_name="Karthik Subramanian",
            requester_email="admin@ecommexpress.test",
            action_type="ledger_purge",
            reason="Q3 Financial Audit Ledger Reconciliation",
            details={"scope": "full_fiscal_year", "priority": "high"},
            status="pending",
            created_at=now,
        ))

        # Seed AuditLog entries
        for oid, oname in [
            (org_a_id, "AeroTech Dynamics"),
            (org_b_id, "BlueDart Logistics Hub"),
            (org_c_id, "Crestline Global Trade"),
            (org_d_id, "Delta Health Diagnostics"),
            (org_e_id, "E-Commerce Express"),
        ]:
            session.add(AuditLog(
                actor_name="Invenza Super Administrator",
                actor_email="superadmin@invenza.internal",
                action_type="company_provisioned",
                target_type="tenant",
                target_id=str(oid),
                tenant_id=oid,
                tenant_name=oname,
                description=f"Provisioned fresh test enterprise organization {oname}.",
                created_at=now,
            ))

        await session.commit()
        print("Provisioning committed successfully.")

async def verify_checkpoint_2():
    print("\n--- Phase 2 Verification Checkpoint ---")
    async with AsyncSessionLocal() as session:
        client_tenants = (await session.execute(text("""
            SELECT id, name, slug, company_code, industry, location, is_active 
            FROM tenants 
            WHERE id != '00000000-0000-0000-0000-000000000000'
            ORDER BY name
        """))).fetchall()

        print(f"\nTotal Client Organizations in DB: {len(client_tenants)}")
        for idx, t in enumerate(client_tenants, 1):
            users = (await session.execute(text(f"SELECT email, role FROM users WHERE tenant_id = '{t[0]}'"))).fetchall()
            p_cnt = (await session.execute(text(f"SELECT COUNT(*) FROM products WHERE tenant_id = '{t[0]}'"))).scalar()
            l_cnt = (await session.execute(text(f"SELECT COUNT(*) FROM locations WHERE tenant_id = '{t[0]}'"))).scalar()
            user_str = ", ".join([f"{u[0]} ({u[1]})" for u in users])
            print(f"  {idx}. {t[1]} [Code: {t[3]}] - Industry: {t[4]} | Users ({len(users)}): {user_str} | Products: {p_cnt} | Locations: {l_cnt}")

        assert len(client_tenants) == 7, f"Expected exactly 7 client organizations, got {len(client_tenants)}!"
        print("\nSUCCESS: Total client organization count = 7 (Hapkonic + Marketza + 5 new test orgs). No extras, no duplicates.")

async def main():
    await seed_orgs()
    await verify_checkpoint_2()

if __name__ == "__main__":
    asyncio.run(main())
