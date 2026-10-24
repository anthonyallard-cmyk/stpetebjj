import html
import logging
import re
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

from app.config import settings
from app.database import db_cursor, get_site_settings

logger = logging.getLogger(__name__)

CRM_STATUS_OPTIONS = [
    ("new", "New Inquiry", "bg-red-500/20 text-red-300 border-red-500/40"),
    ("followed_up", "Followed Up", "bg-amber-500/20 text-amber-300 border-amber-500/40"),
    ("free_class_scheduled", "Free Class Scheduled", "bg-cyan-500/20 text-cyan-300 border-cyan-500/40"),
    ("trial_active", "30-Day Free Trial", "bg-purple-500/20 text-purple-300 border-purple-500/40"),
    ("signed_up", "Signed Up (Member)", "bg-emerald-500/20 text-emerald-300 border-emerald-500/40"),
    ("archived", "Closed / Archived", "bg-zinc-700/40 text-zinc-400 border-zinc-600/40"),
]

CRM_STATUS_LABELS = {code: label for code, label, _ in CRM_STATUS_OPTIONS}


def _strip_tags(html_str: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", html_str, flags=re.IGNORECASE)
    text = re.sub(r"</p>|</tr>|</div>|</li>|</h2>|</h3>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def render_branded_email(
    *,
    kicker: str,
    headline: str,
    intro_html: str,
    body_html: str,
    cta_label: str = "",
    cta_url: str = "",
    site: dict | None = None,
) -> str:
    """Renders a responsive, branded HTML email for St. Pete Brazilian Jiu-Jitsu."""
    if site is None:
        site = get_site_settings()

    base_url = settings.BASE_URL.rstrip("/")
    site_name = site.get("site_name") or "St. Pete Brazilian Jiu-Jitsu"
    phone = site.get("phone") or "(727) 619-4255"
    phone_vanity = site.get("phone_vanity") or "727.619.4BJJ"
    email_contact = site.get("email_contact") or "info@stpetebjj.com"
    address = site.get("address") or "5540 Haines Rd N, St. Petersburg, FL 33714"
    maps_url = site.get("google_maps_url") or "https://maps.app.goo.gl/m6PtQRRiCUu4HEZQ7"
    waiver_url = f"{base_url}{site.get('waiver_url') or '/wp-content/uploads/2017/01/Waiver.pdf'}"
    logo_url = f"{base_url}{site.get('logo_url') or '/static/images/logo-medallion.png'}"
    schedule_url = f"{base_url}/brazilian-jiu-jitsu-class-schedule-saint-petersburg-florida-2"

    cta_block = ""
    if cta_label and cta_url:
        cta_block = f"""
        <div style="margin: 28px 0 12px 0; text-align: center;">
            <a href="{cta_url}" style="display: inline-block; background-color: #CE1E36; color: #FFFFFF; font-weight: 800; font-size: 14px; text-transform: uppercase; letter-spacing: 0.06em; text-decoration: none; padding: 14px 28px; border-radius: 10px; box-shadow: 0 6px 18px rgba(206, 30, 54, 0.35);">
                {cta_label} &rarr;
            </a>
        </div>
        """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{headline} | {site_name}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #09090B; font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif; color: #F4F4F5;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color: #09090B; padding: 28px 12px;">
    <tr>
      <td align="center">
        <table role="presentation" width="620" cellspacing="0" cellpadding="0" border="0" style="max-width: 620px; width: 100%; background-color: #121216; border: 1px solid #27272A; border-radius: 18px; overflow: hidden; box-shadow: 0 20px 50px rgba(0,0,0,0.6);">

          <!-- Top Crimson Championship Bar -->
          <tr>
            <td style="background: linear-gradient(90deg, #CE1E36 0%, #9F1225 100%); height: 6px; font-size: 0; line-height: 0;">&nbsp;</td>
          </tr>

          <!-- Academy Brand Header -->
          <tr>
            <td style="background-color: #09090B; padding: 26px 30px; border-bottom: 1px solid #27272A;">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                <tr>
                  <td width="68" valign="middle">
                    <div style="width: 58px; height: 58px; border-radius: 999px; background-color: #FFFFFF; padding: 3px; text-align: center;">
                      <img src="{logo_url}" alt="{site_name}" width="52" height="52" style="display: block; width: 52px; height: 52px; border-radius: 999px; object-fit: contain;" />
                    </div>
                  </td>
                  <td valign="middle" style="padding-left: 12px;">
                    <div style="font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.14em; color: #FF4D64; margin-bottom: 3px;">
                      {kicker}
                    </div>
                    <div style="font-size: 22px; font-weight: 900; color: #FFFFFF; letter-spacing: 0.02em; line-height: 1.2;">
                      ST. PETE <span style="color: #CE1E36;">BRAZILIAN JIU-JITSU</span>
                    </div>
                    <div style="font-size: 12px; color: #A1A1AA; margin-top: 3px;">
                      4th Degree Black Belt Professor Sean Lynch • Est. 2006
                    </div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Main Email Content -->
          <tr>
            <td style="padding: 30px 30px 24px 30px; color: #E4E4E7; font-size: 15px; line-height: 1.65;">
              <h1 style="margin: 0 0 14px 0; font-size: 22px; font-weight: 800; color: #FFFFFF; line-height: 1.3;">
                {headline}
              </h1>
              <div style="margin-bottom: 18px; color: #D4D4D8;">
                {intro_html}
              </div>
              <div>
                {body_html}
              </div>
              {cta_block}
            </td>
          </tr>

          <!-- Academy Quick Reference Footer Box -->
          <tr>
            <td style="padding: 0 30px 26px 30px;">
              <div style="background-color: #18181B; border: 1px solid #27272A; border-radius: 14px; padding: 18px 20px;">
                <div style="font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.1em; color: #FF4D64; margin-bottom: 8px;">
                  Academy Location &amp; Quick Links
                </div>
                <div style="font-size: 13px; color: #D4D4D8; line-height: 1.6;">
                  <strong style="color: #FFFFFF;">{site_name}</strong><br />
                  📍 <a href="{maps_url}" style="color: #F4F4F5; text-decoration: underline;">{address}</a><br />
                  📱 Text or Call: <a href="tel:17276194255" style="color: #FF4D64; font-weight: 700; text-decoration: none;">{phone}</a> ({phone_vanity})<br />
                  ✉️ Email: <a href="mailto:{email_contact}" style="color: #F4F4F5; text-decoration: underline;">{email_contact}</a>
                </div>
                <div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid #27272A; font-size: 12px;">
                  <a href="{schedule_url}" style="color: #FF4D64; font-weight: 700; text-decoration: none; margin-right: 14px;">Class Schedule &rarr;</a>
                  <a href="{waiver_url}" style="color: #F4F4F5; font-weight: 600; text-decoration: none; margin-right: 14px;">Download Waiver (PDF) &rarr;</a>
                  <a href="{maps_url}" style="color: #FBBF24; font-weight: 700; text-decoration: none;">★ 5.0 Google Reviews &rarr;</a>
                </div>
              </div>
            </td>
          </tr>

          <!-- Bottom Copyright Bar -->
          <tr>
            <td style="background-color: #09090B; padding: 16px 30px; border-top: 1px solid #27272A; text-align: center; font-size: 11px; color: #71717A;">
              &copy; {datetime.now().year} {site_name} • {address}<br />
              Carlos Gracie Sr. &rarr; Carlos Gracie Jr. &rarr; Eduardo "Veio" de Lima &rarr; Professor Sean Lynch
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def dispatch_email(
    *,
    recipients: list[str],
    subject: str,
    html_body: str,
    template_type: str = "general",
    quote_id: int = 0,
    reply_to: str = "",
) -> tuple[bool, str]:
    """Dispatches an HTML email via Plesk SMTP and records the delivery in `email_logs`."""
    clean_recipients = [r.strip() for r in recipients if r and "@" in r]
    if not clean_recipients:
        return False, "No valid recipient email address."

    site = get_site_settings()
    smtp_host = (site.get("smtp_host") or settings.SMTP_HOST or "localhost").strip()
    try:
        smtp_port = int(site.get("smtp_port") or settings.SMTP_PORT or 587)
    except ValueError:
        smtp_port = 587
    smtp_encryption = (site.get("smtp_encryption") or "starttls").strip().lower()
    smtp_user = (site.get("smtp_user") or settings.SMTP_USER or "").strip()
    smtp_pass = (site.get("smtp_pass") or settings.SMTP_PASS or "").strip()
    from_email = (site.get("smtp_from_email") or settings.SMTP_FROM or "info@stpetebjj.com").strip()
    from_name = (site.get("smtp_from_name") or site.get("site_name") or "St. Pete Brazilian Jiu-Jitsu").strip()

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = formataddr((from_name, from_email))
    msg["To"] = ", ".join(clean_recipients)
    if reply_to:
        msg["Reply-To"] = reply_to

    plain_body = _strip_tags(html_body)
    msg.attach(MIMEText(plain_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    delivery_status = "sent"
    error_detail = ""
    sent_ok = False

    try:
        if smtp_encryption == "ssl" or smtp_port == 465:
            with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=6) as server:
                if smtp_user and smtp_pass:
                    server.login(smtp_user, smtp_pass)
                server.sendmail(from_email, clean_recipients, msg.as_string())
        else:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=6) as server:
                server.ehlo()
                if smtp_encryption == "starttls" or smtp_port == 587:
                    try:
                        server.starttls()
                        server.ehlo()
                    except Exception:
                        pass
                if smtp_user and smtp_pass:
                    server.login(smtp_user, smtp_pass)
                server.sendmail(from_email, clean_recipients, msg.as_string())
        sent_ok = True
    except Exception as e:
        delivery_status = "logged_local"
        error_detail = str(e)
        logger.info(f"Plesk SMTP stored in outbox log (host={smtp_host}:{smtp_port}): {e}")

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO email_logs (quote_id, recipient, subject, template_type, delivery_status, error_detail, html_body, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                quote_id,
                ", ".join(clean_recipients),
                subject,
                template_type,
                delivery_status,
                error_detail,
                html_body,
                now_str,
            ),
        )
        if quote_id > 0:
            cur.execute(
                "UPDATE quotes SET last_emailed_at = ?, updated_at = ? WHERE id = ?",
                (now_str, now_str, quote_id),
            )

    return sent_ok, (error_detail or f"Delivered via {smtp_host}:{smtp_port}")


