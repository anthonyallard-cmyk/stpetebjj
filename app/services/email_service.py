import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import settings
from app.database import get_site_settings

logger = logging.getLogger(__name__)


def send_quote_notification(quote_data: dict) -> bool:
    """Sends an email notification for a new Free Trial / Contact / Membership inquiry."""
    cfg = get_site_settings()
    recipients_str = cfg.get("email_quotes") or settings.EMAIL_QUOTES
    recipients = [r.strip() for r in recipients_str.split(",") if r.strip()]

    subject = f"New St. Pete BJJ Inquiry / Free Class Request — {quote_data.get('name', 'Prospect')}"

    html_body = f"""
    <div style="font-family: 'Plus Jakarta Sans', Arial, sans-serif; max-width: 620px; margin: 0 auto; background: #09090B; color: #FAFAFA; border: 1px solid #27272A; border-radius: 14px; overflow: hidden;">
        <div style="background: #CE1E36; padding: 20px 26px;">
            <h2 style="margin: 0; color: #FFFFFF; font-size: 20px; letter-spacing: 0.02em;">
                ST. PETE BRAZILIAN JIU-JITSU — NEW INQUIRY
            </h2>
        </div>
        <div style="padding: 24px 26px; font-size: 15px; line-height: 1.6;">
            <p style="margin-top: 0;">A new student inquiry or free introductory class request was submitted on <strong>stpetebjj.com</strong>:</p>
            <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
                <tr><td style="padding: 8px 0; color: #A1A1AA; width: 160px;">Name:</td><td style="padding: 8px 0; font-weight: 700; color: #FFFFFF;">{quote_data.get('name')}</td></tr>
                <tr><td style="padding: 8px 0; color: #A1A1AA;">Email:</td><td style="padding: 8px 0; color: #FFFFFF;">{quote_data.get('email')}</td></tr>
                <tr><td style="padding: 8px 0; color: #A1A1AA;">Phone / Text:</td><td style="padding: 8px 0; color: #FFFFFF;">{quote_data.get('phone') or 'N/A'}</td></tr>
                <tr><td style="padding: 8px 0; color: #A1A1AA;">Program Interest:</td><td style="padding: 8px 0; color: #CE1E36; font-weight: 700;">{quote_data.get('program_interest') or 'Fundamentals / Free Class'}</td></tr>
                <tr><td style="padding: 8px 0; color: #A1A1AA;">Experience Level:</td><td style="padding: 8px 0; color: #FFFFFF;">{quote_data.get('experience_level') or 'Brand New Beginner'}</td></tr>
                <tr><td style="padding: 8px 0; color: #A1A1AA;">Preferred Day/Time:</td><td style="padding: 8px 0; color: #FFFFFF;">{quote_data.get('preferred_date') or 'Flexible'}</td></tr>
            </table>
            <div style="background: #18181B; padding: 16px; border-radius: 10px; border: 1px solid #27272A;">
                <div style="color: #A1A1AA; font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 6px;">Message / Goals:</div>
                <div style="color: #FAFAFA; white-space: pre-wrap;">{quote_data.get('message') or 'No additional message provided.'}</div>
            </div>
        </div>
    </div>
    """

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.SMTP_FROM
        msg["To"] = ", ".join(recipients)
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=4) as server:
            if settings.SMTP_USER and settings.SMTP_PASS:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASS)
            server.sendmail(settings.SMTP_FROM, recipients, msg.as_string())
        return True
    except Exception as e:
        logger.info(f"SMTP dispatch skipped/logged locally ({e})")
        return False
