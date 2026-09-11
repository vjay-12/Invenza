import os
import smtplib
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
OUTBOX_LOG_PATH = BACKEND_DIR / "email_outbox.log"

def _load_active_env():
    if (ROOT_DIR / ".env").exists():
        load_dotenv(ROOT_DIR / ".env", override=True)
    if (BACKEND_DIR / ".env").exists():
        load_dotenv(BACKEND_DIR / ".env", override=True)

class EmailService:
    @staticmethod
    def _is_smtp_configured() -> bool:
        _load_active_env()
        host = os.getenv("SMTP_HOST", "").strip()
        port = os.getenv("SMTP_PORT", "").strip()
        enabled = os.getenv("EMAILS_ENABLED", "true").strip().lower() in ("true", "1", "yes")
        return bool(host and port and enabled)

    @staticmethod
    def _log_to_outbox(recipient: str, subject: str, body_text: str, body_html: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Logs every dispatched email to an append-only log file for verification and testing.
        """
        try:
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
            entry = [
                f"\n{'='*75}",
                f"INVENZA NOTIFICATION DISPATCH [{timestamp}]",
                f"TO: {recipient}",
                f"SUBJECT: {subject}",
                f"METADATA: {metadata or {}}",
                f"{'-'*75}",
                "CONTENT (PLAIN TEXT):",
                body_text.strip(),
                f"{'='*75}\n",
            ]
            with open(OUTBOX_LOG_PATH, "a", encoding="utf-8") as f:
                f.write("\n".join(entry))
        except Exception as e:
            print(f"[EmailService Outbox Error]: {e}")

    @classmethod
    async def send_email_async(
        cls,
        recipient: str,
        subject: str,
        body_text: str,
        body_html: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Sends an email asynchronously via SMTP if configured, or logs to outbox file if running in local/test mode.
        """
        _load_active_env()
        cls._log_to_outbox(recipient, subject, body_text, body_html, metadata)

        if not cls._is_smtp_configured():
            print(f"[EmailService Local Simulated] Email to <{recipient}> logged to email_outbox.log: '{subject}'")
            return {
                "success": True,
                "mode": "simulated_local",
                "recipient": recipient,
                "subject": subject,
                "message": "Email logged to local outbox (SMTP not configured).",
            }

        # Send via real SMTP server in thread
        def _send_smtp():
            _load_active_env()
            smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
            smtp_port = int(os.getenv("SMTP_PORT", "587"))
            smtp_user = os.getenv("SMTP_USER", "").strip()
            smtp_pass = os.getenv("SMTP_PASSWORD", "").strip()
            from_email = (
                os.getenv("SMTP_FROM")
                or os.getenv("EMAILS_FROM_EMAIL")
                or smtp_user
                or "noreply@invenza.io"
            ).strip()
            from_name = os.getenv("EMAILS_FROM_NAME", "Invenza Enterprise Platform")

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{from_name} <{from_email}>"
            msg["To"] = recipient

            part1 = MIMEText(body_text, "plain", "utf-8")
            part2 = MIMEText(body_html, "html", "utf-8")
            msg.attach(part1)
            msg.attach(part2)

            if smtp_port == 465:
                with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=5) as server:
                    if smtp_user and smtp_pass:
                        server.login(smtp_user, smtp_pass)
                    server.sendmail(from_email, [recipient], msg.as_string())
            else:
                with smtplib.SMTP(smtp_host, smtp_port, timeout=5) as server:
                    server.ehlo()
                    use_tls = os.getenv("SMTP_TLS", "true").lower() in ("true", "1")
                    if use_tls:
                        server.starttls()
                        server.ehlo()
                    if smtp_user and smtp_pass:
                        server.login(smtp_user, smtp_pass)
                    server.sendmail(from_email, [recipient], msg.as_string())

        try:
            await asyncio.to_thread(_send_smtp)
            print(f"[EmailService SMTP Success] Dispatched email to <{recipient}>: '{subject}'")
            return {
                "success": True,
                "mode": "smtp",
                "recipient": recipient,
                "subject": subject,
                "message": "Email sent successfully via SMTP server.",
            }
        except Exception as e:
            print(f"[EmailService SMTP Warning]: Could not reach SMTP server ({e}). Email saved to outbox log.")
            return {
                "success": True,
                "mode": "outbox_fallback",
                "recipient": recipient,
                "subject": subject,
                "error": str(e),
                "message": f"SMTP dispatch failed ({e}). Successfully recorded in local email outbox.",
            }

    @classmethod
    async def send_company_admin_credentials(
        cls,
        company_name: str,
        industry: str,
        location: str,
        admin_name: str,
        admin_email: str,
        temporary_password: str,
        enabled_modules: List[str],
        portal_url: str = "http://localhost:5173",
    ) -> Dict[str, Any]:
        """
        Dispatches welcome email to newly provisioned Company Admin.
        """
        subject = f"Welcome to Invenza - Your {company_name} Admin Account"

        modules_str = ", ".join([m.capitalize() for m in enabled_modules]) if enabled_modules else "All Standard Modules"

        body_text = f"""
Dear {admin_name},

Congratulations! A new enterprise tenant organization has been provisioned for you on the Invenza Inventory Platform by the Super Administrator.

=== YOUR COMPANY DETAILS ===
Company Name: {company_name}
Industry: {industry}
HQ Location: {location}
Enabled Modules: {modules_str}

=== YOUR LOGIN CREDENTIALS ===
Portal URL: {portal_url}
Admin Email: {admin_email}
Temporary Password: {temporary_password}

For security, please log in and change your password upon your first session. Your company has a completely isolated inventory database with zero pre-existing records, allowing you to add your custom warehouses and products.

Best regards,
The Invenza Enterprise Team
        """

        body_html = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0B0F19; color: #F1F5F9; margin: 0; padding: 24px; }}
    .container {{ max-width: 600px; margin: 0 auto; background-color: #1E293B; border-radius: 16px; border: 1px solid #334155; padding: 32px; }}
    .logo {{ display: inline-flex; align-items: center; justify-content: center; width: 44px; height: 44px; background: linear-gradient(135deg, #6366F1, #A855F7); border-radius: 12px; color: #fff; font-size: 22px; font-weight: 900; margin-bottom: 20px; }}
    .title {{ font-size: 22px; font-weight: 700; color: #FFFFFF; margin-bottom: 8px; }}
    .subtitle {{ font-size: 14px; color: #94A3B8; margin-bottom: 24px; line-height: 1.5; }}
    .card {{ background-color: #0F172A; border-radius: 12px; border: 1px solid #334155; padding: 20px; margin-bottom: 20px; }}
    .label {{ font-size: 12px; font-weight: 600; text-transform: uppercase; color: #64748B; letter-spacing: 0.05em; margin-bottom: 4px; }}
    .val {{ font-size: 15px; color: #F8FAFC; font-weight: 600; margin-bottom: 12px; }}
    .val-code {{ font-family: monospace; font-size: 16px; color: #38BDF8; background-color: #0284C71A; padding: 4px 8px; border-radius: 6px; }}
    .tag {{ display: inline-block; background-color: #6366F126; color: #818CF8; border: 1px solid #6366F14D; padding: 3px 8px; border-radius: 6px; font-size: 12px; font-weight: 600; margin: 2px; }}
    .btn {{ display: inline-block; background: linear-gradient(135deg, #6366F1, #4F46E5); color: #FFFFFF !important; text-decoration: none; padding: 12px 28px; border-radius: 8px; font-weight: 700; font-size: 14px; margin-top: 10px; }}
    .footer {{ font-size: 12px; color: #64748B; text-align: center; margin-top: 24px; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="logo">I</div>
    <div class="title">Welcome to Invenza Enterprise</div>
    <div class="subtitle">Your dedicated organization has been provisioned with strict tenant isolation.</div>
    
    <div class="card">
      <div class="label">Company Workspace</div>
      <div class="val">{company_name}</div>
      <div class="label">Assigned Industry</div>
      <div class="val"><span class="tag">{industry}</span></div>
      <div class="label">Headquarters / Location</div>
      <div class="val">{location}</div>
      <div class="label">Enabled Modules</div>
      <div class="val">
        {"".join([f'<span class="tag">{m}</span>' for m in enabled_modules])}
      </div>
    </div>

    <div class="card">
      <div class="label">Portal Web Address</div>
      <div class="val"><a href="{portal_url}" style="color: #60A5FA;">{portal_url}</a></div>
      <div class="label">Admin Email</div>
      <div class="val">{admin_email}</div>
      <div class="label">Temporary Admin Password</div>
      <div class="val"><span class="val-code">{temporary_password}</span></div>
    </div>

    <div style="text-align: center; margin: 24px 0;">
      <a href="{portal_url}" class="btn">Log In to Invenza Workspace &rarr;</a>
    </div>

    <div class="footer">
      Sent by Invenza Super Admin Engine &bull; This email contains sensitive credentials. Please do not forward.
    </div>
  </div>
</body>
</html>
        """

        return await cls.send_email_async(
            recipient=admin_email,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            metadata={"company_name": company_name, "type": "company_admin_onboarding"},
        )

    @classmethod
    async def send_staff_user_credentials(
        cls,
        company_name: str,
        user_name: str,
        user_email: str,
        temporary_password: str,
        role: str,
        permissions: List[str],
        portal_url: str = "http://localhost:5173",
    ) -> Dict[str, Any]:
        """
        Dispatches welcome email to newly created Company Staff user.
        """
        subject = f"Welcome to {company_name} on Invenza - Your Staff Credentials"

        perms_str = ", ".join(permissions) if permissions else "Standard Access"

        body_text = f"""
Dear {user_name},

You have been granted access to the {company_name} workspace on Invenza.

=== YOUR ACCOUNT DETAILS ===
Company: {company_name}
Assigned Role: {role.upper()}
Permissions: {perms_str}

=== LOGIN CREDENTIALS ===
Portal URL: {portal_url}
Email: {user_email}
Temporary Password: {temporary_password}

Please log in and update your password.

Best regards,
{company_name} Administration via Invenza
        """

        body_html = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0B0F19; color: #F1F5F9; margin: 0; padding: 24px; }}
    .container {{ max-width: 600px; margin: 0 auto; background-color: #1E293B; border-radius: 16px; border: 1px solid #334155; padding: 32px; }}
    .logo {{ display: inline-flex; align-items: center; justify-content: center; width: 44px; height: 44px; background: linear-gradient(135deg, #10B981, #06B6D4); border-radius: 12px; color: #fff; font-size: 22px; font-weight: 900; margin-bottom: 20px; }}
    .title {{ font-size: 22px; font-weight: 700; color: #FFFFFF; margin-bottom: 8px; }}
    .subtitle {{ font-size: 14px; color: #94A3B8; margin-bottom: 24px; line-height: 1.5; }}
    .card {{ background-color: #0F172A; border-radius: 12px; border: 1px solid #334155; padding: 20px; margin-bottom: 20px; }}
    .label {{ font-size: 12px; font-weight: 600; text-transform: uppercase; color: #64748B; letter-spacing: 0.05em; margin-bottom: 4px; }}
    .val {{ font-size: 15px; color: #F8FAFC; font-weight: 600; margin-bottom: 12px; }}
    .val-code {{ font-family: monospace; font-size: 16px; color: #38BDF8; background-color: #0284C71A; padding: 4px 8px; border-radius: 6px; }}
    .tag {{ display: inline-block; background-color: #10B98126; color: #34D399; border: 1px solid #10B9814D; padding: 3px 8px; border-radius: 6px; font-size: 12px; font-weight: 600; margin: 2px; }}
    .btn {{ display: inline-block; background: linear-gradient(135deg, #10B981, #059669); color: #FFFFFF !important; text-decoration: none; padding: 12px 28px; border-radius: 8px; font-weight: 700; font-size: 14px; margin-top: 10px; }}
    .footer {{ font-size: 12px; color: #64748B; text-align: center; margin-top: 24px; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="logo">I</div>
    <div class="title">Your Invenza Account is Ready</div>
    <div class="subtitle">You have been assigned access to the <strong>{company_name}</strong> inventory system.</div>
    
    <div class="card">
      <div class="label">Organization</div>
      <div class="val">{company_name}</div>
      <div class="label">Role</div>
      <div class="val"><span class="tag">{role.upper()}</span></div>
      <div class="label">Granted Permissions</div>
      <div class="val">
        {"".join([f'<span class="tag">{p}</span>' for p in permissions])}
      </div>
    </div>

    <div class="card">
      <div class="label">Portal Address</div>
      <div class="val"><a href="{portal_url}" style="color: #34D399;">{portal_url}</a></div>
      <div class="label">User Email</div>
      <div class="val">{user_email}</div>
      <div class="label">Password</div>
      <div class="val"><span class="val-code">{temporary_password}</span></div>
    </div>

    <div style="text-align: center; margin: 24px 0;">
      <a href="{portal_url}" class="btn">Log In to Workspace &rarr;</a>
    </div>

    <div class="footer">
      Sent by {company_name} on Invenza IMS.
    </div>
  </div>
</body>
</html>
        """

        return await cls.send_email_async(
            recipient=user_email,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            metadata={"company_name": company_name, "type": "staff_user_onboarding"},
        )

    @classmethod
    async def send_password_reset_otp(
        cls,
        user_name: str,
        user_email: str,
        otp: str,
        expires_in_minutes: int = 10,
    ) -> Dict[str, Any]:
        """
        Dispatches high-security One-Time Password (OTP) for account password reset.
        """
        subject = f"{otp} is your Invenza Account Password Reset Code"

        body_text = f"""
Hello {user_name},

We received a request to reset the password for your Invenza Enterprise account ({user_email}).

YOUR VERIFICATION CODE:
{otp}

This code will expire in {expires_in_minutes} minutes.

If you did not initiate this request, please disregard this message or contact your organization's system administrator immediately.

Best regards,
Invenza Security Operations
        """

        body_html = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0C1017; color: #F1F5F9; margin: 0; padding: 24px; }}
    .container {{ max-width: 520px; margin: 0 auto; background-color: #131924; border-radius: 12px; border: 1px solid #1E2636; padding: 32px; }}
    .logo {{ display: inline-flex; align-items: center; justify-content: center; width: 40px; height: 40px; background-color: #0E7490; border-radius: 8px; color: #fff; font-size: 20px; font-weight: 800; margin-bottom: 20px; }}
    .title {{ font-size: 20px; font-weight: 700; color: #FFFFFF; margin-bottom: 8px; }}
    .subtitle {{ font-size: 13px; color: #94A3B8; margin-bottom: 24px; line-height: 1.5; }}
    .otp-box {{ background-color: #0C1017; border-radius: 8px; border: 1px solid #1E2636; padding: 24px; text-align: center; margin-bottom: 20px; }}
    .otp-code {{ font-family: 'IBM Plex Mono', monospace, Courier; font-size: 36px; font-weight: 700; color: #2DD4BF; letter-spacing: 8px; }}
    .expiry {{ font-size: 12px; color: #64748B; margin-top: 8px; }}
    .warning {{ font-size: 12px; color: #94A3B8; line-height: 1.5; border-top: 1px solid #1E2636; padding-top: 16px; margin-top: 24px; }}
    .footer {{ font-size: 11px; color: #475569; text-align: center; margin-top: 24px; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="logo">I</div>
    <div class="title">Password Reset Verification</div>
    <div class="subtitle">Hello <strong>{user_name}</strong>, enter the 6-digit verification code below to reset your Invenza credentials:</div>
    
    <div class="otp-box">
      <div class="otp-code">{otp}</div>
      <div class="expiry">Valid for {expires_in_minutes} minutes</div>
    </div>

    <div class="warning">
      If you did not request a password reset, you can safely ignore this email. Your password will remain unchanged.
    </div>

    <div class="footer">
      &copy; 2026 Invenza Enterprise Platform &bull; Automated Security Dispatch
    </div>
  </div>
</body>
</html>
        """

        return await cls.send_email_async(
            recipient=user_email,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            metadata={"email": user_email, "type": "password_reset_otp"},
        )

    @classmethod
    async def send_lead_inquiry_notification(
        cls,
        lead_data: Dict[str, Any],
        superadmin_email: str = "superadmin@invenza.internal",
    ) -> Dict[str, Any]:
        """
        Dispatches executive lead & quotation inquiry notification to Super Admin.
        Contains company information, contact details, operational scale, and requested modules.
        """
        company_name = lead_data.get("company_name", "Prospective Enterprise")
        contact_name = lead_data.get("contact_name", "Inquirer")
        email = lead_data.get("email", "N/A")
        phone = lead_data.get("phone", "N/A")
        whatsapp = lead_data.get("whatsapp_number", phone)
        industry = lead_data.get("industry", "General Merchandise")
        location = lead_data.get("location", "N/A")
        warehouses = lead_data.get("estimated_warehouses", "1-2")
        skus = lead_data.get("estimated_skus", "< 500")
        orders = lead_data.get("estimated_monthly_orders", "< 1,000")
        tier = lead_data.get("tier_estimate", "Growth Suite")
        modules = lead_data.get("selected_modules", [])
        modules_str = ", ".join([str(m).capitalize() for m in modules]) if modules else "All Standard Modules"
        notes = lead_data.get("notes") or "None provided."

        subject = f"[New Lead & Quotation] {company_name} - {tier} Access Request"

        body_text = f"""
NEW PROSPECTIVE CUSTOMER QUOTATION INQUIRY
===========================================
Timestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
Tier Estimate: {tier}

COMPANY PROFILE
----------------
Company: {company_name}
Industry: {industry}
Operating City/Location: {location}

CONTACT INFORMATION
-------------------
Contact Person: {contact_name}
Email Address: {email}
Phone Number: {phone}
WhatsApp: {whatsapp}

OPERATIONAL SCALE & SCOPE
-------------------------
Warehouses / Hubs: {warehouses}
Estimated SKUs: {skus}
Monthly Order Volume: {orders}
Modules Selected: {modules_str}

SPECIAL NOTES / REQUIREMENTS
----------------------------
{notes}

NEXT STEPS FOR SUPER ADMIN:
1. Review quotation parameters above.
2. Reach out to the prospective client offline via WhatsApp ({whatsapp}) or phone to negotiate terms.
3. Open the Invenza Super Admin Console -> 'Prospective Leads' tab and click 'Provision from Lead' to automatically pre-fill and launch the new tenant.
        """

        body_html = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0C1017; color: #F1F5F9; margin: 0; padding: 24px; }}
    .container {{ max-width: 600px; margin: 0 auto; background-color: #131924; border-radius: 12px; border: 1px solid #1E2636; padding: 32px; }}
    .badge {{ display: inline-block; padding: 4px 10px; border-radius: 6px; background-color: rgba(13, 148, 136, 0.15); border: 1px solid rgba(13, 148, 136, 0.3); color: #2DD4BF; font-family: monospace; font-size: 11px; font-weight: 700; text-transform: uppercase; margin-bottom: 12px; }}
    .title {{ font-size: 22px; font-weight: 700; color: #FFFFFF; margin-bottom: 8px; }}
    .subtitle {{ font-size: 13px; color: #94A3B8; margin-bottom: 24px; line-height: 1.5; }}
    .grid-table {{ width: 100%; border-collapse: collapse; margin-bottom: 24px; font-size: 13px; }}
    .grid-table td {{ padding: 10px 12px; border-bottom: 1px solid #1E2636; }}
    .grid-table td.label {{ width: 35%; color: #64748B; font-weight: 600; text-transform: uppercase; font-size: 11px; letter-spacing: 0.5px; }}
    .grid-table td.val {{ color: #F1F5F9; font-weight: 500; }}
    .pill {{ display: inline-block; padding: 2px 8px; border-radius: 4px; background-color: #1E2636; font-size: 12px; font-family: monospace; color: #38BDF8; }}
    .notes-box {{ background-color: #0C1017; border-radius: 8px; border: 1px solid #1E2636; padding: 14px; font-size: 12px; color: #CBD5E1; margin-bottom: 24px; }}
    .action-box {{ background-color: rgba(79, 70, 229, 0.1); border: 1px solid rgba(79, 70, 229, 0.25); border-radius: 8px; padding: 16px; font-size: 12px; color: #C7D2FE; line-height: 1.5; }}
    .footer {{ font-size: 11px; color: #475569; text-align: center; margin-top: 24px; }}
  </style>
</head>
<body>
  <div class="container">
    <span class="badge">Invenza Inbound Lead Notification</span>
    <div class="title">{company_name}</div>
    <div class="subtitle">A prospective customer has requested an access quotation for the <strong>{tier}</strong> platform tier.</div>

    <table class="grid-table">
      <tr>
        <td class="label">Contact Person</td>
        <td class="val"><strong>{contact_name}</strong></td>
      </tr>
      <tr>
        <td class="label">Email Address</td>
        <td class="val"><a href="mailto:{email}" style="color: #2DD4BF; text-decoration: none;">{email}</a></td>
      </tr>
      <tr>
        <td class="label">Phone / WhatsApp</td>
        <td class="val"><a href="https://wa.me/{whatsapp}" style="color: #38BDF8; text-decoration: none;">{whatsapp}</a></td>
      </tr>
      <tr>
        <td class="label">Industry Domain</td>
        <td class="val">{industry}</td>
      </tr>
      <tr>
        <td class="label">Operating Location</td>
        <td class="val">{location}</td>
      </tr>
      <tr>
        <td class="label">Warehouses / Hubs</td>
        <td class="val"><span class="pill">{warehouses}</span></td>
      </tr>
      <tr>
        <td class="label">Estimated SKUs</td>
        <td class="val"><span class="pill">{skus}</span></td>
      </tr>
      <tr>
        <td class="label">Monthly Order Volume</td>
        <td class="val"><span class="pill">{orders}</span></td>
      </tr>
      <tr>
        <td class="label">Modules Requested</td>
        <td class="val" style="color: #94A3B8; font-size: 12px;">{modules_str}</td>
      </tr>
    </table>

    <div style="font-size: 12px; font-weight: 600; color: #94A3B8; margin-bottom: 6px; text-transform: uppercase;">Customer Notes:</div>
    <div class="notes-box">{notes}</div>

    <div class="action-box">
      <strong>Next Steps:</strong> Connect with <strong>{contact_name}</strong> on WhatsApp or phone to finalize commercial terms. Once confirmed, visit the Super Admin Console and click <strong>'Provision from Lead'</strong> to auto-fill the tenant provisioning form.
    </div>

    <div class="footer">
      &copy; 2026 Invenza Enterprise Platform &bull; Inbound Lead Automation
    </div>
  </div>
</body>
</html>
        """

        _load_active_env()
        admin_recipient = os.getenv("SUPERADMIN_EMAIL", superadmin_email).strip() or superadmin_email

        return await cls.send_email_async(
            recipient=admin_recipient,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            metadata={"company": company_name, "email": email, "type": "lead_quotation_inquiry"},
        )

