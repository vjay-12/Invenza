"""
Live End-to-End Multi-Tax / Multi-Currency Billing Test against http://127.0.0.1:8000

Covers the acceptance checklist:
  1. Provision DE org  -> EUR currency, VAT 19% on setup-fee invoice
  2. Provision CA org  -> USD currency, Sales Tax 7.25%
  3. Provision DE(US) org (Delaware) -> USD, explicit 0% Sales Tax line (not blank)
  4. INR regression    -> Karnataka intra-state CGST 9% + SGST 9% unchanged
  5. Locked fields     -> changing Country/State/Currency after provisioning -> 400
  6. Unsupported country -> 400

Run order: start API (uvicorn app.main:app), then:
    cd backend && python test_multitax_billing.py
"""
import sys
import uuid
import httpx

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE_URL = "http://127.0.0.1:8000"


def approx(a, b, tol=0.011):
    return abs(float(a) - float(b)) <= tol


def main():
    print("==================================================")
    print("MULTI-TAX / MULTI-CURRENCY LIVE VERIFICATION")
    print("==================================================")
    client = httpx.Client(base_url=BASE_URL, timeout=30.0)

    res = client.post("/api/v1/auth/login", json={
        "email": "superadmin@invenza.internal", "password": "superadmin2026",
    })
    assert res.status_code == 200, f"SuperAdmin login failed: {res.text}"
    headers = {"Authorization": f"Bearer {res.json()['access_token']}"}
    print("[AUTH] SuperAdmin authenticated")

    sfx = str(uuid.uuid4())[:6].upper()

    def provision(code, name, country, state=None, setup=2400.0, monthly=390.0, expect_status=201):
        payload = {
            "company_name": name,
            "company_code": code,
            "unique_code": code,
            "admin_email": f"admin-{code.lower()}-{sfx.lower()}@example.com",
            "admin_full_name": f"{name} Admin",
            "admin_password": "Password@123",
            "industry": "Manufacturing",
            "location": name,
            "country_code": country,
            "setup_fee": setup,
            "monthly_maintenance_fee": monthly,
            "send_email": False,
        }
        if state:
            payload["state"] = state
        r = client.post("/api/v1/superadmin/companies", json=payload, headers=headers)
        assert r.status_code == expect_status, f"Provision {code}: expected {expect_status}, got {r.status_code}: {r.text}"
        return r.json() if r.status_code == 201 else None

    def mark_setup_fee_paid_and_get_invoice(tenant_id, org_code):
        ov = client.get("/api/v1/billing/overview", headers=headers)
        assert ov.status_code == 200, f"Overview failed: {ov.text}"
        org_row = next((o for o in ov.json()["organizations"] if o["tenant_id"] == tenant_id), None)
        assert org_row, f"{org_code} not found in billing overview"

        detail = client.get(f"/api/v1/billing/tenants/{tenant_id}", headers=headers)
        assert detail.status_code == 200
        d = detail.json()
        sf = d["setup_fee"]
        assert sf["status"] in ("Pending", "pending"), f"{org_code} setup fee not pending: {sf['status']}"

        mp = client.post(f"/api/v1/billing/setup-fee/{sf['id']}/mark-paid", headers=headers, json={
            "confirmed_amount": float(sf["amount"]), "payment_mode": "Bank Transfer",
        })
        assert mp.status_code == 200, f"mark-paid failed for {org_code}: {mp.status_code} {mp.text}"
        inv_num = mp.json()["invoice_number"]
        print(f"[PASS] {org_code}: setup fee marked paid -> invoice {inv_num}")

        # Super admin reads the org's invoice via tenant header
        inv_list = client.get("/api/v1/invoices", headers={**headers, "X-Tenant-ID": tenant_id})
        assert inv_list.status_code == 200, f"Invoice list failed for {org_code}: {inv_list.text}"
        inv = next((i for i in inv_list.json() if i["invoice_number"] == inv_num), None)
        assert inv, f"Invoice {inv_num} not found for {org_code}"
        return org_row, inv

    # ---------------------------------------------------------------
    print("\n--- STEP 1: Provisioning validation (country/state/currency) ---")
    provision(f"MTBAD{sfx}", "Badlands Corp", "XX", expect_status=400)
    print("[PASS] Unsupported country (XX) rejected with 400")
    provision(f"MTNOS{sfx}", "No State Freight LLC", "US", state=None, expect_status=400)
    print("[PASS] US org without state rejected with 400")

    # ---------------------------------------------------------------
    print("\n--- STEP 2: Germany (EUR / VAT 19%) ---")
    de = provision(f"MTDE{sfx}", "MultiTax Germany GmbH", "DE", state=None, setup=2400.0, monthly=390.0)
    assert de["country_code"] == "DE", f"DE org country_code mismatch: {de['country_code']}"
    org_row, inv = mark_setup_fee_paid_and_get_invoice(de["id"], "DE")
    assert org_row["currency_code"] == "EUR", f"overview currency: {org_row['currency_code']}"
    assert inv["currency_code"] == "EUR" and inv["tax_type"] == "VAT", f"DE invoice regime: {inv['tax_type']}/{inv['currency_code']}"
    assert approx(inv["total_single_tax"], 456.00), f"DE VAT amount: {inv['total_single_tax']} (expected 456.00)"
    assert approx(inv["grand_total"], 2856.00), f"DE grand total: {inv['grand_total']}"
    assert approx(inv["items"][0]["single_tax_rate"], 19.00)
    pdf_res = client.get(f"/api/v1/invoices/{inv['id']}/pdf", headers=headers)
    assert pdf_res.status_code == 200 and pdf_res.headers["content-type"] == "application/pdf", "DE invoice PDF download failed"
    print(f"[PASS] DE: VAT 19%, EUR, taxable {inv['total_taxable_value']} + tax {inv['total_single_tax']} = {inv['grand_total']} (PDF OK, {len(pdf_res.content)} bytes)")

    # ---------------------------------------------------------------
    print("\n--- STEP 3: California (USD / Sales Tax 7.25%) ---")
    ca = provision(f"MTCA{sfx}", "MultiTax California Inc.", "US", state="California", setup=3000.0, monthly=450.0)
    assert ca["country_code"] == "US"
    org_row, inv = mark_setup_fee_paid_and_get_invoice(ca["id"], "CA")
    assert org_row["currency_code"] == "USD"
    assert inv["tax_type"] == "SALES_TAX" and inv["currency_code"] == "USD"
    assert approx(inv["total_single_tax"], 217.50), f"CA sales tax: {inv['total_single_tax']} (expected 217.50)"
    assert approx(inv["grand_total"], 3218.00), f"CA grand total (rounded): {inv['grand_total']}"
    assert approx(inv["items"][0]["single_tax_rate"], 7.25)
    print(f"[PASS] CA: Sales Tax 7.25%, USD, tax {inv['total_single_tax']} -> {inv['grand_total']}")

    # ---------------------------------------------------------------
    print("\n--- STEP 4: Delaware (USD / 0% zero-rate — line must render, not blank) ---")
    dl = provision(f"MTDL{sfx}", "MultiTax Delaware LLC", "US", state="Delaware", setup=2800.0, monthly=420.0)
    org_row, inv = mark_setup_fee_paid_and_get_invoice(dl["id"], "DE-Delaware")
    assert inv["tax_type"] == "SALES_TAX" and inv["currency_code"] == "USD"
    assert float(inv["total_single_tax"]) == 0.0, f"Delaware tax should be 0.00, got {inv['total_single_tax']}"
    assert approx(inv["items"][0]["single_tax_rate"], 0.00), "Delaware item must carry explicit 0% rate"
    assert approx(inv["grand_total"], 2800.00)
    pdf_res = client.get(f"/api/v1/invoices/{inv['id']}/pdf", headers=headers)
    assert pdf_res.status_code == 200 and pdf_res.headers["content-type"] == "application/pdf"
    assert len(pdf_res.content) > 1000, "Delaware PDF looks broken/empty"
    print(f"[PASS] Delaware: explicit 0% Sales Tax line rendered (tax=0.00, grand={inv['grand_total']}, PDF OK, {len(pdf_res.content)} bytes)")

    # ---------------------------------------------------------------
    print("\n--- STEP 5: INR regression (Karnataka intra-state, unchanged GST math) ---")
    ka = provision(f"MTKA{sfx}", "MultiTax Karnataka Services", "IN", state="Karnataka", setup=15000.0, monthly=3000.0)
    assert ka["country_code"] == "IN"
    org_row, inv = mark_setup_fee_paid_and_get_invoice(ka["id"], "KA")
    assert inv["tax_type"] == "GST" and inv["currency_code"] == "INR"
    assert approx(inv["total_cgst"], 1350.00) and approx(inv["total_sgst"], 1350.00), f"KA split: {inv['total_cgst']}/{inv['total_sgst']}"
    assert float(inv["total_igst"]) == 0.0
    assert approx(inv["grand_total"], 17700.00), f"KA grand total: {inv['grand_total']}"
    print(f"[PASS] INR: CGST {inv['total_cgst']} + SGST {inv['total_sgst']} = {inv['grand_total']} (unchanged)")

    # ---------------------------------------------------------------
    print("\n--- STEP 6: Locked Country/State/Currency after provisioning ---")
    for field, value in [("country_code", "US"), ("state", "Maharashtra"), ("currency_code", "USD")]:
        r = client.put(f"/api/v1/superadmin/companies/{ka['id']}", headers=headers, json={field: value})
        assert r.status_code == 400, f"Lock violation: {field} change returned {r.status_code}"
        print(f"[PASS] {field} change rejected with 400 (locked after provisioning)")

    # ---------------------------------------------------------------
    print("\n--- STEP 7: Overview per-currency aggregates ---")
    ov = client.get("/api/v1/billing/overview", headers=headers)
    body = ov.json()
    assert "revenue_by_currency" in body and "mrr_by_currency" in body
    print(f"[PASS] revenue_by_currency: {body['revenue_by_currency']}")
    print(f"[PASS] mrr_by_currency: {body['mrr_by_currency']}")

    print("\n==================================================")
    print("ALL MULTI-TAX LIVE CHECKS PASSED")
    print("==================================================")


if __name__ == "__main__":
    main()