def send_quote_notification(quote_data: dict, quote_id: int = 0) -> bool:
    """Sends:
    1) Branded Admin New Contact/Lead Notification to academy staff (`email_quotes`).
    2) Branded Prospect Welcome & First-Class Guide Email to the person who submitted the form.
    """
    site = get_site_settings()
    base_url = settings.BASE_URL.rstrip("/")
    admin_url = f"{base_url}{settings.ADMIN_PATH}?tab=inquiries"

    name = html.escape(str(quote_data.get("name") or "Student"))
    email = html.escape(str(quote_data.get("email") or ""))
    phone = html.escape(str(quote_data.get("phone") or "Not provided"))
    program = html.escape(str(quote_data.get("program_interest") or "Free Introductory Class (Fundamentals)"))
    experience = html.escape(str(quote_data.get("experience_level") or "Brand New Beginner"))
    pref_date = html.escape(str(quote_data.get("preferred_date") or "Flexible / Next Available"))
    message = html.escape(str(quote_data.get("message") or "No additional message provided."))
    source_page = html.escape(str(quote_data.get("source_page") or "/contact"))

    # ------------------------------------------------------------------
    # 1. ADMIN NOTIFICATION EMAIL
    # ------------------------------------------------------------------
    recipients_str = site.get("email_quotes") or settings.EMAIL_QUOTES
    admin_recipients = [r.strip() for r in recipients_str.split(",") if r.strip()]

    admin_subject = f"🥋 New Lead #{quote_id or 'New'}: {quote_data.get('name')} — {quote_data.get('program_interest') or 'Free Intro Class'}"
    admin_body_html = f"""
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color: #18181B; border: 1px solid #27272A; border-radius: 12px; padding: 16px 20px; margin-bottom: 18px;">
      <tr>
        <td style="padding: 6px 0; color: #A1A1AA; width: 150px; font-size: 13px;">Student Name:</td>
        <td style="padding: 6px 0; color: #FFFFFF; font-weight: 800; font-size: 15px;">{name}</td>
      </tr>
      <tr>
        <td style="padding: 6px 0; color: #A1A1AA; font-size: 13px;">Phone / Text:</td>
        <td style="padding: 6px 0; color: #FF4D64; font-weight: 800; font-size: 14px;">
          <a href="tel:{phone}" style="color: #FF4D64; text-decoration: none;">{phone}</a>
          &nbsp;•&nbsp;
          <a href="sms:{phone}" style="color: #38BDF8; text-decoration: underline; font-size: 12px;">Send Text</a>
        </td>
      </tr>
      <tr>
        <td style="padding: 6px 0; color: #A1A1AA; font-size: 13px;">Email Address:</td>
        <td style="padding: 6px 0; color: #FFFFFF; font-size: 14px;">
          <a href="mailto:{email}" style="color: #FFFFFF; text-decoration: underline;">{email}</a>
        </td>
      </tr>
      <tr>
        <td style="padding: 6px 0; color: #A1A1AA; font-size: 13px;">Program Interest:</td>
        <td style="padding: 6px 0; color: #CE1E36; font-weight: 800; font-size: 14px;">{program}</td>
      </tr>
      <tr>
        <td style="padding: 6px 0; color: #A1A1AA; font-size: 13px;">Experience Level:</td>
        <td style="padding: 6px 0; color: #E4E4E7; font-size: 13px;">{experience}</td>
      </tr>
      <tr>
        <td style="padding: 6px 0; color: #A1A1AA; font-size: 13px;">Preferred Day/Time:</td>
        <td style="padding: 6px 0; color: #E4E4E7; font-size: 13px;">{pref_date}</td>
      </tr>
      <tr>
        <td style="padding: 6px 0; color: #A1A1AA; font-size: 13px;">Submitted From:</td>
        <td style="padding: 6px 0; color: #A1A1AA; font-size: 12px;">{source_page} (CRM Status: <strong>New Inquiry</strong>)</td>
      </tr>
    </table>

    <div style="background-color: #09090B; border-left: 4px solid #CE1E36; padding: 14px 18px; border-radius: 8px;">
      <div style="font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.08em; color: #A1A1AA; margin-bottom: 6px;">
        Student Message / Goals:
      </div>
      <div style="color: #FAFAFA; font-size: 14px; white-space: pre-wrap;">{message}</div>
    </div>
    """

    admin_email_html = render_branded_email(
        kicker="New Website Lead Alert",
        headline=f"New Contact / Free Class Request from {name}",
        intro_html="A prospective student just submitted an inquiry on <strong>stpetebjj.com</strong>. You can reply directly to this email or manage their status (Followed Up, Free Class Scheduled, 30-Day Trial, Signed Up) in the Admin CRM.",
        body_html=admin_body_html,
        cta_label="Manage Lead in Admin CRM",
        cta_url=admin_url,
        site=site,
    )

    sent_admin, _ = dispatch_email(
        recipients=admin_recipients,
        subject=admin_subject,
        html_body=admin_email_html,
        template_type="admin_new_inquiry",
        quote_id=quote_id,
        reply_to=str(quote_data.get("email") or ""),
    )

    # ------------------------------------------------------------------
    # 2. PROSPECT AUTO-CONFIRMATION & FIRST-CLASS GUIDE EMAIL
    # ------------------------------------------------------------------
    if site.get("email_auto_reply_enabled", "true").lower() == "true" and quote_data.get("email"):
        student_subject = f"Welcome to St. Pete Brazilian Jiu-Jitsu! Your Free Class & Inquiry Confirmation"
        waiver_url = f"{base_url}{site.get('waiver_url') or '/wp-content/uploads/2017/01/Waiver.pdf'}"
        student_body_html = f"""
        <div style="background-color: #18181B; border: 1px solid #27272A; border-radius: 12px; padding: 18px 20px; margin-bottom: 18px;">
          <div style="font-size: 12px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.08em; color: #FF4D64; margin-bottom: 10px;">
            🥋 What to Know For Your First Class
          </div>
          <ul style="margin: 0; padding-left: 18px; color: #E4E4E7; font-size: 14px; line-height: 1.7;">
            <li><strong>100% Free Loaner Gi Provided:</strong> Just wear comfortable athletic clothes (a t-shirt or rashguard and athletic shorts/sweatpants without zippers). We provide a clean loaner Gi uniform at no charge!</li>
            <li><strong>What to Bring:</strong> Flip-flops or sandals for walking off the mats and a water bottle.</li>
            <li><strong>Arrive 10–15 Minutes Early:</strong> We'll give you a quick tour of the academy, introduce you to Professor Sean Lynch and our coaches, and get you fitted for your loaner Gi.</li>
            <li><strong>Zero Pressure, Ego-Free:</strong> We have no long-term contracts and welcome complete beginners every week.</li>
          </ul>
        </div>

        <div style="background-color: #09090B; border: 1px solid #27272A; border-radius: 12px; padding: 16px 20px;">
          <div style="font-size: 12px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.08em; color: #A1A1AA; margin-bottom: 6px;">
            Your Request Summary
          </div>
          <div style="font-size: 13px; color: #D4D4D8; line-height: 1.6;">
            <strong>Program Interest:</strong> {program}<br />
            <strong>Experience Level:</strong> {experience}<br />
            <strong>Preferred Day/Time:</strong> {pref_date}<br />
            <strong>Academy Waiver:</strong> <a href="{waiver_url}" style="color: #FF4D64; font-weight: 700;">Download Waiver PDF</a>
          </div>
        </div>
        """

        student_email_html = render_branded_email(
            kicker="Inquiry & Free Intro Class Confirmation",
            headline=f"Welcome to St. Pete BJJ, {name}!",
            intro_html=(
                "Thank you for reaching out to <strong>St. Pete Brazilian Jiu-Jitsu</strong>! We have received your request "
                "and a member of our team will follow up with you shortly. For the fastest response, you can also text or call us "
                "anytime at <strong style='color:#FF4D64;'>(727) 619-4255</strong>."
            ),
            body_html=student_body_html,
            cta_label="View Live Class Schedule",
            cta_url=f"{base_url}/brazilian-jiu-jitsu-class-schedule-saint-petersburg-florida-2",
            site=site,
        )

        dispatch_email(
            recipients=[str(quote_data.get("email")).strip()],
            subject=student_subject,
            html_body=student_email_html,
            template_type="prospect_welcome",
            quote_id=quote_id,
            reply_to=site.get("email_contact") or "info@stpetebjj.com",
        )

    return sent_admin


