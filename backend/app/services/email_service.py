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
                with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=20) as server:
                    if smtp_user and smtp_pass:
                        server.login(smtp_user, smtp_pass)
                    server.sendmail(from_email, [recipient], msg.as_string())
            else:
                with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
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
