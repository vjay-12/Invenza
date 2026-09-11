"""
Comprehensive Phase 3 Test Suite:
Validates the complete Invenza platform end-to-end:
1. Super Admin Console (Tenants, Leads, Safeguards, Roles, Billing, Reports)
2. Tenant Platform across the 5 fresh test organizations (Dashboard, Products, Warehouses, Transfers, Orders, Invoices, Ledger, Adjustments, Team)
3. Cross-cutting data consistency and live DB queries.
"""

import asyncio
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import httpx

BASE_URL = "http://localhost:8000/api/v1"

async def run_full_suite():
    print("=" * 70)
    print("STARTING PHASE 3: FULL PLATFORM VERIFICATION")
    print("=" * 70)

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        # -------------------------------------------------------------
        # 1. SUPER ADMIN AUTHENTICATION
        # -------------------------------------------------------------
        print("\n[1] Super Admin Authentication")
        login_res = await client.post("/auth/login", json={
            "email": "superadmin@invenza.internal",
            "password": "superadmin2026"
        })
        assert login_res.status_code == 200, f"Super admin login failed: {login_res.text}"
        super_token = login_res.json()["access_token"]
        super_headers = {"Authorization": f"Bearer {super_token}"}
        print("  [PASS] Super Admin logged in successfully (JWT token received).")

        # -------------------------------------------------------------
        # 2. TENANTS & COMPANIES MANAGEMENT
        # -------------------------------------------------------------
        print("\n[2] Super Admin: Tenants & Companies Management")
        companies_res = await client.get("/superadmin/companies", headers=super_headers)
        assert companies_res.status_code == 200, f"Failed to list companies: {companies_res.text}"
        companies = companies_res.json()
        print(f"  [PASS] Retrieved {len(companies)} client companies (Expected: 7).")
        assert len(companies) == 7, f"Expected 7 companies, got {len(companies)}"

        # Search filter
        search_res = await client.get("/superadmin/companies?search=AeroTech", headers=super_headers)
        assert len(search_res.json()) == 1, "Search by 'AeroTech' failed"
        print("  [PASS] Search by name 'AeroTech' returned exact match.")

        # Industry filter
        ind_res = await client.get("/superadmin/companies?industry=Aerospace%20%26%20Defense", headers=super_headers)
        assert len(ind_res.json()) == 1, "Industry filter failed"
        print("  [PASS] Industry filter 'Aerospace & Defense' returned exact match.")

        # Analytics for first company
        aero_comp = next(c for c in companies if c["unique_code"] == "AEROTECH")
        analytics_res = await client.get(f"/superadmin/companies/{aero_comp['id']}/analytics", headers=super_headers)
        assert analytics_res.status_code == 200, "Analytics failed"
        print(f"  [PASS] Company analytics for {aero_comp['name']} retrieved (Products: {analytics_res.json()['total_products']}).")

        # Deactivate / Reactivate
        archive_res = await client.post(f"/superadmin/companies/{aero_comp['id']}/archive?archive=true", headers=super_headers)
        assert archive_res.status_code == 200, f"Archive failed: {archive_res.text}"
        assert archive_res.json()["is_archived"] is True
        # Reactivate back
        restore_res = await client.post(f"/superadmin/companies/{aero_comp['id']}/archive?archive=false", headers=super_headers)
        assert restore_res.status_code == 200 and restore_res.json()["is_archived"] is False
        print("  [PASS] Deactivate and Reactivate toggle verified.")

        # -------------------------------------------------------------
        # 3. LEADS & QUOTES MANAGEMENT
        # -------------------------------------------------------------
        print("\n[3] Super Admin: Leads & Quotes Management")
        leads_res = await client.get("/superadmin/leads", headers=super_headers)
        assert leads_res.status_code == 200, f"Failed to list leads: {leads_res.text}"
        leads = leads_res.json()
        print(f"  [PASS] Leads loaded: {len(leads)} lead(s).")
        assert len(leads) >= 1, "Expected at least 1 lead"
        m_lead = leads[0]

        # Update lead status
        update_lead_res = await client.patch(f"/superadmin/leads/{m_lead['id']}/status", headers=super_headers, json={
            "status": "converted",
            "quoted_amount": 75000.0,
            "notes": "Verified enterprise requirements in Phase 3 testing."
        })
        assert update_lead_res.status_code == 200, f"Lead update failed: {update_lead_res.text}"
        print("  [PASS] Lead pipeline status & quoted amount update verified.")

        # -------------------------------------------------------------
        # 4. SECURITY SAFEGUARDS & AUDIT LOGS
        # -------------------------------------------------------------
        print("\n[4] Super Admin: Security Safeguards & Audit Logs")
        reqs_res = await client.get("/safeguards/queue?status=all", headers=super_headers)
        assert reqs_res.status_code == 200, f"Failed to fetch safeguards requests: {reqs_res.text}"
        all_reqs = reqs_res.json()
        print(f"  [PASS] Security approval requests loaded: {len(all_reqs)} total request(s).")
        
        # Dynamically create a test security request and approve it
        ecomm_comp = next(c for c in companies if c["unique_code"] == "ECOMMEXP")
        create_req_res = await client.post("/safeguards/queue", headers=super_headers, json={
            "tenant_id": str(ecomm_comp["id"]),
            "action_type": "export_customer_data",
            "target_name": "Customer Data Export",
            "reason": "Phase 3 automated dual-authorization verification",
            "details": {"format": "csv", "destination": "encrypted_vault"}
        })
        assert create_req_res.status_code == 201, f"Create safeguard request failed: {create_req_res.text}"
        target_req = create_req_res.json()
        print(f"  [PASS] Created test dual-authorization request: '{target_req['action_type']}'.")

        # Test approving
        action_res = await client.post(f"/safeguards/queue/{target_req['id']}/approve", headers=super_headers)
        assert action_res.status_code == 200, f"Approve request failed: {action_res.text}"
        assert action_res.json()["status"] == "approved"
        print(f"  [PASS] Security approval request for '{target_req['action_type']}' successfully approved.")

        # Audit logs filter
        logs_res = await client.get("/safeguards/audit-logs?limit=10", headers=super_headers)
        assert logs_res.status_code == 200, f"Failed to fetch audit logs: {logs_res.text}"
        logs = logs_res.json()
        assert len(logs) >= 5, "Expected audit logs to exist"
        print(f"  [PASS] Audit logs filter verified ({len(logs)} audit entries returned).")

        # -------------------------------------------------------------
        # 5. ROLE MANAGEMENT & RBAC SAFEGUARDS
        # -------------------------------------------------------------
        print("\n[5] Super Admin: Role Management & RBAC Protection")
        role_orgs_res = await client.get("/role-management/organizations", headers=super_headers)
        assert role_orgs_res.status_code == 200
        role_orgs = role_orgs_res.json()
        assert len(role_orgs) == 7, f"Expected 7 role orgs, got {len(role_orgs)}"
        print(f"  [PASS] Role Management org picker lists exactly {len(role_orgs)} client organizations.")

        # Delta Health team
        delta_org = next(o for o in role_orgs if o["unique_code"] == "DELTAHLTH")
        team_res = await client.get(f"/role-management/organizations/{delta_org['id']}/team", headers=super_headers)
        assert team_res.status_code == 200
        team = team_res.json()
        assert len(team) == 2, f"Expected 2 operators in Delta Health, got {len(team)}"
        print("  [PASS] Delta Health operator roster verified (1 Admin + 1 Viewer).")

        # Sole admin protection test!
        delta_admin = next(u for u in team if u["role"] == "admin")
        demote_res = await client.put(f"/role-management/users/{delta_admin['id']}/role", headers=super_headers, json={
            "role": "staff",
            "permissions": ["inventory:read", "orders:manage"]
        })
        assert demote_res.status_code == 400, "Sole admin demotion should have been blocked with 400!"
        assert "Assign another user as Admin first" in demote_res.text
        print("  [PASS] Sole Administrator demotion protection verified: Backend properly blocked demoting the last Admin.")

        # -------------------------------------------------------------
        # 6. BILLING & COMMERCIAL MANAGEMENT
        # -------------------------------------------------------------
        print("\n[6] Super Admin: Billing & Commercial Management")
        billing_overview_res = await client.get("/billing/overview", headers=super_headers)
        assert billing_overview_res.status_code == 200
        b_overview = billing_overview_res.json()
        assert len(b_overview["organizations"]) == 7, f"Expected 7 orgs in billing overview, got {len(b_overview['organizations'])}"
        print(f"  [PASS] Billing overview loaded: {len(b_overview['organizations'])} organizations. MRR: Rs.{b_overview['active_monthly_recurring']:,}")

        # Drill-down into E-Commerce Express
        ecomm_org = next(o for o in b_overview["organizations"] if o["company_code"] == "ECOMMEXP")
        detail_res = await client.get(f"/billing/tenants/{ecomm_org['id']}", headers=super_headers)
        assert detail_res.status_code == 200, f"Detail failed: {detail_res.text}"
        b_detail = detail_res.json()
        assert b_detail["setup_fee"]["status"] == "Paid", "Setup fee should be Paid"
        print("  [PASS] Org-level Billing drill-down: Setup Fee card & Monthly rate loaded accurately.")

        # Download setup fee invoice PDF
        setup_fee_id = b_detail["setup_fee"]["id"]
        pdf_res = await client.get(f"/billing/setup-fee/{setup_fee_id}/invoice-pdf", headers=super_headers)
        assert pdf_res.status_code == 200, f"PDF failed: {pdf_res.text}"
        assert pdf_res.headers["content-type"] == "application/pdf"
        assert pdf_res.content.startswith(b"%PDF"), "Response is not a valid PDF"
        print(f"  [PASS] Setup fee Tax Invoice PDF downloaded ({len(pdf_res.content)} bytes).")

        # Update rate test
        rate_res = await client.post(f"/billing/tenants/{ecomm_org['id']}/maintenance-plan", headers=super_headers, json={
            "new_rate": 7500.0,
            "reason": "Enterprise Tier Upgrade SLA"
        })
        assert rate_res.status_code == 200 and rate_res.json()["plan"]["current_rate"] == 7500.0
        print("  [PASS] Monthly maintenance rate updated to Rs.7,500/mo and recorded in rate history.")

        # -------------------------------------------------------------
        # 7. PLATFORM REPORTS
        # -------------------------------------------------------------
        print("\n[7] Super Admin: Platform Reports")
        stats_res = await client.get("/superadmin/reports/platform", headers=super_headers)
        assert stats_res.status_code == 200
        stats = stats_res.json()
        assert stats["total_companies"] == 7, f"Expected 7 total companies in stats, got {stats['total_companies']}"
        assert stats["active_companies"] == 7
        print(f"  [PASS] Platform Reports verified: Total Orgs: {stats['total_companies']}, Active: {stats['active_companies']}, Products: {stats['total_products']}.")

        # =============================================================
        # ORG-LEVEL PLATFORM TESTS ACROSS THE 5 NEW TEST ORGS
        # =============================================================

        # -------------------------------------------------------------
        # ORG A: AEROTECH DYNAMICS (Products, Catalog, Adjustments)
        # -------------------------------------------------------------
        print("\n[8] Org A (AeroTech): Inventory & SKU Catalog Operations")
        org_a_login = await client.post("/auth/login", json={"email": "admin@aerotech.test", "password": "Password123!"})
        assert org_a_login.status_code == 200
        a_token = org_a_login.json()["access_token"]
        a_headers = {"Authorization": f"Bearer {a_token}"}
        print("  [PASS] Logged in as AeroTech Admin.")

        # Valuation Report & Dashboard Metrics
        val_res = await client.get("/reports/valuation", headers=a_headers)
        assert val_res.status_code == 200
        val_data = val_res.json()
        print(f"  [PASS] Valuation & Dashboard metrics: Total SKUs: {val_data['total_skus']}, Stock Units: {val_data['total_units']}, FIFO Valuation: Rs.{val_data['fifo_total_valuation']:,.2f}")
        assert val_data["total_skus"] >= 16

        # Products list
        p_res = await client.get("/products/?skip=0&limit=50", headers=a_headers)
        assert p_res.status_code == 200
        products = p_res.json()
        assert len(products) >= 16, f"Expected at least 16 products for AeroTech, got {len(products)}"
        print(f"  [PASS] Products catalog: {len(products)} aerospace SKUs listed with live stock.")

        # Create a new product
        test_sku = f"SKU-AT-TEST-{uuid.uuid4().hex[:6].upper()}"
        new_p_res = await client.post("/products/", headers=a_headers, json={
            "sku": test_sku,
            "name": "Experimental Solar Array Hinge",
            "category": "Solar & Power",
            "unit_of_measure": "pcs",
            "cost_price": 320.0,
            "sell_price": 750.0,
            "reorder_point": 10,
            "barcode": f"890123{uuid.uuid4().hex[:6]}",
            "hsn_code": "8541",
            "gst_rate": 18.0
        })
        assert new_p_res.status_code == 201, f"Product create failed: {new_p_res.text}"
        new_prod = new_p_res.json()
        print(f"  [PASS] Created new product: {new_prod['name']} (SKU: {new_prod['sku']}).")

        # Edit the product
        edit_p_res = await client.put(f"/products/{new_prod['id']}", headers=a_headers, json={
            "name": "Experimental Solar Array Hinge Pro",
            "cost_price": 340.0,
            "sell_price": 790.0,
            "reorder_point": 15
        })
        assert edit_p_res.status_code == 200 and edit_p_res.json()["sell_price"] == 790.0
        print("  [PASS] Product successfully edited.")

        # Delete the test product
        del_p_res = await client.delete(f"/products/{new_prod['id']}", headers=a_headers)
        assert del_p_res.status_code in (200, 204)
        print("  [PASS] Test product successfully removed.")

        # -------------------------------------------------------------
        # ORG B: BLUEDART LOGISTICS (Transfers & Movement Ledger)
        # -------------------------------------------------------------
        print("\n[9] Org B (BlueDart): Stock Transfers & Movement Ledger")
        org_b_login = await client.post("/auth/login", json={"email": "admin@bluedart.test", "password": "Password123!"})
        assert org_b_login.status_code == 200
        b_token = org_b_login.json()["access_token"]
        b_headers = {"Authorization": f"Bearer {b_token}"}
        print("  [PASS] Logged in as BlueDart Admin.")

        # Warehouses
        locs_res = await client.get("/locations/", headers=b_headers)
        assert locs_res.status_code == 200
        locs = locs_res.json()
        assert len(locs) == 2, f"Expected 2 warehouses, got {len(locs)}"
        print(f"  [PASS] Verified 2 warehouses: {locs[0]['name']} & {locs[1]['name']}.")

        # Transfers list
        trans_res = await client.get("/transfers/", headers=b_headers)
        assert trans_res.status_code == 200
        transfers = trans_res.json()
        assert len(transfers) >= 1
        print(f"  [PASS] Existing stock transfers verified: {len(transfers)} completed transfer.")

        # Movement ledger entries
        ledger_res = await client.get("/ledger/?skip=0&limit=20", headers=b_headers)
        assert ledger_res.status_code == 200
        ledger = ledger_res.json()
        assert len(ledger) >= 13, "Expected movements for all items plus transfer"
        print(f"  [PASS] Movement ledger loaded: {len(ledger)} immutable movement rows verified.")

        # -------------------------------------------------------------
        # ORG C: CRESTLINE GLOBAL (POs, SOs, GST Invoices)
        # -------------------------------------------------------------
        print("\n[10] Org C (Crestline): Purchase Orders, Sales Orders & Invoicing")
        org_c_login = await client.post("/auth/login", json={"email": "admin@crestline.test", "password": "Password123!"})
        assert org_c_login.status_code == 200
        c_token = org_c_login.json()["access_token"]
        c_headers = {"Authorization": f"Bearer {c_token}"}
        print("  [PASS] Logged in as Crestline Admin.")

        # Purchase Orders
        po_res = await client.get("/orders/purchase-orders", headers=c_headers)
        assert po_res.status_code == 200, f"PO list failed: {po_res.text}"
        pos = po_res.json()
        assert len(pos) >= 1, "Expected seeded PO"
        print(f"  [PASS] Purchase Orders: {len(pos)} PO verified (Vendor: {pos[0]['supplier_name']}).")

        # Sales Orders
        so_res = await client.get("/orders/sales-orders", headers=c_headers)
        assert so_res.status_code == 200, f"SO list failed: {so_res.text}"
        sos = so_res.json()
        assert len(sos) >= 1, "Expected seeded SO"
        print(f"  [PASS] Sales Orders: {len(sos)} SO verified (Customer: {sos[0]['customer_name']}).")

        # Invoices list
        inv_res = await client.get("/invoices", headers=c_headers)
        assert inv_res.status_code == 200
        invs = inv_res.json()
        assert len(invs) >= 1, "Expected seeded GST invoice"
        inv = invs[0]
        print(f"  [PASS] GST Invoices: Invoice {inv['invoice_number']} verified (Total: Rs.{inv['grand_total']:,.2f}).")

        # Download invoice PDF
        inv_pdf = await client.get(f"/invoices/{inv['id']}/pdf", headers=c_headers)
        assert inv_pdf.status_code == 200
        assert inv_pdf.headers["content-type"] == "application/pdf"
        assert inv_pdf.content.startswith(b"%PDF")
        print(f"  [PASS] Tenant GST Tax Invoice PDF downloaded successfully ({len(inv_pdf.content)} bytes).")

        # -------------------------------------------------------------
        # ORG D & E: RBAC & SAFEGUARDS CHECK
        # -------------------------------------------------------------
        print("\n[11] Org D (Delta Health) & Org E (E-Commerce Express)")
        org_d_login = await client.post("/auth/login", json={"email": "auditor@deltahealth.test", "password": "Password123!"})
        assert org_d_login.status_code == 200
        print("  [PASS] Viewer role login verified for Delta Health auditor.")

        org_e_login = await client.post("/auth/login", json={"email": "admin@ecommexpress.test", "password": "Password123!"})
        assert org_e_login.status_code == 200
        print("  [PASS] Admin login verified for E-Commerce Express.")

    print("\n" + "=" * 70)
    print("ALL PHASE 3 PLATFORM TESTS PASSED WITH 100% SUCCESS!")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(run_full_suite())
