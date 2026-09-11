import asyncio
import sys
import httpx
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.user import User, UserRole
from app.core.security import create_access_token

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

BASE_URL = "http://127.0.0.1:8000/api/v1"

async def run_end_to_end_verification():
    print("\n" + "="*70)
    print("INVENZA SUPER ADMIN CONSOLE REDESIGN - END-TO-END VERIFICATION")
    print("="*70)

    # 1. Generate Super Admin Token
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(User).where(User.role == UserRole.SUPER_ADMIN.value))
        sa = res.scalars().first()
        if not sa:
            raise Exception("No Super Admin found in database.")
        token = create_access_token(subject=str(sa.id), tenant_id=str(sa.tenant_id or "00000000-0000-0000-0000-000000000000"), role=sa.role)
        print(f"[OK] Super Admin Authenticated: {sa.email}")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        # STEP 1: Verify Tenants & Companies listing includes tier and tags
        print("\n--- STEP 1: Tenants & Companies API ---")
        res = await client.get(f"{BASE_URL}/superadmin/companies", headers=headers)
        assert res.status_code == 200, f"Failed listing companies: {res.text}"
        companies = res.json()
        print(f"[OK] Fetched {len(companies)} existing tenant organizations.")
        if companies:
            first = companies[0]
            print(f"     Sample Org: {first['name']} | Tier: {first.get('tier')} | Code: {first.get('company_code')}")
            assert "tier" in first, "tier missing in CompanyResponse"
            assert "tags" in first, "tags missing in CompanyResponse"

        # STEP 2: Pre-sales Leads Pipeline (Capture -> Negotiate -> Quoted)
        print("\n--- STEP 2: Leads Pipeline (Calculator Inquiry -> Quoted) ---")
        lead_payload = {
            "company_name": "Apex Pharma Logistics",
            "industry": "Pharmaceuticals & Healthcare",
            "location": "Hyderabad, Telangana",
            "contact_name": "Dr. Rajesh Sharma",
            "email": "rajesh.sharma@apexpharma.test",
            "phone": "+919876543210",
            "estimated_warehouses": "3-5",
            "estimated_skus": "1,000 - 5,000",
            "tier_estimate": "Growth Suite",
            "quoted_amount": 0.0,
            "selected_modules": ["products", "locations", "orders", "ledger", "reports"],
        }
        res = await client.post(f"{BASE_URL}/leads/inquiry", json=lead_payload)
        assert res.status_code in [200, 201], f"Lead creation failed: {res.text}"
        lead = res.json()
        lead_id = lead["id"]
        print(f"[OK] Created lead inquiry ID: {lead_id} for {lead['company_name']}")

        # Update lead status to 'quoted' with agreed setup fee
        res = await client.patch(
            f"{BASE_URL}/superadmin/leads/{lead_id}/status",
            headers=headers,
            json={
                "status": "quoted",
                "quoted_amount": 45000.0,
                "notes": "Agreed on Rs. 45,000 setup fee with cold-chain storage validation.",
            }
        )
        assert res.status_code == 200, f"Lead status update failed: {res.text}"
        updated_lead = res.json()
        assert updated_lead["status"] == "quoted"
        assert float(updated_lead["quoted_amount"]) == 45000.0
        print(f"[OK] Lead status advanced to 'quoted' with Rs. {updated_lead['quoted_amount']} setup fee.")

        # STEP 3: One-Click Lead Conversion -> Provision Company
        print("\n--- STEP 3: Lead Conversion & Company Provisioning ---")
        import random
        rnd = random.randint(1000, 9999)
        prov_payload = {
            "company_name": f"Apex Pharma Logistics {rnd}",
            "company_code": f"APX{rnd}",
            "industry": "Pharmaceuticals & Healthcare",
            "location": "Hyderabad, Telangana",
            "currency_code": "INR",
            "tier": updated_lead["tier_estimate"],
            "tags": [updated_lead["tier_estimate"], "Healthcare", "ColdChain"],
            "lead_id": lead_id,
            "quoted_setup_fee": float(updated_lead["quoted_amount"]),
            "admin_full_name": "Dr. Rajesh Sharma",
            "admin_email": f"admin.apex{rnd}@apexpharma.test",
            "admin_password": "SecurePassword123!",
            "enabled_modules": updated_lead["selected_modules"],
            "send_email": False,
        }
        res = await client.post(f"{BASE_URL}/superadmin/companies", headers=headers, json=prov_payload)
        assert res.status_code == 201, f"Provisioning failed: {res.text}"
        new_company = res.json()
        new_tenant_id = new_company["id"]
        print(f"[OK] Provisioned Company '{new_company['name']}' (ID: {new_tenant_id})")
        print(f"     Tier: {new_company.get('tier')} | Code: {new_company.get('company_code')}")

        # Verify Lead is now marked 'converted' with converted_tenant_id
        res = await client.get(f"{BASE_URL}/superadmin/leads", headers=headers)
        all_leads = res.json()
        matched_lead = next((l for l in all_leads if l["id"] == lead_id), None)
        assert matched_lead is not None
        assert matched_lead["status"] == "converted", f"Lead status is {matched_lead['status']}, expected 'converted'"
        assert matched_lead["converted_tenant_id"] == new_tenant_id, "converted_tenant_id was not linked!"
        print(f"[OK] Lead {lead_id} successfully transitioned to 'converted' linked to {new_tenant_id}.")

        # STEP 4: Billing Management (Setup Fee, Monthly Fee, Cycle Payments)
        print("\n--- STEP 4: Billing Management Integration ---")
        # Fetch tenant billing detail
        res = await client.get(f"{BASE_URL}/billing/tenants/{new_tenant_id}", headers=headers)
        assert res.status_code == 200, f"Tenant billing fetch failed: {res.text}"
        billing_data = res.json()
        billing_prof = billing_data["profile"]
        print(f"[OK] Fetched Tenant Billing Profile:")
        print(f"     Pre-filled Setup Fee: Rs. {billing_prof['setup_fee']} (Status: {billing_prof['setup_fee_status']})")
        assert float(billing_prof["setup_fee"]) == 45000.0, "Quoted setup fee was not auto-carried over!"

        # Update Setup Fee status to paid
        res = await client.put(
            f"{BASE_URL}/billing/tenants/{new_tenant_id}/setup-fee",
            headers=headers,
            json={
                "amount": 45000.0,
                "status": "paid",
                "payment_mode": "manual",
                "payment_reference": "NEFT-SETUP-001"
            }
        )
        assert res.status_code == 200, f"Update setup fee failed: {res.text}"
        print("[OK] Setup fee marked as PAID.")

        # Update Monthly Maintenance Fee (Active MRR)
        res = await client.post(
            f"{BASE_URL}/billing/tenants/{new_tenant_id}/update-fee",
            headers=headers,
            json={
                "new_amount": 7500.0,
                "effective_from": "2026-10-01T00:00:00",
                "reason": "Negotiated Growth Suite enterprise SLA rate"
            }
        )
        assert res.status_code == 200, f"Update monthly fee failed: {res.text}"
        print("[OK] Monthly maintenance fee set to Rs. 7,500 / month with audit trail.")

        # Record a cycle payment
        res = await client.post(
            f"{BASE_URL}/billing/tenants/{new_tenant_id}/payments",
            headers=headers,
            json={
                "cycle_month": "October 2026",
                "amount": 7500.0,
                "payment_mode": "manual",
                "status": "paid",
                "payment_reference": "NEFT88912739182",
                "notes": "October maintenance fee cleared"
            }
        )
        assert res.status_code in [200, 201], f"Record payment failed: {res.text}"
        print("[OK] October 2026 cycle payment of Rs. 7,500 recorded.")

        # Record a Rs. 0 waived cycle
        res = await client.post(
            f"{BASE_URL}/billing/tenants/{new_tenant_id}/payments",
            headers=headers,
            json={
                "cycle_month": "November 2026",
                "amount": 0.0,
                "payment_mode": "manual",
                "status": "waived",
                "payment_reference": "WAIVE-NOV2026",
                "notes": "Promotional holiday waiver month"
            }
        )
        assert res.status_code in [200, 201], f"Record waived payment failed: {res.text}"
        print("[OK] November 2026 Rs. 0 cycle recorded with 'waived' status (continuous record).")

        # Verify Billing Overview
        res = await client.get(f"{BASE_URL}/billing/overview", headers=headers)
        assert res.status_code == 200, f"Billing overview failed: {res.text}"
        overview = res.json()
        print(f"[OK] Dynamic Billing Overview Telemetry:")
        print(f"     Total Revenue Collected: Rs. {overview['total_revenue_collected']}")
        print(f"     Active Monthly MRR: Rs. {overview['active_mrr_sum']}")
        print(f"     Organizations Tracked: {len(overview['organizations'])}")
        assert overview["active_mrr_sum"] >= 7500.0

        # STEP 5: Role Management (Tenant-Scoped RBAC & Guardrails)
        print("\n--- STEP 5: Role Management & Lockout Protection ---")
        res = await client.get(f"{BASE_URL}/role-management/organizations", headers=headers)
        assert res.status_code == 200, f"Role orgs failed: {res.text}"
        role_orgs = res.json()
        assert any(o["id"] == new_tenant_id for o in role_orgs), "Provisioned org missing from Role Management!"
        print(f"[OK] New company listed in Role Management org picker.")

        # Get team for the new company
        res = await client.get(f"{BASE_URL}/role-management/organizations/{new_tenant_id}/team", headers=headers)
        assert res.status_code == 200, f"Team fetch failed: {res.text}"
        team = res.json()
        assert len(team) >= 1, "Expected initial admin in team"
        admin_member = team[0]
        print(f"[OK] Found team operator: {admin_member['full_name']} ({admin_member['email']}) | Role: {admin_member['role']}")

        # Attempt to demote the sole admin without force_last_admin -> Safeguard triggered!
        res = await client.put(
            f"{BASE_URL}/role-management/users/{admin_member['id']}/role",
            headers=headers,
            json={
                "role": "staff",
                "permissions": ["inventory:read"],
                "force_last_admin": False
            }
        )
        assert res.status_code == 200
        guardrail_res = res.json()
        assert guardrail_res.get("requires_safeguard") is True, "Guardrail should have intercepted last admin removal!"
        queued_request_id = guardrail_res.get("request_id")
        print(f"[OK] Guardrail Intercepted: Demoting sole admin generated approval request ID: {queued_request_id}")

        # STEP 6: Security Safeguards (Approval Queue & Compliance Audit Log)
        print("\n--- STEP 6: Security Safeguards (Queue & Audit Log) ---")
        res = await client.get(f"{BASE_URL}/safeguards/queue?status=pending", headers=headers)
        assert res.status_code == 200, f"Queue fetch failed: {res.text}"
        queue_items = res.json()
        assert any(q["id"] == queued_request_id for q in queue_items), "Queued request not found in pending queue!"
        print(f"[OK] Verified request {queued_request_id} is in the Security Safeguards Queue.")

        # Approve the request
        res = await client.post(
            f"{BASE_URL}/safeguards/queue/{queued_request_id}/approve",
            headers=headers
        )
        assert res.status_code == 200, f"Approval execution failed: {res.text}"
        print(f"[OK] Super Admin signed off on request {queued_request_id}.")

        # Fetch Audit Logs and verify end-to-end trail
        res = await client.get(f"{BASE_URL}/safeguards/audit-logs?tenant_id={new_tenant_id}", headers=headers)
        assert res.status_code == 200, f"Audit logs fetch failed: {res.text}"
        org_audit_logs = res.json()
        print(f"[OK] Fetched {len(org_audit_logs)} compliance audit log entries for organization:")
        for log in org_audit_logs[:5]:
            print(f"     [{log['created_at'][:19]}] {log['action_type']} by {log['actor_email']} - {log['description']}")

        assert any(l["action_type"] == "company_provisioned" for l in org_audit_logs), "Missing company_provisioned audit log!"
        assert any("fee" in l["action_type"] or "billing" in l["action_type"] for l in org_audit_logs), "Missing billing audit log!"

    print("\n" + "="*70)
    print("ALL PRODUCTION-GRADE FLOW TESTS PASSED SUCCESSFULLY! (100% GREEN)")
    print("="*70 + "\n")

if __name__ == "__main__":
    asyncio.run(run_end_to_end_verification())

