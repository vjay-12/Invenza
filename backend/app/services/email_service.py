import os
import smtplib
import asyncio
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
OUTBOX_LOG_PATH = BACKEND_DIR / "email_outbox.log"
STATIC_DIR = BACKEND_DIR / "app" / "static"
FRONTEND_PUBLIC_DIR = ROOT_DIR / "frontend" / "public"

def _load_active_env():
    if (ROOT_DIR / ".env").exists():
        load_dotenv(ROOT_DIR / ".env", override=True)
    if (BACKEND_DIR / ".env").exists():
        load_dotenv(BACKEND_DIR / ".env", override=True)


class EmailService:
    """
    Official Enterprise Transactional Email Engine for Invenza.
    Implements unified layout architecture, dual-theme support (Dark Primary + Adaptive Light),
    inline CID branding assets, and formal enterprise business correspondence standards.
    """

    @staticmethod
    def _is_smtp_configured() -> bool:
        _load_active_env()
        host = os.getenv("SMTP_HOST", "").strip()
        port = os.getenv("SMTP_PORT", "").strip()
        enabled = os.getenv("EMAILS_ENABLED", "true").strip().lower() in ("true", "1", "yes")
        return bool(host and port and enabled)

    @classmethod
    def _get_logo_bytes(cls, filename: str) -> Optional[bytes]:
        """Loads brand logo bytes from static asset or public directories."""
        candidates = [
            STATIC_DIR / filename,
            FRONTEND_PUBLIC_DIR / filename,
            ROOT_DIR / "frontend" / "public" / filename,
        ]
        for path in candidates:
            if path.exists():
                try:
                    with open(path, "rb") as f:
                        return f.read()
                except Exception:
                    pass
        return None

    @classmethod
    def _get_logo_base64(cls, filename: str) -> str:
        """Returns base64 data URI for previewing HTML in standard web browsers."""
        b = cls._get_logo_bytes(filename)
        if b:
            return f"data:image/png;base64,{base64.b64encode(b).decode('ascii')}"
        return ""

    @classmethod
    def _log_to_outbox(
        cls,
        recipient: str,
        subject: str,
        body_text: str,
        body_html: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Logs every dispatched email to an append-only log file for auditing,
        and generates a standalone browser preview in scratch/latest_email_preview.html.
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

            scratch_dir = BACKEND_DIR / "scratch"
            scratch_dir.mkdir(exist_ok=True)
            preview_html = body_html
            if "cid:invenza_logo_dark" in preview_html:
                dark_b64 = cls._get_logo_base64("invenza-logo-dark.png")
                if dark_b64:
                    preview_html = preview_html.replace("cid:invenza_logo_dark", dark_b64)
            if "cid:invenza_logo_light" in preview_html:
                light_b64 = cls._get_logo_base64("invenza-logo-light.png")
                if light_b64:
                    preview_html = preview_html.replace("cid:invenza_logo_light", light_b64)

            with open(scratch_dir / "latest_email_preview.html", "w", encoding="utf-8") as f:
                f.write(preview_html)
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

        # Send via real SMTP server in worker thread
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

            msg = MIMEMultipart("related")
            msg["Subject"] = subject
            msg["From"] = f"{from_name} <{from_email}>"
            msg["To"] = recipient

            alt_part = MIMEMultipart("alternative")
            part1 = MIMEText(body_text, "plain", "utf-8")
            part2 = MIMEText(body_html, "html", "utf-8")
            alt_part.attach(part1)
            alt_part.attach(part2)
            msg.attach(alt_part)

            # Attach inline images if referenced in HTML body
            if "cid:invenza_logo_dark" in body_html:
                dark_bytes = cls._get_logo_bytes("invenza-logo-dark.png")
                if dark_bytes:
                    img_dark = MIMEImage(dark_bytes, _subtype="png")
                    img_dark.add_header("Content-ID", "<invenza_logo_dark>")
                    img_dark.add_header("Content-Disposition", "inline", filename="invenza-logo-dark.png")
                    msg.attach(img_dark)

            if "cid:invenza_logo_light" in body_html:
                light_bytes = cls._get_logo_bytes("invenza-logo-light.png")
                if light_bytes:
                    img_light = MIMEImage(light_bytes, _subtype="png")
                    img_light.add_header("Content-ID", "<invenza_logo_light>")
                    img_light.add_header("Content-Disposition", "inline", filename="invenza-logo-light.png")
                    msg.attach(img_light)

            try:
                if smtp_port == 465:
                    with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10) as server:
                        if smtp_user and smtp_pass:
                            server.login(smtp_user, smtp_pass)
                        server.send_message(msg)
                else:
                    with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
                        server.ehlo()
                        server.starttls()
                        server.ehlo()
                        if smtp_user and smtp_pass:
                            server.login(smtp_user, smtp_pass)
                        server.send_message(msg)
            except Exception as ex:
                raise ex

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, _send_smtp)
            print(f"[EmailService SMTP Success] Dispatched email to <{recipient}>: '{subject}'")
            return {
                "success": True,
                "mode": "smtp",
                "recipient": recipient,
                "subject": subject,
                "message": f"Successfully dispatched to {recipient} via SMTP server.",
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

    # ═════════════════════════════════════════════════════════════════════════════
    # UNIFIED DESIGN SYSTEM & MASTER LAYOUT RENDERER
    # ═════════════════════════════════════════════════════════════════════════════

    @classmethod
    def _render_master_layout(
        cls,
        subject: str,
        preheader: str,
        badge_text: str,
        badge_type: str,
        title: str,
        subtitle: str,
        salutation: str,
        body_intro_html: str,
        content_cards_html: str,
        cta_text: Optional[str] = None,
        cta_url: Optional[str] = None,
        cta_color: str = "teal",
        signoff_team: str = "Invenza Platform Operations Team",
    ) -> str:
        """
        Master layout engine providing 100% visual consistency across all platform emails.
        Supports true dark-theme default and adaptive light mode via media queries and inline styles.
        """
        badge_styles = {
            "teal": {
                "dark_bg": "#0E74901F", "dark_text": "#22D3EE", "dark_border": "#0891B240",
                "light_bg": "#E0F2FE", "light_text": "#0369A1", "light_border": "#BAE6FD"
            },
            "indigo": {
                "dark_bg": "#4F46E51F", "dark_text": "#818CF8", "dark_border": "#6366F140",
                "light_bg": "#EEF2FF", "light_text": "#4338CA", "light_border": "#C7D2FE"
            },
            "emerald": {
                "dark_bg": "#0596691F", "dark_text": "#34D399", "dark_border": "#10B98140",
                "light_bg": "#ECFDF5", "light_text": "#047857", "light_border": "#A7F3D0"
            },
            "amber": {
                "dark_bg": "#D977061F", "dark_text": "#FBBF24", "dark_border": "#F59E0B40",
                "light_bg": "#FFFBEB", "light_text": "#B45309", "light_border": "#FDE68A"
            },
            "crimson": {
                "dark_bg": "#E11D481F", "dark_text": "#FB7185", "dark_border": "#F43F5E40",
                "light_bg": "#FFF1F2", "light_text": "#BE123C", "light_border": "#FECDD3"
            },
        }
        b = badge_styles.get(badge_type, badge_styles["teal"])

        btn_bg = "#0284C7" if cta_color == "teal" else ("#E11D48" if cta_color == "crimson" else "#059669")
        btn_hover = "#0369A1" if cta_color == "teal" else ("#BE123C" if cta_color == "crimson" else "#047857")

        cta_button_html = ""
        if cta_text and cta_url:
            cta_button_html = f"""
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin: 28px 0 12px 0;">
              <tr>
                <td align="center">
                  <!--[if mso]>
                  <v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" xmlns:w="urn:schemas-microsoft-com:office:word" href="{cta_url}" style="height:46px;v-text-anchor:middle;width:280px;" arcsize="18%" stroke="f" fillcolor="{btn_bg}">
                    <w:anchorlock/>
                    <center style="color:#ffffff;font-family:sans-serif;font-size:14px;font-weight:bold;">{cta_text}</center>
                  </v:roundrect>
                  <![endif]-->
                  <a href="{cta_url}" target="_blank" class="cta-button" style="display: inline-block; background-color: {btn_bg}; background-image: linear-gradient(135deg, {btn_bg}, {btn_hover}); color: #FFFFFF; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 14px; font-weight: 600; line-height: 46px; text-align: center; text-decoration: none; padding: 0 32px; border-radius: 8px; box-shadow: 0 4px 14px rgba(2, 132, 199, 0.35); mso-hide: all;">
                    {cta_text}
                  </a>
                </td>
              </tr>
            </table>
            """

        return f"""<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="color-scheme" content="light dark">
  <meta name="supported-color-schemes" content="light dark">
  <title>{subject}</title>
  <style>
    :root {{
      color-scheme: light dark;
      supported-color-schemes: light dark;
    }}
    body, table, td, div, p, a {{
      -webkit-font-smoothing: antialiased;
      text-size-adjust: 100%;
    }}
    body {{
      margin: 0 !important;
      padding: 0 !important;
      width: 100% !important;
      background-color: #090D16;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }}
    img {{
      border: 0;
      line-height: 100%;
      outline: none;
      text-decoration: none;
      vertical-align: middle;
    }}

    /* ADAPTIVE LIGHT THEME FALLBACK */
    @media (prefers-color-scheme: light) {{
      body, .email-canvas {{
        background-color: #F1F5F9 !important;
      }}
      .email-container {{
        background-color: #FFFFFF !important;
        border-color: #E2E8F0 !important;
        box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08) !important;
      }}
      .header-title {{
        color: #0F172A !important;
      }}
      .header-subtitle {{
        color: #64748B !important;
      }}
      .body-text, .salutation {{
        color: #334155 !important;
      }}
      .content-card {{
        background-color: #F8FAFC !important;
        border-color: #E2E8F0 !important;
      }}
      .card-heading {{
        color: #0F172A !important;
      }}
      .meta-label {{
        color: #64748B !important;
      }}
      .meta-value {{
        color: #0F172A !important;
      }}
      .cred-box {{
        background-color: #F1F5F9 !important;
        border-color: #CBD5E1 !important;
        color: #0369A1 !important;
      }}
      .advisory-box {{
        background-color: #F8FAFC !important;
        border-color: #E2E8F0 !important;
      }}
      .signoff-name {{
        color: #0F172A !important;
      }}
      .signoff-team {{
        color: #64748B !important;
      }}
      .footer-border {{
        border-color: #E2E8F0 !important;
      }}
      .footer-heading {{
        color: #475569 !important;
      }}
      .footer-text, .footer-disclaimer {{
        color: #94A3B8 !important;
      }}
      .footer-link {{
        color: #0284C7 !important;
      }}
      .badge-span {{
        background-color: {b['light_bg']} !important;
        color: {b['light_text']} !important;
        border-color: {b['light_border']} !important;
      }}
      .dark-logo {{
        display: none !important;
        max-height: 0px !important;
        mso-hide: all !important;
      }}
      .light-logo {{
        display: block !important;
        max-height: 38px !important;
      }}
    }}
  </style>
</head>
<body style="margin: 0; padding: 0; background-color: #090D16;" class="email-canvas">

  <!-- INBOX PREHEADER TEXT -->
  <div style="display: none; font-size: 1px; color: #090D16; line-height: 1px; max-height: 0px; max-width: 0px; opacity: 0; overflow: hidden; mso-hide: all;">
    {preheader} &zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;
  </div>

  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #090D16; width: 100%;" class="email-canvas">
    <tr>
      <td align="center" style="padding: 40px 16px 48px 16px;">
        
        <!-- MAIN 600PX CONTAINER -->
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width: 600px; width: 100%; background-color: #0F172A; border: 1px solid #1E293B; border-radius: 16px; overflow: hidden; box-shadow: 0 16px 40px rgba(0, 0, 0, 0.45);" class="email-container">
          
          <!-- TOP BRANDING HEADER -->
          <tr>
            <td style="padding: 36px 40px 24px 40px; text-align: left;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <!-- BRAND LOGO -->
                  <td align="left" style="vertical-align: middle;">
                    <!-- Dark Logo (Default) -->
                    <img src="cid:invenza_logo_dark" alt="Invenza" width="148" height="36" class="dark-logo" style="display: block; width: 148px; height: auto; border: 0;" />
                    <!-- Light Logo (Hidden by default, shown via prefers-color-scheme) -->
                    <img src="cid:invenza_logo_light" alt="Invenza" width="148" height="36" class="light-logo" style="display: none; max-height: 0px; width: 148px; height: auto; border: 0; mso-hide: all;" />
                  </td>
                  <!-- STATUS BADGE -->
                  <td align="right" style="vertical-align: middle;">
                    <span class="badge-span" style="display: inline-block; background-color: {b['dark_bg']}; color: {b['dark_text']}; border: 1px solid {b['dark_border']}; font-size: 10px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; padding: 5px 12px; border-radius: 20px;">
                      {badge_text}
                    </span>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- HERO TITLE & SUBTITLE -->
          <tr>
            <td style="padding: 0 40px 24px 40px;">
              <h1 class="header-title" style="margin: 0 0 6px 0; font-size: 22px; font-weight: 700; line-height: 28px; color: #FFFFFF; letter-spacing: -0.01em;">
                {title}
              </h1>
              <p class="header-subtitle" style="margin: 0; font-size: 13px; line-height: 18px; color: #94A3B8;">
                {subtitle}
              </p>
            </td>
          </tr>

          <!-- BODY INTRO / SALUTATION -->
          <tr>
            <td style="padding: 0 40px 20px 40px;">
              <p class="salutation" style="margin: 0 0 12px 0; font-size: 14px; font-weight: 600; line-height: 20px; color: #F8FAFC;">
                {salutation}
              </p>
              <div class="body-text" style="font-size: 13px; line-height: 22px; color: #94A3B8;">
                {body_intro_html}
              </div>
            </td>
          </tr>

          <!-- STRUCTURED CONTENT SECTION -->
          <tr>
            <td style="padding: 0 40px 10px 40px;">
              {content_cards_html}
              {cta_button_html}
            </td>
          </tr>

          <!-- FORMAL SIGNOFF -->
          <tr>
            <td style="padding: 16px 40px 28px 40px;">
              <p class="signoff-team" style="margin: 0; font-size: 13px; line-height: 20px; color: #94A3B8;">
                Sincerely,<br>
                <strong class="signoff-name" style="color: #F8FAFC; font-weight: 600;">{signoff_team}</strong><br>
                <span style="font-size: 12px; color: #64748B;">Invenza Enterprise Inventory Platform</span>
              </p>
            </td>
          </tr>

          <!-- COMPLIANCE & LEGAL FOOTER -->
          <tr>
            <td style="padding: 24px 40px 32px 40px; background-color: #0A0F1D; border-top: 1px solid #1E293B;" class="footer-border">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td align="center" style="font-size: 11px; line-height: 17px; color: #64748B;" class="footer-text">
                    <p class="footer-heading" style="margin: 0 0 4px 0; font-weight: 600; color: #94A3B8;">
                      Invenza Enterprise Platform · Operated by Hapkonic Technologies Private Limited
                    </p>
                    <p style="margin: 0 0 6px 0;">
                      Registered Office: Bengaluru, Karnataka - 560103, India &nbsp;|&nbsp; GSTIN: 29ABCDE1234F1Z5
                    </p>
                    <p style="margin: 0 0 10px 0;">
                      Commercial Desk: <a href="mailto:support@hapkonic.com" style="color: #38BDF8; text-decoration: none;" class="footer-link">support@hapkonic.com</a> &nbsp;|&nbsp; Priority Phone: <a href="tel:+918825904050" style="color: #38BDF8; text-decoration: none;" class="footer-link">+91 8825904050</a>
                    </p>
                    <p class="footer-disclaimer" style="margin: 0; font-size: 10px; line-height: 15px; color: #475569; max-width: 500px;">
                      CONFIDENTIALITY NOTICE: This transmission is intended solely for the authorized business entity addressed above and may contain privileged operational information. If you have received this communication in error, please notify <a href="mailto:security@hapkonic.com" style="color: #64748B; text-decoration: underline;">security@hapkonic.com</a> and permanently purge this message.
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>

</body>
</html>"""

    @classmethod
    def _render_card(cls, title: str, rows: List[Tuple[str, str]], icon_symbol: str = "◆") -> str:
        """Renders a structured key-value specification card."""
        rows_html = ""
        for i, (label, val) in enumerate(rows):
            border_css = "border-bottom: 1px solid #223046;" if i < len(rows) - 1 else ""
            rows_html += f"""
            <tr>
              <td class="meta-label" style="padding: 10px 14px; font-size: 11px; font-weight: 600; color: #64748B; text-transform: uppercase; letter-spacing: 0.06em; width: 40%; vertical-align: top; {border_css}">
                {label}
              </td>
              <td class="meta-value" style="padding: 10px 14px; font-size: 13px; font-weight: 600; color: #F8FAFC; width: 60%; vertical-align: top; {border_css}">
                {val}
              </td>
            </tr>
            """
        return f"""
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" class="content-card" style="background-color: #162032; border: 1px solid #223046; border-radius: 10px; margin-bottom: 16px; overflow: hidden;">
          <tr>
            <td colspan="2" class="card-heading" style="padding: 12px 14px; font-size: 12px; font-weight: 700; color: #FFFFFF; text-transform: uppercase; letter-spacing: 0.06em; border-bottom: 1px solid #223046; background-color: rgba(255, 255, 255, 0.02);">
              <span style="color: #0284C7; margin-right: 6px;">{icon_symbol}</span> {title}
            </td>
          </tr>
          {rows_html}
        </table>
        """

    @classmethod
    def _render_credential_box(cls, label: str, value: str, subnote: Optional[str] = None) -> str:
        """Renders a secure monospace credentials or OTP box."""
        subnote_html = f'<p style="margin: 6px 0 0 0; font-size: 11px; color: #64748B;">{subnote}</p>' if subnote else ""
        return f"""
        <div class="cred-box" style="margin: 16px 0; padding: 16px; background-color: #0B1322; border: 1px solid #1E293B; border-radius: 8px; text-align: center;">
          <div style="font-size: 10px; font-weight: 700; color: #64748B; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 6px;">
            {label}
          </div>
          <div style="font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace; font-size: 20px; font-weight: 700; color: #38BDF8; letter-spacing: 0.12em; user-select: all;">
            {value}
          </div>
          {subnote_html}
        </div>
        """

    @classmethod
    def _render_advisory(cls, text: str, severity: str = "info") -> str:
        """Renders a formal operational advisory box."""
        colors = {
            "info": {"bg": "rgba(14, 116, 144, 0.08)", "border": "#0891B240", "text": "#38BDF8", "icon": "ℹ"},
            "warning": {"bg": "rgba(217, 119, 6, 0.08)", "border": "#F59E0B40", "text": "#FBBF24", "icon": "⚠"},
            "danger": {"bg": "rgba(225, 29, 72, 0.08)", "border": "#F43F5E40", "text": "#FB7185", "icon": "🛑"},
        }
        c = colors.get(severity, colors["info"])
        return f"""
        <div class="advisory-box" style="margin: 14px 0 18px 0; padding: 12px 14px; background-color: {c['bg']}; border-left: 3px solid {c['border']}; border-radius: 4px; font-size: 12px; line-height: 18px; color: #94A3B8;">
          <strong style="color: {c['text']}; margin-right: 4px;">{c['icon']} NOTICE:</strong> {text}
        </div>
        """

    # ═════════════════════════════════════════════════════════════════════════════
    # 1. ORG ONBOARDING: COMPANY ADMIN CREDENTIAL DISPATCH
    # ═════════════════════════════════════════════════════════════════════════════

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
        company_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Dispatches formal enterprise onboarding notice and credentials to the Primary Organization Administrator."""
        subject = f"Official Notice: Invenza Enterprise Organization Provisioned - {company_name}"
        preheader = f"Your enterprise tenant and primary administrative credentials for {company_name} are ready."

        modules_str = ", ".join([m.capitalize() for m in enabled_modules]) if enabled_modules else "All Standard Modules"

        body_text = f"""
OFFICIAL NOTIFICATION: INVENZA ENTERPRISE TENANT PROVISIONED
============================================================
Dear {admin_name},

This communication confirms that an isolated enterprise tenant organization has been formally provisioned for {company_name} on the Invenza Inventory Management Platform.

ORGANIZATION PROFILE:
- Entity Name: {company_name}
- Company Code: {company_code or 'Assigned'}
- Industry Sector: {industry}
- Registered Location: {location}
- Active Modules: {modules_str}

ADMINISTRATIVE ACCESS CREDENTIALS:
- Portal URL: {portal_url}
- Administrator Email: {admin_email}
- Initial Temporary Password: {temporary_password}

SECURITY ADVISORY:
For compliance and security standards, this initial password must be rotated immediately upon your initial login.

Sincerely,
Invenza Platform Operations Team
Operated by Hapkonic Technologies Private Limited
Direct Support: support@hapkonic.com | Priority Phone: +91 8825904050
        """

        card1 = cls._render_card("Enterprise Organization Profile", [
            ("Company Name", company_name),
            ("Company Code", company_code or "System Assigned"),
            ("Industry Sector", industry),
            ("Headquarters", location),
            ("Authorized Modules", modules_str),
        ])

        card2 = cls._render_card("Administrative Access Profile", [
            ("Portal Access URL", f'<a href="{portal_url}" style="color: #38BDF8; text-decoration: none;">{portal_url}</a>'),
            ("Administrator Email", admin_email),
            ("Initial Access Scope", "Super Administrator (Full Tenant Control)"),
        ])

        cred_box = cls._render_credential_box(
            "Initial One-Time Password",
            temporary_password,
            "Mandatory rotation required upon first sign-in."
        )

        advisory = cls._render_advisory(
            "Your company database is completely isolated with multi-tenant zero-trust isolation. Configure your facility locations and warehouses prior to importing product catalogs.",
            severity="info"
        )

        intro_html = f"""
        This official communication confirms that your enterprise tenant organization has been provisioned on the Invenza Platform. 
        Your dedicated administrative environment is ready for commercial deployment.
        """

        body_html = cls._render_master_layout(
            subject=subject,
            preheader=preheader,
            badge_text="ENTERPRISE PROVISIONING",
            badge_type="teal",
            title="Organization Provisioning Complete",
            subtitle=f"{company_name} · Administrator Credential Dispatch",
            salutation=f"Dear {admin_name},",
            body_intro_html=intro_html,
            content_cards_html=card1 + card2 + cred_box + advisory,
            cta_text="Access Administrative Console →",
            cta_url=portal_url,
            cta_color="teal",
            signoff_team="Invenza Platform Operations Team",
        )

        return await cls.send_email_async(
            recipient=admin_email,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            metadata={"company_name": company_name, "type": "company_admin_credentials"},
        )

    # ═════════════════════════════════════════════════════════════════════════════
    # 2. TEAM INVITATION: STAFF USER CREDENTIAL DISPATCH
    # ═════════════════════════════════════════════════════════════════════════════

    @classmethod
    async def send_staff_user_credentials(
        cls,
        staff_name: str,
        staff_email: str,
        company_name: str,
        role: str,
        temporary_password: str,
        portal_url: str = "http://localhost:5173",
        location: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Dispatches operational credentials to an invited team member."""
        role_label = role.replace("_", " ").title()
        subject = f"Official Notice: Invenza Platform Access Granted - {company_name}"
        preheader = f"Your user account for {company_name} on Invenza has been provisioned."

        body_text = f"""
OFFICIAL NOTIFICATION: USER ACCOUNT PROVISIONED
===============================================
Dear {staff_name},

An authorized administrator has provisioned your user account on the Invenza Inventory Platform for {company_name}.

OPERATIONAL ACCESS PROFILE:
- Organization: {company_name}
- Assigned Role: {role_label}
- Assigned Location: {location or 'All Assigned Warehouses'}
- Portal URL: {portal_url}
- Login Email: {staff_email}
- Initial Password: {temporary_password}

SECURITY ADVISORY:
Please log in to the portal and establish a personal password immediately. All operations performed are logged to the organizational audit ledger.

Sincerely,
Invenza Identity & Access Management
        """

        card = cls._render_card("Assigned Operational Profile", [
            ("Organization", company_name),
            ("Assigned Role", role_label),
            ("Primary Facility", location or "All Assigned Facilities"),
            ("Portal URL", f'<a href="{portal_url}" style="color: #38BDF8; text-decoration: none;">{portal_url}</a>'),
            ("User Identity", staff_email),
        ])

        cred_box = cls._render_credential_box(
            "Initial One-Time Password",
            temporary_password,
            "Establish your personal password upon initial login."
        )

        advisory = cls._render_advisory(
            "Your actions on the platform are governed by organizational role permissions and recorded in accordance with enterprise compliance audit requirements.",
            severity="info"
        )

        intro_html = f"""
        An authorized administrator has granted you operational access to the Invenza Inventory Management Portal for <strong>{company_name}</strong>. 
        Your login credentials and role assignment are detailed below:
        """

        body_html = cls._render_master_layout(
            subject=subject,
            preheader=preheader,
            badge_text="TEAM ACCESS DISPATCH",
            badge_type="indigo",
            title="User Account Provisioned",
            subtitle=f"{company_name} · Operational Staff Dispatch",
            salutation=f"Dear {staff_name},",
            body_intro_html=intro_html,
            content_cards_html=card + cred_box + advisory,
            cta_text="Log In to Invenza Portal →",
            cta_url=portal_url,
            cta_color="teal",
            signoff_team="Invenza Identity & Access Management",
        )

        return await cls.send_email_async(
            recipient=staff_email,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            metadata={"company_name": company_name, "role": role, "type": "staff_user_credentials"},
        )

    # ═════════════════════════════════════════════════════════════════════════════
    # 3. ACCOUNT SECURITY: PASSWORD RESET OTP
    # ═════════════════════════════════════════════════════════════════════════════

    @classmethod
    async def send_password_reset_otp(
        cls,
        recipient_email: str,
        otp_code: str,
        ttl_minutes: int = 15,
        user_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Dispatches a secure 6-digit verification code for password recovery."""
        subject = "Security Verification Code: Invenza Account Password Reset"
        preheader = f"Your single-use password recovery verification code is {otp_code}."

        salutation_name = user_name if user_name else "Account Holder"

        body_text = f"""
SECURITY NOTIFICATION: PASSWORD RESET VERIFICATION
==================================================
Attention: {salutation_name},

We received a verified request to reset the password for your Invenza account ({recipient_email}).

YOUR SINGLE-USE VERIFICATION CODE:
{otp_code}

This authorization code is valid for {ttl_minutes} minutes from issuance.

SECURITY ADVISORY:
If you did not initiate this recovery request, please disregard this communication and notify security@hapkonic.com immediately. Invenza personnel will never request your verification code or credentials.

Sincerely,
Invenza Security & Authentication Team
        """

        cred_box = cls._render_credential_box(
            f"Verification Code ({ttl_minutes}-Minute Expiry)",
            otp_code,
            f"Valid for {ttl_minutes} minutes · Single-use authorization code"
        )

        advisory = cls._render_advisory(
            "If you did not request a password reset, your credentials may be secure, but we advise auditing your recent account activity. Never share this code with anyone.",
            severity="warning"
        )

        intro_html = f"""
        We received a request to reset the authentication password associated with your Invenza account (<strong>{recipient_email}</strong>). 
        To authorize this identity verification and establish new credentials, enter the code below:
        """

        body_html = cls._render_master_layout(
            subject=subject,
            preheader=preheader,
            badge_text="SECURITY VERIFICATION",
            badge_type="amber",
            title="Password Reset Authorization",
            subtitle="Invenza Security & Identity Verification Desk",
            salutation=f"Attention: {salutation_name},",
            body_intro_html=intro_html,
            content_cards_html=cred_box + advisory,
            signoff_team="Invenza Security & Authentication Team",
        )

        return await cls.send_email_async(
            recipient=recipient_email,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            metadata={"type": "password_reset_otp", "expires_in_minutes": ttl_minutes},
        )

    # ═════════════════════════════════════════════════════════════════════════════
    # 4. PRE-SALES: PUBLIC QUOTE REQUEST CONFIRMATION (TO PROSPECT)
    # ═════════════════════════════════════════════════════════════════════════════

    @classmethod
    async def send_quote_confirmation_email(cls, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatches an official quotation request acknowledgment to the prospective enterprise client."""
        recipient = lead_data.get("email")
        if not recipient:
            return {"success": False, "message": "Missing recipient email"}

        contact_name = lead_data.get("contact_name") or "Valued Client"
        company_name = lead_data.get("company_name") or "Your Enterprise"
        industry = lead_data.get("industry") or "General Merchandise"
        
        loc_city = lead_data.get("location") or "India"
        loc_state = lead_data.get("state") or ""
        loc_pin = lead_data.get("pincode") or ""
        location_str = f"{loc_city}, {loc_state} - {loc_pin}".strip(", -") if (loc_state or loc_pin) else loc_city

        warehouses = lead_data.get("estimated_warehouses") or "1 - 2 Facilities"
        skus = lead_data.get("estimated_skus") or "Up to 5,000 SKUs"
        orders = lead_data.get("estimated_monthly_orders") or "Standard Volume"
        tier = lead_data.get("tier_estimate") or "Enterprise Growth"
        
        modules = lead_data.get("selected_modules") or []
        modules_str = ", ".join([m.capitalize() for m in modules]) if modules else "Full ERP Suite"

        subject = f"Commercial Inquiry Received: Invenza Enterprise Platform Quote - {company_name}"
        preheader = f"Thank you for contacting Invenza. We have received your quotation request for {company_name}."

        body_text = f"""
COMMERCIAL INQUIRY ACKNOWLEDGMENT
=================================
Dear {contact_name},

Thank you for your commercial interest in the Invenza Inventory Management Platform. We have successfully registered your quotation request on behalf of {company_name}.

SUBMITTED COMMERCIAL REQUIREMENTS:
- Entity Name: {company_name}
- Industry Sector: {industry}
- Registered Location: {location_str}
- Estimated Warehouses: {warehouses}
- SKU Catalog Scale: {skus}
- Monthly Order Volume: {orders}
- Requested Modules: {modules_str}
- Projected Tier: {tier}

SERVICE LEVEL AGREEMENT (SLA):
Our commercial solutions team is evaluating your specifications. A formal commercial proposal and pricing matrix will be furnished to your registered email address within 24 to 48 business hours.

DIRECT CONTACT DESK:
For priority scheduling or technical inquiries:
- Phone: +91 8825904050
- Email: support@hapkonic.com

Sincerely,
Invenza Commercial Operations Team
        """

        card = cls._render_card("Submitted Commercial Specifications", [
            ("Organization / Entity", company_name),
            ("Industry Sector", industry),
            ("Location / State", location_str),
            ("Facility Scale", warehouses),
            ("Active SKU Catalog", skus),
            ("Projected Monthly Orders", orders),
            ("Required Modules", modules_str),
            ("Projected Tier", tier),
        ])

        advisory = cls._render_advisory(
            "Our enterprise solutions team will review your operational requirements and deliver an itemized commercial proposal within 24 to 48 business hours.",
            severity="info"
        )

        intro_html = f"""
        Thank you for contacting Invenza regarding your enterprise supply chain and inventory management requirements. 
        We have received your quotation request on behalf of <strong>{company_name}</strong>. The parameters submitted for commercial evaluation are detailed below:
        """

        body_html = cls._render_master_layout(
            subject=subject,
            preheader=preheader,
            badge_text="COMMERCIAL INQUIRY",
            badge_type="teal",
            title="Quotation Request Acknowledged",
            subtitle=f"{company_name} · Pre-Sales Commercial Desk",
            salutation=f"Dear {contact_name},",
            body_intro_html=intro_html,
            content_cards_html=card + advisory,
            signoff_team="Invenza Commercial Operations Team",
        )

        return await cls.send_email_async(
            recipient=recipient,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            metadata={"company_name": company_name, "type": "quote_request_confirmation"},
        )

    # ═════════════════════════════════════════════════════════════════════════════
    # 5. COMMERCIAL INTERNAL ALERT: NEW LEAD INQUIRY (TO INVENZA TEAM)
    # ═════════════════════════════════════════════════════════════════════════════

    @classmethod
    def send_lead_inquiry_notification(cls, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatches an internal alert to Invenza Commercial Operations when a new quotation request arrives."""
        _load_active_env()
        internal_recipient = (
            os.getenv("SALES_NOTIFICATION_EMAIL")
            or os.getenv("SMTP_USER")
            or "superadmin@invenza.internal"
        ).strip()

        company = lead_data.get("company_name", "Prospective Enterprise")
        contact = lead_data.get("contact_name", "Primary Contact")
        email = lead_data.get("email", "N/A")
        phone = lead_data.get("phone", "N/A")
        industry = lead_data.get("industry", "N/A")

        loc_city = lead_data.get("location") or "N/A"
        loc_state = lead_data.get("state") or ""
        loc_pin = lead_data.get("pincode") or ""
        location_str = f"{loc_city}, {loc_state} - {loc_pin}".strip(", -") if (loc_state or loc_pin) else loc_city

        warehouses = lead_data.get("estimated_warehouses", "N/A")
        skus = lead_data.get("estimated_skus", "N/A")
        orders = lead_data.get("estimated_monthly_orders", "N/A")
        tier = lead_data.get("tier_estimate", "Growth Suite")
        notes = lead_data.get("notes") or "No additional notes provided."

        modules = lead_data.get("selected_modules") or []
        modules_str = ", ".join([m.capitalize() for m in modules]) if modules else "All Modules"

        subject = f"Commercial Lead Alert: New Quote Request - {company}"
        preheader = f"New commercial quotation inquiry submitted by {contact} ({company})."

        body_text = f"""
INTERNAL DISPATCH: NEW COMMERCIAL QUOTATION INQUIRY
===================================================
A new quotation request has been received on the public portal.

PROSPECT CONTACT DETAILS:
- Entity: {company}
- Contact Person: {contact}
- Email Address: {email}
- Phone: {phone}
- Location: {location_str}
- Industry: {industry}

OPERATIONAL SCALE SPECIFICATIONS:
- Estimated Warehouses: {warehouses}
- Catalog Scale: {skus}
- Order Volume: {orders}
- Selected Modules: {modules_str}
- Projected Tier: {tier}
- Client Notes: {notes}

ACTION REQUIRED:
Review lead profile in Super Admin Console or initiate commercial discussion within SLA.
        """

        card1 = cls._render_card("Prospective Enterprise Contact", [
            ("Company Name", company),
            ("Primary Contact", contact),
            ("Email Address", f'<a href="mailto:{email}" style="color: #38BDF8; text-decoration: none;">{email}</a>'),
            ("Phone / Mobile", f'<a href="tel:{phone}" style="color: #38BDF8; text-decoration: none;">{phone}</a>'),
            ("Registered State / PIN", location_str),
            ("Industry Sector", industry),
        ])

        card2 = cls._render_card("Projected Operational Scope", [
            ("Facility Count", warehouses),
            ("SKU Catalog Scale", skus),
            ("Monthly Order Volume", orders),
            ("Requested Modules", modules_str),
            ("Estimated Tier", tier),
            ("Client Notes", notes),
        ])

        intro_html = f"""
        A prospective enterprise client has submitted an inquiry for platform deployment via the public portal. 
        Commercial parameters and operational scope are summarized below for sales triage:
        """

        body_html = cls._render_master_layout(
            subject=subject,
            preheader=preheader,
            badge_text="INCOMING COMMERCIAL LEAD",
            badge_type="teal",
            title="New Commercial Lead Received",
            subtitle=f"{company} · Invenza Internal Sales Triage",
            salutation="Invenza Commercial & Sales Operations Team,",
            body_intro_html=intro_html,
            content_cards_html=card1 + card2,
            cta_text="Triage Lead in Super Admin Console →",
            cta_url="http://localhost:5173/leads",
            cta_color="teal",
            signoff_team="Invenza Automated Lead Dispatch Desk",
        )

        return asyncio.create_task(
            cls.send_email_async(
                recipient=internal_recipient,
                subject=subject,
                body_text=body_text,
                body_html=body_html,
                metadata={"company_name": company, "type": "internal_lead_alert"},
            )
        )

    # ═════════════════════════════════════════════════════════════════════════════
    # 6. COMPLIANCE SAFEGUARD: DUAL-AUTHORIZATION APPROVAL NOTICE (TO SUPER ADMIN)
    # ═════════════════════════════════════════════════════════════════════════════

    @classmethod
    async def send_security_safeguard_alert(
        cls,
        action_type: str,
        tenant_name: str,
        requester_name: str,
        requester_email: str,
        affected_scope: str,
        reason: str,
        request_id: str,
        superadmin_email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Dispatches an urgent dual-authorization compliance alert to the Super Administrator."""
        recipient = superadmin_email or os.getenv("SMTP_USER") or "superadmin@invenza.internal"
        action_label = action_type.replace("_", " ").title()

        subject = f"CRITICAL COMPLIANCE NOTICE: Dual-Authorization Required - {action_label}"
        preheader = f"Authorization required for high-risk action: {action_label} for {tenant_name}."

        body_text = f"""
CRITICAL COMPLIANCE NOTICE: DUAL-AUTHORIZATION REQUIRED
======================================================
Attention: Super Administrator,

A high-impact operational request requiring multi-party administrative authorization has been initiated on the Invenza Platform. In accordance with enterprise governance protocols, execution is currently suspended pending your explicit review and authorization.

REQUEST SPECIFICATIONS:
- Action Requested: {action_label}
- Target Organization: {tenant_name}
- Initiating Operator: {requester_name} ({requester_email})
- Request Reference ID: {request_id}
- Affected Scope / Records: {affected_scope}
- Operational Justification: {reason}

GOVERNANCE ADVISORY:
This operation is destructive or alters tenant operational access. Confirm all compliance prerequisites before approving. No changes have been executed.

Sincerely,
Invenza Enterprise Compliance Desk
        """

        card = cls._render_card("Safeguard Request Specifications", [
            ("Requested Action", action_label),
            ("Target Organization", tenant_name),
            ("Initiating Operator", f"{requester_name} ({requester_email})"),
            ("Request Reference ID", request_id),
            ("Affected Scope", affected_scope),
            ("Stated Justification", reason),
            ("Current Status", "PENDING DUAL-AUTHORIZATION"),
        ])

        advisory = cls._render_advisory(
            "This operation involves high-impact data modification. Verify operational prerequisites and obtain secondary sign-off before approving this request in the Security Queue.",
            severity="danger"
        )

        intro_html = f"""
        A high-impact operational request requiring secondary administrative authorization has been initiated for <strong>{tenant_name}</strong>. 
        Execution is suspended pending your review in the Compliance Safeguards Queue.
        """

        body_html = cls._render_master_layout(
            subject=subject,
            preheader=preheader,
            badge_text="COMPLIANCE SAFEGUARD",
            badge_type="crimson",
            title="Dual-Authorization Required",
            subtitle=f"{action_label} · Security Safeguards Desk",
            salutation="Attention: Super Administrator,",
            body_intro_html=intro_html,
            content_cards_html=card + advisory,
            cta_text="Review Safeguard in Security Queue →",
            cta_url="http://localhost:5173/security-safeguards",
            cta_color="crimson",
            signoff_team="Invenza Enterprise Compliance Desk",
        )

        return await cls.send_email_async(
            recipient=recipient,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            metadata={"action": action_type, "request_id": request_id, "type": "safeguard_approval_notice"},
        )

    # ═════════════════════════════════════════════════════════════════════════════
    # 7. SECURITY STEP-UP: DESTRUCTIVE ACTION VERIFICATION OTP (TO OPERATOR)
    # ═════════════════════════════════════════════════════════════════════════════

    @classmethod
    async def send_destruction_otp_email(
        cls,
        operator_email: str,
        action_name: str,
        otp_code: str,
        operator_name: Optional[str] = None,
        ttl_minutes: int = 10,
    ) -> Dict[str, Any]:
        """Dispatches an immediate OTP verification code for a destructive operation in the Danger Zone."""
        action_label = action_name.replace("_", " ").title()
        subject = f"CRITICAL VERIFICATION: Danger Zone Operation Code - {action_label}"
        preheader = f"Your single-use verification code for irreversible destruction: {action_label}."

        salutation = f"Attention: {operator_name}," if operator_name else "Attention: Authorized Operator,"

        body_text = f"""
CRITICAL SECURITY VERIFICATION: DESTRUCTIVE OPERATION
=====================================================
{salutation}

You have requested to execute an irreversible, destructive operation on the Invenza Platform: {action_label}.

YOUR SINGLE-USE DESTRUCTION CODE:
{otp_code}

This code is valid for {ttl_minutes} minutes. Once verified and executed, this operation CANNOT be rolled back.

SECURITY WARNING:
If you did not initiate this destructive operation, terminate your session immediately and report this incident to security@hapkonic.com.

Sincerely,
Invenza Data Protection Desk
        """

        cred_box = cls._render_credential_box(
            f"Destruction Verification Code ({ttl_minutes}-Minute Expiry)",
            otp_code,
            f"Valid for {ttl_minutes} minutes · Irreversible operation authorization"
        )

        advisory = cls._render_advisory(
            f"Executing '{action_label}' will permanently delete records from the system database. Ensure all historical data backups have been verified prior to inputting this code.",
            severity="danger"
        )

        intro_html = f"""
        You have initiated a destructive, irreversible command on the Invenza Platform: <strong>{action_label}</strong>. 
        To authorize this operation, enter the single-use verification code below:
        """

        body_html = cls._render_master_layout(
            subject=subject,
            preheader=preheader,
            badge_text="DESTRUCTIVE ACTION STEP-UP",
            badge_type="crimson",
            title="Destruction Authorization Required",
            subtitle=f"{action_label} · Data Protection & Integrity Desk",
            salutation=salutation,
            body_intro_html=intro_html,
            content_cards_html=cred_box + advisory,
            signoff_team="Invenza Data Protection Desk",
        )

        return await cls.send_email_async(
            recipient=operator_email,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            metadata={"action": action_name, "type": "destruction_otp"},
        )

    # ═════════════════════════════════════════════════════════════════════════════
    # 8. COMMERCIAL BILLING: GST TAX INVOICE & PAYMENT RECEIPT
    # ═════════════════════════════════════════════════════════════════════════════

    @classmethod
    async def send_billing_receipt_email(
        cls,
        recipient_email: str,
        recipient_name: str,
        company_name: str,
        invoice_number: str,
        payment_mode: str,
        taxable_value: float,
        cgst: float,
        sgst: float,
        igst: float,
        grand_total: float,
        place_of_supply: str,
        invoice_id: str,
        pdf_download_url: Optional[str] = None,
        single_tax: float = 0.0,
        tax_type: str = "GST",
        tax_label: str = "GST",
        currency_code: str = "INR",
        currency_symbol: str = "₹",
    ) -> Dict[str, Any]:
        """Dispatches an official Tax Invoice and payment receipt (GST / VAT / Sales Tax aware)."""
        subject = f"Official Tax Invoice & Payment Receipt: {invoice_number} - {company_name}"
        preheader = f"Payment confirmation and {tax_label} Tax Invoice {invoice_number} for {company_name} ({currency_code} {grand_total:,.2f})."

        download_link = pdf_download_url or f"http://localhost:8000/api/v1/billing/setup-fee/{invoice_id}/invoice-pdf"

        region_label = "Place of Supply" if tax_type == "GST" else "Tax Region"

        if tax_type == "GST":
            breakdown_lines = (
                f"- CGST: {currency_code} {cgst:,.2f}\n"
                f"- SGST: {currency_code} {sgst:,.2f}\n"
                f"- IGST: {currency_code} {igst:,.2f}"
            )
            card_tax_rows = [
                ("CGST (Intrastate)", f"{currency_code} {cgst:,.2f}"),
                ("SGST (Intrastate)", f"{currency_code} {sgst:,.2f}"),
                ("IGST (Interstate)", f"{currency_code} {igst:,.2f}"),
            ]
        else:
            zero_note = " (0% - No state sales tax)" if (tax_type == "SALES_TAX" and single_tax == 0) else ""
            breakdown_lines = f"- {tax_label}{zero_note}: {currency_code} {single_tax:,.2f}"
            card_tax_rows = [(f"{tax_label}{zero_note}", f"{currency_code} {single_tax:,.2f}")]

        body_text = f"""
OFFICIAL {tax_label.upper()} TAX INVOICE & PAYMENT RECEIPT
==========================================
Dear {recipient_name},

Thank you for your payment. This communication serves as your official Tax Invoice and receipt for commercial services on the Invenza Enterprise Platform.

INVOICE SUMMARY:
- Invoice Number: {invoice_number}
- Billed Organization: {company_name}
- Payment Mode: {payment_mode}
- {region_label}: {place_of_supply}

FINANCIAL BREAKDOWN:
- Taxable Value: {currency_code} {taxable_value:,.2f}
{breakdown_lines}
- Grand Total: {currency_code} {grand_total:,.2f}

Download Official PDF Invoice:
{download_link}

Sincerely,
Invenza Commercial Billing Team
        """

        card = cls._render_card(f"{tax_label} Tax Invoice Breakdown", [
            ("Invoice Number", invoice_number),
            ("Billed Organization", company_name),
            ("Payment Mode", payment_mode),
            (region_label, place_of_supply),
            ("Taxable Value", f"{currency_code} {taxable_value:,.2f}"),
            *card_tax_rows,
            ("Total Amount Paid", f"{currency_code} {grand_total:,.2f}"),
        ])

        advisory = cls._render_advisory(
            "This electronic receipt constitutes an official tax-compliant commercial document issued by Invenza. Retain for commercial and tax audit records.",
            severity="info"
        )

        intro_html = f"""
        Thank you for your payment. This official correspondence confirms receipt of payment for commercial platform services for <strong>{company_name}</strong>.
        Your {tax_label} tax breakdown and invoice specifics are summarized below:
        """

        body_html = cls._render_master_layout(
            subject=subject,
            preheader=preheader,
            badge_text="TAX INVOICE RECEIPT",
            badge_type="emerald",
            title="Payment Receipt & Tax Invoice",
            subtitle=f"{invoice_number} · Invenza Commercial Accounts",
            salutation=f"Dear {recipient_name},",
            body_intro_html=intro_html,
            content_cards_html=card + advisory,
            cta_text="Download Official PDF Invoice →",
            cta_url=download_link,
            cta_color="emerald",
            signoff_team="Invenza Commercial Billing Team",
        )

        return await cls.send_email_async(
            recipient=recipient_email,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            metadata={"invoice_number": invoice_number, "company_name": company_name, "type": "billing_tax_invoice", "tax_type": tax_type, "currency_code": currency_code},
        )

    # ═════════════════════════════════════════════════════════════════════════════
    # 9. COMMERCIAL BILLING: MAINTENANCE CYCLE PAYMENT REMINDER
    # ═════════════════════════════════════════════════════════════════════════════

    @classmethod
    async def send_billing_reminder_email(
        cls,
        recipient_email: str,
        recipient_name: str,
        company_name: str,
        cycle_month: str,
        amount_due: float,
        due_date: str,
        portal_url: str = "http://localhost:5173/billing",
        tax_label: str = "GST",
        currency_code: str = "INR",
    ) -> Dict[str, Any]:
        """Dispatches an official maintenance cycle billing notice/reminder to the organization administrator."""
        subject = f"Commercial Notice: Maintenance Cycle Due - {cycle_month} - {company_name}"
        preheader = f"Monthly maintenance settlement for cycle {cycle_month} is due for {company_name}."

        body_text = f"""
COMMERCIAL BILLING NOTICE: MAINTENANCE CYCLE
=============================================
Dear {recipient_name},

This communication serves as an official billing reminder regarding the monthly platform maintenance fee for {company_name} for the billing cycle {cycle_month}.

CYCLE DETAILS:
- Billed Entity: {company_name}
- Billing Cycle: {cycle_month}
- Amount Payable: {currency_code} {amount_due:,.2f} (+ applicable {tax_label})
- Payment Due Date: {due_date}
- Status: Pending Settlement

SETTLEMENT INSTRUCTIONS (NEFT/RTGS):
- Account Name: Hapkonic Technologies Private Limited
- Bank: HDFC Bank Limited
- Account Number: 50200088259040
- IFSC Code: HDFC0001234
- Branch: Koramangala, Bengaluru

Please arrange for payment remittance prior to the due date to ensure continuous platform availability.

Sincerely,
Invenza Commercial Billing Team
        """

        card1 = cls._render_card("Maintenance Cycle Details", [
            ("Organization", company_name),
            ("Billing Cycle", cycle_month),
            ("Base Amount Due", f"{currency_code} {amount_due:,.2f}"),
            ("Applicable Taxes", f"{tax_label} as applicable by region"),
            ("Due Date", due_date),
            ("Current Status", "Pending Settlement"),
        ])

        card2 = cls._render_card("Direct Remittance Bank Details (NEFT / RTGS)", [
            ("Beneficiary Name", "Hapkonic Technologies Private Limited"),
            ("Bank Institution", "HDFC Bank Limited"),
            ("Account Number", "50200088259040"),
            ("IFSC Code", "HDFC0001234"),
            ("Branch / City", "Koramangala, Bengaluru"),
        ])

        intro_html = f"""
        This official correspondence serves as a billing statement for monthly platform maintenance services for <strong>{company_name}</strong> 
        covering the service cycle <strong>{cycle_month}</strong>.
        """

        body_html = cls._render_master_layout(
            subject=subject,
            preheader=preheader,
            badge_text="BILLING ADVISORY",
            badge_type="amber",
            title="Maintenance Cycle Notice",
            subtitle=f"{company_name} · Service Period {cycle_month}",
            salutation=f"Dear {recipient_name},",
            body_intro_html=intro_html,
            content_cards_html=card1 + card2,
            cta_text="View Billing Ledger in Console →",
            cta_url=portal_url,
            cta_color="teal",
            signoff_team="Invenza Commercial Billing Team",
        )

        return await cls.send_email_async(
            recipient=recipient_email,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            metadata={"cycle_month": cycle_month, "company_name": company_name, "type": "billing_reminder"},
        )

    # ═════════════════════════════════════════════════════════════════════════════
    # 10. ACCESS GOVERNANCE: ROLE & PERMISSION MODIFICATION NOTIFICATION
    # ═════════════════════════════════════════════════════════════════════════════

    @classmethod
    async def send_role_change_notification(
        cls,
        user_email: str,
        user_name: str,
        company_name: str,
        previous_role: str,
        new_role: str,
        permissions_count: int,
        admin_name: str,
        portal_url: str = "http://localhost:5173",
    ) -> Dict[str, Any]:
        """Dispatches an access governance notification when a user's role or permissions are updated."""
        prev_label = previous_role.replace("_", " ").title()
        new_label = new_role.replace("_", " ").title()

        subject = f"Security Notice: Account Access Role Updated - Invenza"
        preheader = f"Your operational role in {company_name} has been updated to {new_label}."

        body_text = f"""
ACCESS GOVERNANCE NOTIFICATION: ROLE MODIFICATION
=================================================
Dear {user_name},

An organization administrator has modified your operational role and permissions on the Invenza Platform for {company_name}.

UPDATED ACCESS PROFILE:
- Organization: {company_name}
- Previous Role: {prev_label}
- Updated Role: {new_label}
- Authorized Permissions: {permissions_count} operational scopes
- Modified By: {admin_name}

SESSION INSTRUCTIONS:
If your active browser session does not immediately reflect these modified permissions, please sign out and log back in to refresh your authentication tokens.

Sincerely,
Invenza Identity & Governance Desk
        """

        card = cls._render_card("Access Modification Summary", [
            ("Organization", company_name),
            ("Previous Role", prev_label),
            ("Updated Operational Role", new_label),
            ("Active Permission Scopes", f"{permissions_count} authorized permissions"),
            ("Authorized By", admin_name),
            ("Effective Timestamp", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")),
        ])

        advisory = cls._render_advisory(
            "If you are currently signed into the Invenza Portal, sign out and sign back in to apply your updated permission parameters.",
            severity="info"
        )

        intro_html = f"""
        An authorized administrator has updated your access credentials and operational scope within <strong>{company_name}</strong>. 
        Your modified role assignment is outlined below:
        """

        body_html = cls._render_master_layout(
            subject=subject,
            preheader=preheader,
            badge_text="ACCESS GOVERNANCE",
            badge_type="indigo",
            title="Operational Role Updated",
            subtitle=f"{company_name} · Identity & Access Desk",
            salutation=f"Dear {user_name},",
            body_intro_html=intro_html,
            content_cards_html=card + advisory,
            cta_text="Log In to Invenza Portal →",
            cta_url=portal_url,
            cta_color="teal",
            signoff_team="Invenza Identity & Governance Desk",
        )

        return await cls.send_email_async(
            recipient=user_email,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            metadata={"user_email": user_email, "new_role": new_role, "type": "role_change_notification"},
        )

    # ═════════════════════════════════════════════════════════════════════════════
    # 11. SUPPLY CHAIN ALERT: LOW STOCK INVENTORY REORDER ADVISORY
    # ═════════════════════════════════════════════════════════════════════════════

    @classmethod
    async def send_low_stock_alert(
        cls,
        recipient_email: str,
        company_name: str,
        product_name: str,
        sku: str,
        current_stock: float,
        reorder_level: float,
        warehouse_name: str,
        unit: str = "Units",
        portal_url: str = "http://localhost:5173/products",
    ) -> Dict[str, Any]:
        """Dispatches an urgent operational supply chain alert when an SKU's stock drops below safety reorder threshold."""
        subject = f"SUPPLY CHAIN ALERT: Low Stock Threshold Reached - {product_name} ({sku})"
        preheader = f"Stock for {product_name} ({sku}) is at {current_stock} {unit}, below reorder point of {reorder_level} {unit}."

        body_text = f"""
OPERATIONAL SUPPLY CHAIN ALERT: LOW STOCK THRESHOLD
===================================================
Attention: Inventory Operations Team,

The Invenza Automated Inventory Monitor has detected that available inventory for {product_name} ({sku}) in {warehouse_name} has fallen to or below the safety reorder threshold.

SKU SPECIFICATIONS:
- Organization: {company_name}
- Product Description: {product_name}
- SKU / Catalog Code: {sku}
- Facility / Warehouse: {warehouse_name}
- Current Available Balance: {current_stock} {unit}
- Safety Reorder Level: {reorder_level} {unit}
- Deficit to Reorder Point: {max(0.0, reorder_level - current_stock)} {unit}

RECOMMENDED ACTION:
Review current purchase orders or initiate supplier procurement immediately to prevent fulfillment delays.

Sincerely,
Invenza Inventory Operations Desk
        """

        card = cls._render_card("Inventory Balance & Reorder Specifications", [
            ("Organization", company_name),
            ("Product Description", product_name),
            ("SKU / Item Code", sku),
            ("Storage Facility", warehouse_name),
            ("Current On-Hand Balance", f'<span style="color: #FBBF24;">{current_stock:,.0f} {unit}</span>'),
            ("Safety Reorder Threshold", f"{reorder_level:,.0f} {unit}"),
            ("Replenishment Deficit", f"{max(0.0, reorder_level - current_stock):,.0f} {unit}"),
        ])

        advisory = cls._render_advisory(
            f"Available inventory in {warehouse_name} has reached critical replenishment levels. Initiate purchase orders or stock transfers to avoid stockouts.",
            severity="warning"
        )

        intro_html = f"""
        The Invenza Automated Inventory Monitoring Engine has detected that stock for <strong>{product_name}</strong> 
        has depleted below the configured safety replenishment threshold in <strong>{warehouse_name}</strong>.
        """

        body_html = cls._render_master_layout(
            subject=subject,
            preheader=preheader,
            badge_text="SUPPLY CHAIN ALERT",
            badge_type="amber",
            title="Inventory Threshold Alert",
            subtitle=f"{sku} · Safety Stock Depletion Notice",
            salutation="Attention: Inventory Operations Team,",
            body_intro_html=intro_html,
            content_cards_html=card + advisory,
            cta_text="Review Product & Reorder →",
            cta_url=portal_url,
            cta_color="teal",
            signoff_team="Invenza Inventory Operations Desk",
        )

        return await cls.send_email_async(
            recipient=recipient_email,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            metadata={"sku": sku, "company_name": company_name, "type": "low_stock_alert"},
        )