def send_contact_status_email(quote_row: dict, new_status: str, custom_note: str = "") -> tuple[bool, str]:
    """Sends a branded lifecycle email to the student when the Admin updates their status or sends a follow-up."""
    site = get_site_settings()
    base_url = settings.BASE_URL.rstrip("/")
    recipient = (quote_row.get("email") or "").strip()
    if not recipient or "@" not in recipient:
        return False, "Contact does not have a valid email address."

    name = html.escape(str(quote_row.get("name") or "Student"))
    program = html.escape(str(quote_row.get("program_interest") or "Fundamentals Brazilian Jiu-Jitsu"))
    pref_date = html.escape(str(quote_row.get("preferred_date") or "your upcoming session"))
    note_html = ""
    if custom_note and custom_note.strip():
        escaped_note = html.escape(custom_note.strip())
        note_html = f"""
        <div style="background-color: #09090B; border-left: 4px solid #CE1E36; padding: 14px 18px; border-radius: 8px; margin: 16px 0;">
          <div style="font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.08em; color: #FF4D64; margin-bottom: 4px;">
            Note from St. Pete BJJ:
          </div>
          <div style="color: #FFFFFF; font-size: 14px; white-space: pre-wrap;">{escaped_note}</div>
        </div>
        """

    if new_status == "free_class_scheduled":
        subject = f"🥋 Your Free Intro Class at St. Pete BJJ is Scheduled!"
        kicker = "Free Introductory Class Confirmed"
        headline = f"See You on the Mats, {name}!"
        intro = f"We're excited to welcome you to <strong>St. Pete Brazilian Jiu-Jitsu</strong> for your Free Introductory Class ({program})!"
        body = f"""
        {note_html}
        <div style="background-color: #18181B; border: 1px solid #27272A; border-radius: 12px; padding: 18px 20px;">
          <div style="font-size: 13px; color: #E4E4E7; line-height: 1.7;">
            ✅ <strong>Free Loaner Gi Waiting for You:</strong> Wear a comfortable t-shirt/rashguard and athletic shorts/sweatpants.<br />
            ✅ <strong>Arrival:</strong> Please arrive 10–15 minutes early at <strong>5540 Haines Rd N, St. Petersburg, FL 33714</strong>.<br />
            ✅ <strong>Questions or Rescheduling?</strong> Just reply to this email or text us at <strong>(727) 619-4255</strong>.
          </div>
        </div>
        """
        cta_label = "Download Academy Waiver (PDF)"
        cta_url = f"{base_url}{site.get('waiver_url') or '/wp-content/uploads/2017/01/Waiver.pdf'}"

    elif new_status == "trial_active":
        subject = f"🥋 Welcome to Your 30-Day Free Trial at St. Pete BJJ!"
        kicker = "30-Day Free Trial Active"
        headline = f"Great Job on the Mats, {name}!"
        intro = "Welcome to your <strong>30-Day Free Trial</strong> at St. Pete Brazilian Jiu-Jitsu! Our goal over the next 30 days is to help you build confidence, learn core self-defense fundamentals, and feel right at home in our academy."
        body = f"""
        {note_html}
        <div style="background-color: #18181B; border: 1px solid #27272A; border-radius: 12px; padding: 18px 20px;">
          <div style="font-size: 12px; font-weight: 800; text-transform: uppercase; color: #FF4D64; margin-bottom: 8px;">Recommended Classes During Your Trial</div>
          <div style="font-size: 13px; color: #E4E4E7; line-height: 1.7;">
            • <strong>Fundamentals Gi BJJ:</strong> Mon, Wed, Thu at 6:00 PM &amp; Sat at 10:00 AM<br />
            • <strong>Daytime All-Levels Gi:</strong> Mon, Wed, Thu at 11:00 AM<br />
            • <strong>Judo &amp; Takedowns / No-Gi:</strong> Tuesdays starting at 6:00 PM
          </div>
        </div>
        """
        cta_label = "View Full Weekly Schedule"
        cta_url = f"{base_url}/brazilian-jiu-jitsu-class-schedule-saint-petersburg-florida-2"

    elif new_status == "signed_up":
        subject = f"🥋 Welcome to the Team, {name}! Official St. Pete BJJ Member"
        kicker = "Official Academy Welcome"
        headline = f"Welcome to the St. Pete BJJ Family, {name}!"
        intro = "On behalf of <strong>Professor Sean Lynch</strong> and our entire coaching staff, congratulations and welcome aboard as an official member of <strong>St. Pete Brazilian Jiu-Jitsu</strong>!"
        body = f"""
        {note_html}
        <div style="background-color: #18181B; border: 1px solid #27272A; border-radius: 12px; padding: 18px 20px;">
          <div style="font-size: 13px; color: #E4E4E7; line-height: 1.7;">
            Consistency is the secret to Brazilian Jiu-Jitsu. Whether your goal is self-defense, fitness, belt progression, or competition, our professors and coaches are here to support you every step of the way. See you on the mats!
          </div>
        </div>
        """
        cta_label = "Meet Your Professors & Coaches"
        cta_url = f"{base_url}/st-pete-jiu-jitsu-professors"

    else:
        # Default: followed_up or general custom message
        subject = f"Following Up from St. Pete Brazilian Jiu-Jitsu"
        kicker = "Personal Follow-Up"
        headline = f"Hi {name}, Checking In from St. Pete BJJ!"
        intro = f"We wanted to follow up on your interest in <strong>{program}</strong> at St. Pete Brazilian Jiu-Jitsu."
        body = f"""
        {note_html}
        <div style="background-color: #18181B; border: 1px solid #27272A; border-radius: 12px; padding: 18px 20px;">
          <div style="font-size: 13px; color: #E4E4E7; line-height: 1.7;">
            Whenever you're ready to come try your <strong>Free Introductory Class</strong>, we have a clean loaner Gi ready for you at no charge. Just reply to this email or text us at <strong>(727) 619-4255</strong> with the day that works best for you!
          </div>
        </div>
        """
        cta_label = "View Class Schedule"
        cta_url = f"{base_url}/brazilian-jiu-jitsu-class-schedule-saint-petersburg-florida-2"

    html_body = render_branded_email(
        kicker=kicker,
        headline=headline,
        intro_html=intro,
        body_html=body,
        cta_label=cta_label,
        cta_url=cta_url,
        site=site,
    )

    return dispatch_email(
        recipients=[recipient],
        subject=subject,
        html_body=html_body,
        template_type=f"status_{new_status}",
        quote_id=int(quote_row.get("id") or 0),
        reply_to=site.get("email_contact") or "info@stpetebjj.com",
    )


