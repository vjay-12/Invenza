import sys
sys.path.insert(0, r'c:\Users\vijay\Project_26\Invenza\backend')
import asyncio
from app.core.database import AsyncSessionLocal
from app.models.tenant import Tenant
from app.models.invoice import TenantSettings
from app.api.v1.endpoints.invoices import get_tenant_settings, update_tenant_settings
from app.schemas.invoice import TenantSettingsUpdate
from sqlalchemy import select

async def run_tests():
    print("--- Running Legal Settings Regression Tests ---")
    async with AsyncSessionLocal() as db:
        # 1. Test Indian Tenant (e.g. BlueDart Logistics Hub or Kaveri Retail)
        res = await db.execute(select(Tenant).where(Tenant.country_code == 'IN').limit(1))
        in_tenant = res.scalar_one_or_none()
        assert in_tenant is not None, "Indian tenant not found"
        print(f"1. Testing Indian Tenant: {in_tenant.name} ({in_tenant.country_code})")

        in_sett = await get_tenant_settings(tenant_id=in_tenant.id, db=db)
        print(f"   [GET] tax_type: {in_sett.tax_type}, gstin: '{in_sett.gstin}', pan: '{in_sett.pan}', state_code: '{in_sett.state_code}', ifsc: '{in_sett.bank_ifsc_code}'")
        assert in_sett.tax_type == "GST", f"Expected GST, got {in_sett.tax_type}"
        assert in_sett.country_code == "IN", f"Expected IN, got {in_sett.country_code}"

        # 2. Test German Tenant ("SK E-com")
        res = await db.execute(select(Tenant).where(Tenant.name == 'SK E-com'))
        de_tenant = res.scalar_one_or_none()
        assert de_tenant is not None, "German tenant 'SK E-com' not found"
        print(f"2. Testing German Tenant: {de_tenant.name} ({de_tenant.country_code})")

        de_sett = await get_tenant_settings(tenant_id=de_tenant.id, db=db)
        print(f"   [GET] tax_type: {de_sett.tax_type}, gstin/vat_id: '{de_sett.gstin}', pan/steuernummer: '{de_sett.pan}', state: '{de_sett.state}'")
        assert de_sett.tax_type == "VAT", f"Expected VAT, got {de_sett.tax_type}"
        assert de_sett.country_code == "DE", f"Expected DE, got {de_sett.country_code}"
        assert de_sett.pan != "AABCI1234F", "German tenant should NOT have Indian dummy PAN 'AABCI1234F'!"

        # Update German tenant with valid German tax & SEPA bank info
        de_update = TenantSettingsUpdate(
            legal_business_name="SK E-Commerce GmbH",
            vat_id="DE345678901",
            steuernummer="12/345/67890",
            registered_address="Kurfürstendamm 100, 10709 Berlin, Germany",
            account_holder_name="SK E-Commerce GmbH",
            bank_name="Deutsche Bank AG",
            bank_account_number="DE89370400440532013000",
            bank_routing_code="DEUTDEDDFXX",
            bank_branch="Berlin Main Branch",
        )
        de_updated = await update_tenant_settings(payload=de_update, tenant_id=de_tenant.id, db=db)
        print(f"   [PUT] Saved: vat_id: '{de_updated.gstin}', steuernummer: '{de_updated.pan}', iban: '{de_updated.bank_account_number}', bic: '{de_updated.bank_ifsc_code}'")
        assert de_updated.gstin == "DE345678901"
        assert de_updated.pan == "12/345/67890"
        assert de_updated.bank_account_number == "DE89370400440532013000"
        assert de_updated.bank_ifsc_code == "DEUTDEDDFXX"
        print("   -> German tenant legal profile updated and verified successfully!")

        # 3. Test US Tenant ("Pacific Crest Distribution Inc.")
        res = await db.execute(select(Tenant).where(Tenant.name.ilike('%Pacific Crest%')))
        us_tenant = res.scalar_one_or_none()
        assert us_tenant is not None, "US tenant 'Pacific Crest' not found"
        print(f"3. Testing US Tenant: {us_tenant.name} ({us_tenant.country_code})")

        us_sett = await get_tenant_settings(tenant_id=us_tenant.id, db=db)
        print(f"   [GET] tax_type: {us_sett.tax_type}, gstin/permit: '{us_sett.gstin}', pan/ein: '{us_sett.pan}', state: '{us_sett.state}'")
        assert us_sett.tax_type == "SALES_TAX", f"Expected SALES_TAX, got {us_sett.tax_type}"
        assert us_sett.country_code == "US", f"Expected US, got {us_sett.country_code}"
        assert us_sett.pan != "AABCI1234F", "US tenant should NOT have Indian dummy PAN 'AABCI1234F'!"

        # Update US tenant with valid US EIN, Permit #, and ACH routing
        us_update = TenantSettingsUpdate(
            legal_business_name="Pacific Crest Distribution Inc.",
            tax_reg_number="SR AC 12-345678",
            ein="95-1234567",
            registered_address="500 Howard Street, Suite 400, San Francisco, CA 94105",
            account_holder_name="Pacific Crest Distribution Inc.",
            bank_name="JPMorgan Chase",
            bank_account_number="123456789012",
            bank_routing_code="021000021",
            bank_branch="San Francisco Financial District",
        )
        us_updated = await update_tenant_settings(payload=us_update, tenant_id=us_tenant.id, db=db)
        print(f"   [PUT] Saved: permit: '{us_updated.gstin}', ein: '{us_updated.pan}', routing: '{us_updated.bank_ifsc_code}'")
        assert us_updated.gstin == "SR AC 12-345678"
        assert us_updated.pan == "95-1234567"
        assert us_updated.bank_ifsc_code == "021000021"
        print("   -> US tenant legal profile updated and verified successfully!")

    print("\n--- ALL REGRESSION TESTS PASSED! ---")

if __name__ == '__main__':
    asyncio.run(run_tests())
