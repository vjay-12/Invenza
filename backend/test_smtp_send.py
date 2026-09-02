import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

# Load .env
root_env = backend_dir.parent / ".env"
backend_env = backend_dir / ".env"

if root_env.exists():
    load_dotenv(root_env, override=True)
if backend_env.exists():
    load_dotenv(backend_env, override=True)

from app.services.email_service import EmailService

async def main():
    target_email = os.getenv("SMTP_USER", "ofc123kor@gmail.com").strip()
    print(f"=== INVENZA SMTP TEST DISPATCH ===")
    print(f"SMTP Host: {os.getenv('SMTP_HOST')}")
    print(f"SMTP Port: {os.getenv('SMTP_PORT')}")
    print(f"SMTP User: {os.getenv('SMTP_USER')}")
    print(f"Recipient: {target_email}")
    print("-----------------------------------")
    
    # Send sample company admin onboarding email
    print(f"Attempting to send sample company admin welcome email to {target_email}...")
    result = await EmailService.send_company_admin_credentials(
        company_name="Apex Logistics & Distribution",
        industry="Supply Chain & Freight",
        location="Chicago, IL",
        admin_name="Apex Administrator",
        admin_email=target_email,
        temporary_password="ApexSecure2026!Demo",
        enabled_modules=["Products", "Locations", "Orders", "Reports", "Storage"],
        portal_url="http://localhost:5173",
    )
    
    print("\n=== DISPATCH RESULT ===")
    for k, v in result.items():
        print(f"  {k}: {v}")

    if result.get("mode") == "smtp":
        print("\n[SUCCESS] Email was successfully transmitted through Google SMTP server directly to your inbox!")
    else:
        print(f"\n[FALLBACK / FAILED SMTP] Mode: {result.get('mode')}, Error: {result.get('error')}")

if __name__ == "__main__":
    asyncio.run(main())
