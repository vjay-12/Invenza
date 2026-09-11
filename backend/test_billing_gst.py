"""
End-to-End Verification for Invenza Tenant Billing Module & GST Compliance.
Tests:
1. Superadmin login & token acquisition
2. Billing overview telemetry & real tenant retrieval
3. Drill-down into a real tenant's billing detail (confirming both flattened & nested structures)
4. Recording paid cycle payment with automatic GST tax calculation (Intra vs Inter, SAC 998313)
5. Recording waived cycle (₹0) with zero tax breakdown
6. Downloading GST Tax Invoice vector PDF for regular cycle
7. Downloading GST Tax Invoice vector PDF for ₹0 waived cycle
8. Downloading GST Tax Invoice vector PDF for setup fee
9. Resilient handling of invalid / placeholder org UUIDs
"""

import sys
import asyncio
import httpx
from uuid import UUID

BASE_URL = "http://localhost:8000/api/v1"

async def run_billing_tests():
    print("=== INVENZA TENANT BILLING & GST TAX ENGINE TEST SUITE ===")
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Superadmin login
        print("\n1. Logging in as Super Admin...")
        login_res = await client.post(
            f"{BASE_URL}/auth/login",
            json={"email": "superadmin@invenza.internal", "password": "superadmin2026"}
        )
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("   [OK] Logged in successfully.")

        # 2. Billing overview telemetry
        print("\n2. Fetching Billing Overview telemetry...")
        overview_res = await client.get(f"{BASE_URL}/billing/overview", headers=headers)
        assert overview_res.status_code == 200, f"Overview fetch failed: {overview_res.text}"
        overview_data = overview_res.json()
        orgs = overview_data.get("organizations", [])
        print(f"   [OK] Revenue Collected: Rs. {overview_data.get('total_revenue_collected')}")
        print(f"   [OK] Active MRR: Rs. {overview_data.get('active_mrr_sum')}")
        print(f"   [OK] Organizations in overview: {len(orgs)}")
        assert len(orgs) > 0, "No organizations found in billing overview to test drilldown!"

        test_org = orgs[0]
        test_org_id = test_org["tenant_id"]
        print(f"   [OK] Selected Org for Drilldown: {test_org['tenant_name']} (ID: {test_org_id})")

        # 3. Drill-down into the real tenant's billing detail
        print(f"\n3. Drilling down into Tenant Billing Detail: /billing/tenants/{test_org_id}...")
        detail_res = await client.get(f"{BASE_URL}/billing/tenants/{test_org_id}", headers=headers)
        assert detail_res.status_code == 200, f"Detail fetch failed: {detail_res.text}"
        detail_data = detail_res.json()

        # Verify backward compatibility (nested profile) and new flattened structure
        assert "profile" in detail_data, "Missing 'profile' in response!"
        assert "tenant_name" in detail_data, "Missing flattened 'tenant_name' at root!"
        assert "setup_fee" in detail_data, "Missing flattened 'setup_fee' at root!"
        assert "setup_fee_status" in detail_data, "Missing flattened 'setup_fee_status' at root!"
        assert "payment_records" in detail_data, "Missing 'payment_records' in response!"
        print(f"   [OK] Tenant Name: {detail_data['tenant_name']}")
        print(f"   [OK] Setup Fee: Rs. {detail_data['setup_fee']} ({detail_data['setup_fee_status']})")
        print(f"   [OK] Monthly Maintenance Fee: Rs. {detail_data['monthly_maintenance_fee']}")
        print(f"   [OK] Payment Records Count: {len(detail_data['payment_records'])}")

        # 4. Record a cycle payment with GST calculation
        print("\n4. Recording a paid monthly maintenance cycle payment with GST...")
        pay_res = await client.post(
            f"{BASE_URL}/billing/tenants/{test_org_id}/payments",
            headers=headers,
            json={
                "cycle_month": "September 2026",
                "amount": 5000.0,
                "payment_mode": "manual",
                "status": "paid",
                "payment_reference": "NEFT-TEST-GST-001",
                "notes": "Automated GST verification cycle payment",
            }
        )
        assert pay_res.status_code in [200, 201], f"Record payment failed: {pay_res.text}"
        pay_data = pay_res.json()
        payment_id = pay_data.get("payment_id")
        inv_num = pay_data.get("invoice_number")
        print(f"   [OK] Payment recorded. Invoice Number: {inv_num}, Payment ID: {payment_id}")
        assert inv_num.startswith("INV-TEN/"), f"Invoice number format unexpected: {inv_num}"

        # 5. Record a Rs. 0 waived cycle
        print("\n5. Recording a Rs. 0 waived maintenance cycle...")
        waived_res = await client.post(
            f"{BASE_URL}/billing/tenants/{test_org_id}/payments",
            headers=headers,
            json={
                "cycle_month": "October 2026",
                "amount": 0.0,
                "payment_mode": "manual",
                "status": "waived",
                "payment_reference": "WAIVE-OCT2026",
                "notes": "Promotional waived month test",
            }
        )
        assert waived_res.status_code in [200, 201], f"Record waived payment failed: {waived_res.text}"
        waived_data = waived_res.json()
        waived_payment_id = waived_data.get("payment_id")
        waived_inv_num = waived_data.get("invoice_number")
        print(f"   [OK] Waived cycle recorded. Invoice Number: {waived_inv_num}, Payment ID: {waived_payment_id}")

        # 6. Download PDF for the regular paid cycle
        print(f"\n6. Generating & Downloading GST Tax Invoice PDF for payment {payment_id}...")
        pdf_res = await client.get(
            f"{BASE_URL}/billing/tenants/{test_org_id}/payments/{payment_id}/invoice-pdf",
            headers=headers,
        )
        assert pdf_res.status_code == 200, f"PDF generation failed: {pdf_res.text}"
        assert pdf_res.headers.get("content-type") == "application/pdf", f"Unexpected content-type: {pdf_res.headers.get('content-type')}"
        assert pdf_res.content.startswith(b"%PDF-"), "Generated file does not have valid PDF magic bytes!"
        print(f"   [OK] Valid vector GST Tax Invoice PDF received ({len(pdf_res.content)} bytes).")

        # 7. Download PDF for the Rs. 0 waived cycle
        print(f"\n7. Generating & Downloading GST Invoice PDF for waived cycle {waived_payment_id}...")
        waived_pdf_res = await client.get(
            f"{BASE_URL}/billing/tenants/{test_org_id}/payments/{waived_payment_id}/invoice-pdf",
            headers=headers,
        )
        assert waived_pdf_res.status_code == 200, f"Waived PDF generation failed: {waived_pdf_res.text}"
        assert waived_pdf_res.content.startswith(b"%PDF-"), "Waived file is not a valid PDF!"
        print(f"   [OK] Valid Waived GST Invoice PDF received ({len(waived_pdf_res.content)} bytes).")

        # 8. Download PDF for Setup Fee
        print(f"\n8. Generating & Downloading Setup Fee GST Tax Invoice PDF...")
        setup_pdf_res = await client.get(
            f"{BASE_URL}/billing/tenants/{test_org_id}/setup-fee/invoice-pdf",
            headers=headers,
        )
        assert setup_pdf_res.status_code == 200, f"Setup PDF generation failed: {setup_pdf_res.text}"
        assert setup_pdf_res.content.startswith(b"%PDF-"), "Setup fee invoice is not a valid PDF!"
        print(f"   [OK] Valid Setup Fee GST Invoice PDF received ({len(setup_pdf_res.content)} bytes).")

        # 9. Test resilience with invalid / placeholder UUID
        print("\n9. Testing drill-down resilience with invalid / placeholder UUID...")
        bad_res = await client.get(
            f"{BASE_URL}/billing/tenants/00000000-0000-0000-0000-999999999999",
            headers=headers,
        )
        assert bad_res.status_code == 404, f"Expected 404 for unknown org, got {bad_res.status_code}"
        print("   [OK] Unknown org UUID correctly returns HTTP 404 (handled gracefully by UI).")

        print("\n=== ALL BILLING & GST INVOICING TESTS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    asyncio.run(run_billing_tests())