def send_smtp_test_email(recipient_email: str) -> tuple[bool, str]:
    """Sends a branded Plesk SMTP verification email to the specified address."""
    site = get_site_settings()
    base_url = settings.BASE_URL.rstrip("/")
    body_html = f"""
    <div style="background-color: #18181B; border: 1px solid #27272A; border-radius: 12px; padding: 18px 20px;">
      <div style="font-size: 13px; color: #E4E4E7; line-height: 1.7;">
        <strong>SMTP Host:</strong> {html.escape(site.get('smtp_host') or 'localhost')}:{html.escape(site.get('smtp_port') or '587')}<br />
        <strong>Encryption:</strong> {html.escape((site.get('smtp_encryption') or 'starttls').upper())}<br />
        <strong>From Address:</strong> {html.escape(site.get('smtp_from_email') or 'info@stpetebjj.com')}<br />
        <strong>Auto-Reply to Prospects:</strong> {'Enabled' if site.get('email_auto_reply_enabled', 'true') == 'true' else 'Disabled'}
      </div>
    </div>
    """
    html_body = render_branded_email(
        kicker="Plesk SMTP Configuration Test",
        headline="Your Branded Academy Emails Are Ready!",
        intro_html="This is a test of the <strong>St. Pete Brazilian Jiu-Jitsu</strong> branded HTML email system configured for your Plesk SMTP server.",
        body_html=body_html,
        cta_label="Open Admin Console",
        cta_url=f"{base_url}{settings.ADMIN_PATH}?tab=inquiries",
        site=site,
    )
    return dispatch_email(
        recipients=[recipient_email],
        subject="✅ St. Pete BJJ — Branded Plesk SMTP Test Email",
        html_body=html_body,
        template_type="smtp_test",
        quote_id=0,
    )
