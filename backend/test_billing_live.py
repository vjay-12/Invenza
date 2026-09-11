"""
Live End-to-End Test for Invenza Billing Module against http://127.0.0.1:8000
"""
import sys
import uuid
import httpx

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

BASE_URL = "http://127.0.0.1:8000"

def main():
    print("==================================================")
    print("STARTING LIVE BILLING MODULE VERIFICATION")
    print("==================================================")

    client = httpx.Client(base_url=BASE_URL, timeout=30.0)

    # 1. Login as SuperAdmin
    login_payload = {
        "email": "superadmin@invenza.internal",
        "password": "superadmin2026"
    }
    res_login = client.post("/api/v1/auth/login", json=login_payload)
    assert res_login.status_code == 200, f"SuperAdmin login failed: {res_login.status_code} {res_login.text}"
    token = res_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("[AUTH] SuperAdmin authenticated successfully via /api/v1/auth/login")

    # -------------------------------------------------------------
    # STEP 1: PROVISIONING VALIDATION & BILLING INITIALIZATION
    # -------------------------------------------------------------
    print("\n--- STEP 1: Provisioning Form Validation & Initial Billing Records ---")
    unique_suffix = str(uuid.uuid4())[:6]

    # 1A. Missing fees validation
    invalid_payload = {
        "company_name": f"Missing Fee Org {unique_suffix}",
        "company_code": f"MFO{unique_suffix.upper()}",
        "admin_email": f"mfoadmin-{unique_suffix}@example.com",
        "admin_full_name": "MFO Admin",
        "admin_password": "Password@123",
        "industry": "Manufacturing",
        "location": "Bengaluru, Karnataka",
        # Missing setup_fee and monthly_maintenance_fee
    }
    res_inv = client.post("/api/v1/superadmin/companies", json=invalid_payload, headers=headers)
    assert res_inv.status_code == 422, f"Expected 422 for missing fees, got {res_inv.status_code}"
    print("[PASS] Provisioning rejected missing setup_fee/monthly_maintenance_fee (422 Unprocessable Entity)")

    # 1B. Negative fees validation
    neg_payload = invalid_payload.copy()
    neg_payload["setup_fee"] = -1000.0
    neg_payload["monthly_maintenance_fee"] = 500.0
    res_neg = client.post("/api/v1/superadmin/companies", json=neg_payload, headers=headers)
    assert res_neg.status_code == 422, f"Expected 422 for negative fee, got {res_neg.status_code}"
    print("[PASS] Provisioning rejected negative fees (422 Unprocessable Entity)")

    # 1C. Provision Karnataka tenant (Intra-state)
    org1_payload = {
        "company_name": f"Bangalore Tech Services {unique_suffix}",
        "company_code": f"KA{unique_suffix.upper()}",
        "admin_email": f"btsadmin-{unique_suffix}@example.com",
        "admin_full_name": "BTS Admin",
        "admin_password": "Password@123",
        "industry": "Technology",
        "location": "Bengaluru, Karnataka",
        "setup_fee": 15000.0,
        "monthly_maintenance_fee": 3000.0,
        "send_email": False
    }
    res_org1 = client.post("/api/v1/superadmin/companies", json=org1_payload, headers=headers)
    assert res_org1.status_code == 201, f"Failed to provision Org 1: {res_org1.status_code} {res_org1.text}"
    org1_id = res_org1.json()["id"]
    print(f"[PASS] Provisioned Org 1 (Karnataka, ID: {org1_id}) with Setup Fee=INR 15,000, Monthly Rate=INR 3,000")

    # 1D. Provision Maharashtra tenant (Inter-state) with INR 0 maintenance
    org2_payload = {
        "company_name": f"Mumbai Retailers {unique_suffix}",
        "company_code": f"MH{unique_suffix.upper()}",
        "admin_email": f"mradmin-{unique_suffix}@example.com",
        "admin_full_name": "MR Admin",
        "admin_password": "Password@123",
        "industry": "Retail",
        "location": "Mumbai, Maharashtra",
        "setup_fee": 20000.0,
        "monthly_maintenance_fee": 0.0,
        "send_email": False
    }
    res_org2 = client.post("/api/v1/superadmin/companies", json=org2_payload, headers=headers)
    assert res_org2.status_code == 201, f"Failed to provision Org 2: {res_org2.status_code} {res_org2.text}"
    org2_id = res_org2.json()["id"]
    print(f"[PASS] Provisioned Org 2 (Maharashtra, ID: {org2_id}) with Setup Fee=INR 20,000, Monthly Rate=INR 0")

    # -------------------------------------------------------------
    # STEP 2: ORG DRILL-DOWN INITIAL STATE
    # -------------------------------------------------------------
    print("\n--- STEP 2: Org Drill-Down (/billing/tenants/{id}) Verification ---")
    res_drill1 = client.get(f"/api/v1/billing/tenants/{org1_id}", headers=headers)
    assert res_drill1.status_code == 200, f"Drilldown failed: {res_drill1.status_code} {res_drill1.text}"
    drill1 = res_drill1.json()
    assert drill1["setup_fee"]["amount"] == 15000.0
    assert drill1["setup_fee"]["status"] == "Pending"
    assert drill1["current_maintenance_plan"]["current_rate"] == 3000.0
    assert len(drill1["rate_history"]) == 1
    assert len(drill1["transactions"]) >= 2  # Setup fee + initial cycle
    setup_fee_1_id = drill1["setup_fee"]["id"]
    print(f"[PASS] Org 1 drill-down data verified: Setup Fee=Pending (INR 15,000), Current Rate=INR 3,000/mo, Transactions={len(drill1['transactions'])}")

    res_drill2 = client.get(f"/api/v1/billing/tenants/{org2_id}", headers=headers)
    assert res_drill2.status_code == 200
    drill2 = res_drill2.json()
    assert drill2["setup_fee"]["amount"] == 20000.0
    assert drill2["current_maintenance_plan"]["current_rate"] == 0.0
    setup_fee_2_id = drill2["setup_fee"]["id"]
    print(f"[PASS] Org 2 drill-down data verified: Setup Fee=Pending (INR 20,000), Current Rate=INR 0/mo")

    # -------------------------------------------------------------
    # STEP 3: AUTO-GENERATION & MONTH ROLLOVER
    # -------------------------------------------------------------
    print("\n--- STEP 3: Auto-Generation & Month Rollover Simulation ---")
    simulated_month = "2026-11"
    res_gen = client.post(f"/api/v1/billing/cycles/generate?cycle_month={simulated_month}", headers=headers)
    assert res_gen.status_code == 200, f"Cycle generation failed: {res_gen.status_code} {res_gen.text}"
    gen_result = res_gen.json()
    print(f"[PASS] Rollover generated {gen_result['created_count']} cycle records for {simulated_month}")

    # Idempotency check
    res_gen_idem = client.post(f"/api/v1/billing/cycles/generate?cycle_month={simulated_month}", headers=headers)
    assert res_gen_idem.status_code == 200
    assert res_gen_idem.json()["created_count"] == 0
    print("[PASS] Generation idempotency verified: 0 duplicate rows on re-execution")

    # Re-fetch drilldown to verify the new November cycle
    res_drill1_after_gen = client.get(f"/api/v1/billing/tenants/{org1_id}", headers=headers)
    nov_cycle_org1 = next(
        (t for t in res_drill1_after_gen.json()["transactions"] if simulated_month in str(t.get("cycle_month", ""))),
        None
    )
    assert nov_cycle_org1 is not None, f"November cycle missing for Org 1"
    assert nov_cycle_org1["amount"] == 3000.0
    assert nov_cycle_org1["status"] == "Pending"
    nov_cycle_1_id = nov_cycle_org1["id"]
    print(f"[PASS] November cycle verified for Org 1: Month={nov_cycle_org1['cycle_month']}, Amount=INR {nov_cycle_org1['amount']}, Status={nov_cycle_org1['status']}")

    # -------------------------------------------------------------
    # STEP 4: MARK AS PAID ON SETUP FEE (INTRA-STATE GST INVOICING)
    # -------------------------------------------------------------
    print("\n--- STEP 4: Setup Fee 'Mark as Paid' + GST Invoice (Intra-State: Karnataka) ---")
    pay_sf_payload = {
        "amount": 15000.0,
        "payment_date": "2026-09-11",
        "payment_mode": "Bank Transfer",
        "note": "Payment received via HDFC NEFT Ref #TXN889900"
    }
    res_pay_sf = client.post(f"/api/v1/billing/setup-fee/{setup_fee_1_id}/mark-paid", json=pay_sf_payload, headers=headers)
    assert res_pay_sf.status_code == 200, f"Mark setup fee paid failed: {res_pay_sf.status_code} {res_pay_sf.text}"
    sf_pay_data = res_pay_sf.json()
    invoice_number = sf_pay_data["invoice_number"]
    print(f"[PASS] Setup fee marked Paid. Auto-generated sequential invoice: {invoice_number}")

    # Verify drilldown reflects Paid status and generated invoice
    res_drill1_paid = client.get(f"/api/v1/billing/tenants/{org1_id}", headers=headers)
    drill1_paid = res_drill1_paid.json()
    sf_row = drill1_paid["setup_fee"]
    assert sf_row["status"] == "Paid"
    assert sf_row["payment_mode"] == "Bank Transfer"
    assert sf_row["gst_invoice_id"] is not None
    assert sf_row["invoice_number"] == invoice_number
    print(f"[PASS] Org 1 setup fee row updated: Status=Paid, Mode=Bank Transfer, Invoice={invoice_number}")

    # Verify GST Tax amounts: Intra-State (Karnataka seller + Karnataka buyer): 9% CGST + 9% SGST, 0% IGST
    assert sf_pay_data["tax_summary"]["cgst"] == 1350.0
    assert sf_pay_data["tax_summary"]["sgst"] == 1350.0
    assert sf_pay_data["tax_summary"]["igst"] == 0.0
    assert sf_pay_data["tax_summary"]["total"] == 17700.0
    print(f"[PASS] Intra-state GST Breakdown verified: Base=INR 15,000 + CGST (9%)=INR 1,350 + SGST (9%)=INR 1,350 -> Total=INR 17,700")

    # Guardrail: Cannot mark as Paid twice
    res_sf_double = client.post(f"/api/v1/billing/setup-fee/{setup_fee_1_id}/mark-paid", json=pay_sf_payload, headers=headers)
    assert res_sf_double.status_code == 400, f"Expected 400 for double pay, got {res_sf_double.status_code}"
    print("[PASS] Double-payment guardrail verified: Second payment attempt returned 400 Bad Request")

    # -------------------------------------------------------------
    # STEP 5: RATE UPDATE & APPEND-ONLY RATE HISTORY
    # -------------------------------------------------------------
    print("\n--- STEP 5: Rate Update & Append-Only Plan History ---")
    update_rate_payload = {
        "new_rate": 4500.0,
        "effective_from": "2026-12-01",
        "reason": "Enterprise Tier Upgrade with 50GB storage"
    }
    res_update_rate = client.post(f"/api/v1/billing/tenants/{org1_id}/maintenance-plan", json=update_rate_payload, headers=headers)
    assert res_update_rate.status_code == 200, f"Rate update failed: {res_update_rate.status_code} {res_update_rate.text}"
    
    # Check drilldown history
    res_drill1_updated = client.get(f"/api/v1/billing/tenants/{org1_id}", headers=headers)
    drill1_updated = res_drill1_updated.json()
    assert drill1_updated["current_maintenance_plan"]["current_rate"] == 4500.0
    history = drill1_updated["rate_history"]
    assert len(history) == 2, f"Expected 2 rate history entries, got {len(history)}"
    assert history[0]["current_rate"] == 4500.0
    assert history[0]["reason"] == "Enterprise Tier Upgrade with 50GB storage"
    assert history[1]["current_rate"] == 3000.0, "Original rate row was overwritten!"
    print(f"[PASS] Rate history verified: {len(history)} entries (Newest: INR 4,500/mo, Previous: INR 3,000/mo). Append-only verified!")

    # Snapshot integrity check: Past cycles must retain their historical amounts
    past_nov_cycle = next(t for t in drill1_updated["transactions"] if simulated_month in str(t.get("cycle_month", "")))
    assert past_nov_cycle["amount"] == 3000.0, f"Past cycle amount changed to {past_nov_cycle['amount']}! Snapshot was violated!"
    print("[PASS] Snapshot rate integrity verified: November cycle retained its INR 3,000 amount despite new rate")

    # -------------------------------------------------------------
    # STEP 6: INTER-STATE GST INVOICE ON CYCLE PAYMENT
    # -------------------------------------------------------------
    print("\n--- STEP 6: Cycle 'Mark as Paid' + GST Invoice (Inter-State: Maharashtra) ---")
    # Org 2: Update rate to 6000 first
    client.post(f"/api/v1/billing/tenants/{org2_id}/maintenance-plan", json={
        "new_rate": 6000.0,
        "effective_from": "2026-12-01",
        "reason": "Commercial SLA agreement"
    }, headers=headers)

    # Generate cycle for 2026-12
    client.post("/api/v1/billing/cycles/generate?cycle_month=2026-12", headers=headers)
    res_drill2_fresh = client.get(f"/api/v1/billing/tenants/{org2_id}", headers=headers)
    dec_cycle_org2 = next(t for t in res_drill2_fresh.json()["transactions"] if "2026-12" in str(t.get("cycle_month", "")))
    assert dec_cycle_org2["amount"] == 6000.0
    dec_cycle_2_id = dec_cycle_org2["id"]

    pay_cycle_payload = {
        "amount": 6000.0,
        "payment_date": "2026-09-11",
        "payment_mode": "UPI",
        "note": "Paid via UPI QR code"
    }
    res_pay_cy = client.post(f"/api/v1/billing/cycles/{dec_cycle_2_id}/mark-paid", json=pay_cycle_payload, headers=headers)
    assert res_pay_cy.status_code == 200, f"Mark cycle paid failed: {res_pay_cy.status_code} {res_pay_cy.text}"
    cy_pay_data = res_pay_cy.json()
    print(f"[PASS] Cycle marked Paid. Auto-generated invoice: {cy_pay_data['invoice_number']}")

    # Inter-state Tax Check (Karnataka seller + Maharashtra buyer): 18% IGST, 0% CGST/SGST
    tax = cy_pay_data["tax_summary"]
    assert tax["igst"] == 1080.0, f"Expected IGST 1080, got {tax['igst']}"
    assert tax["cgst"] == 0.0, f"Expected CGST 0 for inter-state, got {tax['cgst']}"
    assert tax["sgst"] == 0.0, f"Expected SGST 0 for inter-state, got {tax['sgst']}"
    assert tax["total"] == 7080.0, f"Expected total 7080, got {tax['total']}"
    print(f"[PASS] Inter-state GST Breakdown verified: Base=INR 6,000 + IGST (18%)=INR 1,080 -> Total=INR 7,080")

    # -------------------------------------------------------------
    # STEP 7: CYCLE 'MARK AS WAIVED' (NO INVOICE GENERATION)
    # -------------------------------------------------------------
    print("\n--- STEP 7: Cycle 'Mark as Waived' (Zero Invoicing & Audit Log) ---")
    waive_payload = {
        "reason": "Promotional launch waiver approved by Management"
    }
    res_waive = client.post(f"/api/v1/billing/cycles/{nov_cycle_1_id}/mark-waived", json=waive_payload, headers=headers)
    assert res_waive.status_code == 200, f"Mark waived failed: {res_waive.status_code} {res_waive.text}"
    waive_data = res_waive.json()
    assert waive_data["status"] == "Waived"
    assert waive_data["gst_invoice_id"] is None, "CRITICAL: Waived cycle must have gst_invoice_id=None!"
    assert waive_data["invoice_number"] is None
    print("[PASS] Waived cycle confirmed: Status=Waived, No GST Invoice generated")

    # Guardrails on finalized waived row
    res_w_double = client.post(f"/api/v1/billing/cycles/{nov_cycle_1_id}/mark-waived", json=waive_payload, headers=headers)
    assert res_w_double.status_code == 400
    res_w_pay = client.post(f"/api/v1/billing/cycles/{nov_cycle_1_id}/mark-paid", json=pay_cycle_payload, headers=headers)
    assert res_w_pay.status_code == 400
    print("[PASS] Guardrails verified: Finalized waived cycle cannot be re-waived or paid (400 Bad Request)")

    # -------------------------------------------------------------
    # STEP 8: BILLING OVERVIEW TOP-LEVEL KPIs & TABLE
    # -------------------------------------------------------------
    print("\n--- STEP 8: Top-Level Overview Page (/billing/overview) ---")
    res_overview = client.get("/api/v1/billing/overview", headers=headers)
    assert res_overview.status_code == 200, f"Overview failed: {res_overview.status_code} {res_overview.text}"
    overview = res_overview.json()
    cards = overview.get("summary_cards") or overview
    print(f"Summary Cards:")
    print(f"  - Total Revenue Collected: INR {cards['total_revenue_collected']:,.2f}")
    print(f"  - Pending Setup Fees: {cards['pending_setup_fees_count']} orgs (INR {cards['pending_setup_fees_amount']:,.2f})")
    print(f"  - Active Monthly Recurring: INR {cards['active_monthly_recurring']:,.2f}/mo")
    print(f"  - Orgs on INR 0 Maintenance: {cards['zero_maintenance_orgs_count']}")
    print(f"  - Overdue Count: {cards['overdue_count']}")

    assert cards["total_revenue_collected"] > 0
    org_list = overview.get("organizations") or overview.get("tenants")
    assert len(org_list) >= 2
    tenant_org1 = next(t for t in org_list if str(t["id"]) == str(org1_id))
    assert tenant_org1["setup_fee_status"] == "Paid"
    assert tenant_org1["current_monthly_rate"] == 4500.0
    print(f"[PASS] Overview tenant row verified: Org 1 Setup Status={tenant_org1['setup_fee_status']}, Monthly Rate=INR {tenant_org1['current_monthly_rate']}")

    # -------------------------------------------------------------
    # STEP 9: PDF INVOICE DOWNLOADS
    # -------------------------------------------------------------
    print("\n--- STEP 9: PDF Invoice Downloads ---")
    res_sf_pdf = client.get(f"/api/v1/billing/setup-fee/{setup_fee_1_id}/invoice-pdf", headers=headers)
    assert res_sf_pdf.status_code == 200
    assert res_sf_pdf.headers.get("content-type") == "application/pdf"
    assert len(res_sf_pdf.content) > 1000
    print(f"[PASS] Setup fee invoice PDF downloaded successfully ({len(res_sf_pdf.content)} bytes)")

    res_cy_pdf = client.get(f"/api/v1/billing/cycles/{dec_cycle_2_id}/invoice-pdf", headers=headers)
    assert res_cy_pdf.status_code == 200
    assert res_cy_pdf.headers.get("content-type") == "application/pdf"
    assert len(res_cy_pdf.content) > 1000
    print(f"[PASS] Cycle invoice PDF downloaded successfully ({len(res_cy_pdf.content)} bytes)")

    print("\n==================================================")
    print("ALL BILLING MODULE REQUIREMENTS CONFIRMED WORKING!")
    print("==================================================")

if __name__ == "__main__":
    main()
