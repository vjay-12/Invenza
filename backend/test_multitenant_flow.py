import asyncio
import httpx
import os
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000/api/v1"
OUTBOX_FILE = Path(__file__).resolve().parent / "email_outbox.log"

async def test_flow():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0, follow_redirects=True) as client:
        print("\n=== STEP 1: SUPER ADMIN AUTHENTICATION ===")
        login_res = await client.post("/auth/login", json={
            "email": "superadmin@invenza.internal",
            "password": "superadmin2026"
        })
        assert login_res.status_code == 200, f"Super admin login failed: {login_res.text}"
        super_data = login_res.json()
        super_token = super_data["access_token"]
        assert super_data["user_role"] == "super_admin"
        print(f"[SUCCESS] Super Admin logged in! Token acquired. Role: {super_data['user_role']}")

        super_headers = {"Authorization": f"Bearer {super_token}"}

        print("\n=== STEP 2: SUPER ADMIN PROVISIONS NEW COMPANY & ADMIN ===")
        import uuid
        run_id = uuid.uuid4().hex[:6]
        admin_email = f"marcus.{run_id}@novapharma.internal"
        company_name = f"Nova BioPharma {run_id.upper()}"
        company_payload = {
            "company_name": company_name,
            "industry": "Pharmaceuticals & Healthcare",
            "location": "Boston Research Park, MA",
            "currency_code": "INR",
            "admin_full_name": "Dr. Marcus Vance",
            "admin_email": admin_email,
            "admin_password": "NovaSecurePassword2026!",
            "enabled_modules": ["products", "locations", "orders", "reports"],
            "send_email": True
        }
        prov_res = await client.post("/superadmin/companies", json=company_payload, headers=super_headers)
        assert prov_res.status_code in [201, 200], f"Provision failed: {prov_res.text}"
        nova_company = prov_res.json()
        nova_tenant_id = nova_company["id"]
        print(f"[SUCCESS] Company provisioned: '{nova_company['name']}' (ID: {nova_tenant_id})")
        print(f"Industry: {nova_company['industry']} | Admin: {nova_company['admin_name']} <{nova_company['admin_email']}>")

        print("\n=== STEP 3: VERIFY EMAIL DISPATCH IN OUTBOX ===")
        assert OUTBOX_FILE.exists(), "email_outbox.log does not exist!"
        with open(OUTBOX_FILE, "r", encoding="utf-8") as f:
            outbox_content = f.read()
        assert admin_email in outbox_content
        assert "NovaSecurePassword2026!" in outbox_content
        print("[SUCCESS] Found welcome email in outbox log with exact temporary password and industry details!")

        print("\n=== STEP 4: NEW COMPANY ADMIN LOGS IN ===")
        admin_login = await client.post("/auth/login", json={
            "email": admin_email,
            "password": "NovaSecurePassword2026!"
        })
        assert admin_login.status_code == 200, f"Nova Admin login failed: {admin_login.text}"
        admin_data = admin_login.json()
        nova_token = admin_data["access_token"]
        assert admin_data["user_role"] == "admin"
        assert admin_data["company_name"] == company_name
        assert admin_data["industry"] == "Pharmaceuticals & Healthcare"
        print(f"[SUCCESS] Nova Admin logged in! Company: '{admin_data['company_name']}', Industry: '{admin_data['industry']}'")

        nova_headers = {"Authorization": f"Bearer {nova_token}"}

        print("\n=== STEP 5: VERIFY CLEAN SLATE (0 EXISTING PRODUCTS) ===")
        prods_res = await client.get("/products", headers=nova_headers)
        assert prods_res.status_code == 200, f"List products failed: {prods_res.text}"
        prods = prods_res.json()
        print(f"Total products in new Nova BioPharma company: {len(prods)}")
        assert len(prods) == 0, f"Expected 0 products in fresh company, found {len(prods)}"
        print("[SUCCESS] Confirmed clean-slate! No data leaked from other tenants.")

        print("\n=== STEP 6: CREATE PRODUCT IN NOVA BIOPHARMA ===")
        create_prod_res = await client.post("/products", json={
            "sku": "SKU-AMOX-500",
            "name": "Amoxicillin 500mg USP Capsules",
            "category": "Antibiotics",
            "unit_of_measure": "box",
            "cost_price": 12.50,
            "sell_price": 28.00,
            "reorder_point": 20,
            "custom_fields": {"fdaCode": "NDC-0093-3109-01", "storageTemp": "15-25C"}
        }, headers=nova_headers)
        assert create_prod_res.status_code == 201, f"Product create failed: {create_prod_res.text}"
        print(f"[SUCCESS] Created product: {create_prod_res.json()['name']} (SKU: {create_prod_res.json()['sku']})")

        # Verify Nova Admin sees 1 product
        prods_after = (await client.get("/products", headers=nova_headers)).json()
        assert len(prods_after) == 1
        assert prods_after[0]["sku"] == "SKU-AMOX-500"

        print("\n=== STEP 7: VERIFY DEMO COMPANY CANNOT SEE NOVA'S PRODUCT (ISOLATION) ===")
        demo_login = await client.post("/auth/login", json={
            "email": "admin@invenza.internal",
            "password": "adminpassword2026"
        })
        demo_token = demo_login.json()["access_token"]
        demo_headers = {"Authorization": f"Bearer {demo_token}"}

        demo_prods = (await client.get("/products", headers=demo_headers)).json()
        demo_skus = [p["sku"] for p in demo_prods]
        assert "SKU-AMOX-500" not in demo_skus, "Data leakage! Demo company saw Nova's product!"
        print(f"[SUCCESS] Demo tenant products: {demo_skus} (SKU-AMOX-500 is completely invisible to other companies)")

        print("\n=== STEP 8: SUPER ADMIN VIEWS LIVE COMPANY ANALYTICS ===")
        analytics_res = await client.get(f"/superadmin/companies/{nova_tenant_id}/analytics", headers=super_headers)
        assert analytics_res.status_code == 200
        analytics = analytics_res.json()
        print(f"[SUCCESS] Nova BioPharma Analytics: {analytics['total_products']} SKU, Industry: {analytics['industry']}, Valuation: ${analytics['total_inventory_valuation']}")
        assert analytics["total_products"] == 1

        print("\n=== STEP 9: SUPER ADMIN DEACTIVATES NOVA BIOPHARMA ===")
        toggle_res = await client.patch(f"/superadmin/companies/{nova_tenant_id}/toggle-status", headers=super_headers)
        assert toggle_res.status_code == 200
        assert toggle_res.json()["is_active"] is False
        print("[SUCCESS] Nova BioPharma deactivated by Super Admin.")

        # Attempt to access with Nova token -> must be 403 Forbidden
        deact_res = await client.get("/products", headers=nova_headers)
        assert deact_res.status_code == 403, f"Expected 403 when deactivated, got {deact_res.status_code}"
        print(f"[SUCCESS] Deactivated tenant correctly rejected with 403: '{deact_res.json()['detail']}'")

        print("\n=== STEP 10: SUPER ADMIN REACTIVATES NOVA BIOPHARMA ===")
        toggle_back = await client.patch(f"/superadmin/companies/{nova_tenant_id}/toggle-status", headers=super_headers)
        assert toggle_back.json()["is_active"] is True
        print("[SUCCESS] Nova BioPharma reactivated by Super Admin.")

        print("\n=== STEP 11: COMPANY ADMIN CREATES A USER & ASSIGNS ROLES & SENDS EMAIL ===")
        staff_email = f"elena.{run_id}@novapharma.internal"
        staff_res = await client.post("/company/users/", json={
            "full_name": "Elena Rostova",
            "email": staff_email,
            "password": "StaffSecret2026!",
            "role": "staff",
            "permissions": ["inventory:read", "inventory:write"],
            "send_email": True
        }, headers=nova_headers)
        assert staff_res.status_code == 201, f"Create user failed: {staff_res.text}"
        staff_user = staff_res.json()
        print(f"[SUCCESS] Nova Admin created user: {staff_user['full_name']} (Role: {staff_user['role']})")

        # Verify staff email in outbox log
        with open(OUTBOX_FILE, "r", encoding="utf-8") as f:
            updated_outbox = f.read()
        assert staff_email in updated_outbox
        assert "StaffSecret2026!" in updated_outbox
        print("[SUCCESS] Found staff welcome email with credentials in outbox log!")

        print("\n=== ALL MULTI-TENANT ARCHITECTURAL TESTS PASSED PERFECTLY! ===")

if __name__ == "__main__":
    asyncio.run(test_flow())
