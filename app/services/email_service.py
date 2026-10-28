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

EMAIL_SCENARIO_CATALOG = [
    {
        "key": "prospect_welcome",
        "title": "1. Prospect Welcome & First-Class Guide",
        "recipient_role": "Prospective Student",
        "trigger": "Auto-sent when a visitor submits the Contact / Free Intro Class form",
        "badge": "Auto-Responder",
    },
    {
        "key": "admin_new_inquiry",
        "title": "2. Admin New Lead / Contact Alert",
        "recipient_role": "Academy Admin / Staff",
        "trigger": "Auto-sent to academy staff when any website form or AI Chat lead is submitted",
        "badge": "Staff Alert",
    },
    {
        "key": "private_or_dropin",
        "title": "3. Private Lesson / Visitor Drop-In Confirmation",
        "recipient_role": "Visiting Grappler / Private Student",
        "trigger": "Auto-sent when someone requests Private Lessons, Seminars, or a Drop-In Visit",
        "badge": "Special Request",
    },
    {
        "key": "status_free_class_scheduled",
        "title": "4. Free Intro Class Confirmed",
        "recipient_role": "Prospective Student",
        "trigger": "Sent when Admin sets lead status to 'Free Class Scheduled'",
        "badge": "CRM Pipeline",
    },
    {
        "key": "status_followed_up",
        "title": "5. Personal Coaching Follow-Up",
        "recipient_role": "Prospective Student",
        "trigger": "Sent when Admin sets lead status to 'Followed Up' or sends a custom note",
        "badge": "CRM Pipeline",
    },
    {
        "key": "status_trial_active",
        "title": "6. 30-Day Free Trial Activated",
        "recipient_role": "Trial Student",
        "trigger": "Sent when Admin sets lead status to '30-Day Free Trial'",
        "badge": "CRM Pipeline",
    },
    {
        "key": "status_signed_up",
        "title": "7. Official Academy Member Welcome",
        "recipient_role": "New Academy Member",
        "trigger": "Sent when Admin sets lead status to 'Signed Up (Member)'",
        "badge": "CRM Pipeline",
    },
    {
        "key": "admin_password_reset",
        "title": "8. Admin Password Reset Request",
        "recipient_role": "Academy Admin",
        "trigger": "Sent when Admin clicks 'Forgot Password?' on the Admin Login screen",
        "badge": "Account Security",
    },
    {
        "key": "admin_password_changed",
        "title": "9. Admin Password Changed Confirmation",
        "recipient_role": "Academy Admin",
        "trigger": "Sent immediately after the Admin password is reset or updated",
        "badge": "Account Security",
    },
    {
        "key": "admin_security_alert",
        "title": "10. Security & Failed Login Lockout Alert",
        "recipient_role": "Academy Admin",
        "trigger": "Sent when repeated failed login attempts occur on the Admin portal",
        "badge": "Security Alert",
    },
]


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
                      4th Degree Black Belt Professor Sean Lynch &bull; Est. 2006
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
                  &#128205; <a href="{maps_url}" style="color: #F4F4F5; text-decoration: underline;">{address}</a><br />
                  &#128241; Text or Call: <a href="tel:17276194255" style="color: #FF4D64; font-weight: 700; text-decoration: none;">{phone}</a> ({phone_vanity})<br />
                  &#9993; Email: <a href="mailto:{email_contact}" style="color: #F4F4F5; text-decoration: underline;">{email_contact}</a>
                </div>
                <div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid #27272A; font-size: 12px;">
                  <a href="{schedule_url}" style="color: #FF4D64; font-weight: 700; text-decoration: none; margin-right: 14px;">Class Schedule &rarr;</a>
                  <a href="{waiver_url}" style="color: #F4F4F5; font-weight: 600; text-decoration: none; margin-right: 14px;">Download Waiver (PDF) &rarr;</a>
                  <a href="{maps_url}" style="color: #FBBF24; font-weight: 700; text-decoration: none;">&#9733; 5.0 Google Reviews &rarr;</a>
                </div>
              </div>
            </td>
          </tr>

          <!-- Bottom Copyright Bar -->
          <tr>
            <td style="background-color: #09090B; padding: 16px 30px; border-top: 1px solid #27272A; text-align: center; font-size: 11px; color: #71717A;">
              &copy; {datetime.now().year} {site_name} &bull; {address}<br />
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


# =====================================================================
# HTML BUILDERS FOR ALL 10 SYSTEM EMAIL SCENARIOS
# =====================================================================

def build_admin_new_inquiry_email(quote_data: dict, quote_id: int = 0, site: dict | None = None) -> tuple[str, str]:
    if site is None:
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

    subject = f"🥋 New Lead #{quote_id or 'New'}: {quote_data.get('name')} — {quote_data.get('program_interest') or 'Free Intro Class'}"
    body_html = f"""
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color: #18181B; border: 1px solid #27272A; border-radius: 12px; padding: 16px 20px; margin-bottom: 18px;">
      <tr>
        <td style="padding: 6px 0; color: #A1A1AA; width: 150px; font-size: 13px;">Student Name:</td>
        <td style="padding: 6px 0; color: #FFFFFF; font-weight: 800; font-size: 15px;">{name}</td>
      </tr>
      <tr>
        <td style="padding: 6px 0; color: #A1A1AA; font-size: 13px;">Phone / Text:</td>
        <td style="padding: 6px 0; color: #FF4D64; font-weight: 800; font-size: 14px;">
          <a href="tel:{phone}" style="color: #FF4D64; text-decoration: none;">{phone}</a>
          &nbsp;&bull;&nbsp;
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

    html_body = render_branded_email(
        kicker="New Website Lead Alert",
        headline=f"New Contact / Free Class Request from {name}",
        intro_html="A prospective student just submitted an inquiry on <strong>stpetebjj.com</strong>. You can reply directly to this email or manage their status (Followed Up, Free Class Scheduled, 30-Day Trial, Signed Up) in the Admin CRM.",
        body_html=body_html,
        cta_label="Manage Lead in Admin CRM",
        cta_url=admin_url,
        site=site,
    )
    return subject, html_body


def build_prospect_welcome_email(quote_data: dict, site: dict | None = None) -> tuple[str, str, str]:
    """Returns (subject, html_body, template_type). Automatically detects Private Lesson / Visitor Drop-In vs Free Class."""
    if site is None:
        site = get_site_settings()
    base_url = settings.BASE_URL.rstrip("/")
    waiver_url = f"{base_url}{site.get('waiver_url') or '/wp-content/uploads/2017/01/Waiver.pdf'}"

    name = html.escape(str(quote_data.get("name") or "Student"))
    program = html.escape(str(quote_data.get("program_interest") or "Free Introductory Class (Fundamentals)"))
    experience = html.escape(str(quote_data.get("experience_level") or "Brand New Beginner"))
    pref_date = html.escape(str(quote_data.get("preferred_date") or "Flexible / Next Available"))

    prog_lower = program.lower()
    is_special = any(w in prog_lower for w in ("private", "visit", "drop-in", "drop in", "open mat", "seminar"))

    if is_special:
        subject = f"🥋 St. Pete BJJ — Your {quote_data.get('program_interest') or 'Private Lesson / Visitor'} Request"
        body_html = f"""
        <div style="background-color: #18181B; border: 1px solid #27272A; border-radius: 12px; padding: 18px 20px; margin-bottom: 18px;">
          <div style="font-size: 12px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.08em; color: #FF4D64; margin-bottom: 10px;">
            &#129355; Visiting Grapplers &amp; Private Training Info
          </div>
          <ul style="margin: 0; padding-left: 18px; color: #E4E4E7; font-size: 14px; line-height: 1.7;">
            <li><strong>100% Open &amp; Affiliation-Friendly:</strong> We welcome visiting students and travelers from all Brazilian Jiu-Jitsu academies and affiliations.</li>
            <li><strong>Private 1-on-1 Coaching:</strong> Professor Sean Lynch and our black belt instructors offer customized Gi, No-Gi, and Self-Defense private sessions tailored to your schedule.</li>
            <li><strong>Clean Loaner Gi Available:</strong> Traveling without a Gi? Let us know your height/weight and we will have a clean loaner Gi ready for you.</li>
            <li><strong>Academy Waiver:</strong> You can save time by reviewing our <a href="{waiver_url}" style="color: #FF4D64; font-weight: 700;">Academy Waiver PDF</a> prior to arriving.</li>
          </ul>
        </div>

        <div style="background-color: #09090B; border: 1px solid #27272A; border-radius: 12px; padding: 16px 20px;">
          <div style="font-size: 12px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.08em; color: #A1A1AA; margin-bottom: 6px;">
            Your Request Details
          </div>
          <div style="font-size: 13px; color: #D4D4D8; line-height: 1.6;">
            <strong>Request Type:</strong> {program}<br />
            <strong>Current Rank / Experience:</strong> {experience}<br />
            <strong>Requested Day/Time:</strong> {pref_date}
          </div>
        </div>
        """
        html_body = render_branded_email(
            kicker="Private Lesson & Visitor Request",
            headline=f"We've Received Your Request, {name}!",
            intro_html=(
                "Thank you for contacting <strong>St. Pete Brazilian Jiu-Jitsu</strong>! Professor Sean Lynch or one of our coaches "
                "will reach out shortly to confirm your session or drop-in time. For immediate scheduling, text or call us at "
                "<strong style='color:#FF4D64;'>(727) 619-4255</strong>."
            ),
            body_html=body_html,
            cta_label="View Weekly Class Schedule",
            cta_url=f"{base_url}/brazilian-jiu-jitsu-class-schedule-saint-petersburg-florida-2",
            site=site,
        )
        return subject, html_body, "private_or_dropin"

    subject = "Welcome to St. Pete Brazilian Jiu-Jitsu! Your Free Class & Inquiry Confirmation"
    body_html = f"""
    <div style="background-color: #18181B; border: 1px solid #27272A; border-radius: 12px; padding: 18px 20px; margin-bottom: 18px;">
      <div style="font-size: 12px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.08em; color: #FF4D64; margin-bottom: 10px;">
        &#129355; What to Know For Your First Class
      </div>
      <ul style="margin: 0; padding-left: 18px; color: #E4E4E7; font-size: 14px; line-height: 1.7;">
        <li><strong>100% Free Loaner Gi Provided:</strong> Just wear comfortable athletic clothes (a t-shirt or rashguard and athletic shorts/sweatpants without zippers). We provide a clean loaner Gi uniform at no charge!</li>
        <li><strong>What to Bring:</strong> Flip-flops or sandals for walking off the mats and a water bottle.</li>
        <li><strong>Arrive 10&ndash;15 Minutes Early:</strong> We'll give you a quick tour of the academy, introduce you to Professor Sean Lynch and our coaches, and get you fitted for your loaner Gi.</li>
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

    html_body = render_branded_email(
        kicker="Inquiry & Free Intro Class Confirmation",
        headline=f"Welcome to St. Pete BJJ, {name}!",
        intro_html=(
            "Thank you for reaching out to <strong>St. Pete Brazilian Jiu-Jitsu</strong>! We have received your request "
            "and a member of our team will follow up with you shortly. For the fastest response, you can also text or call us "
            "anytime at <strong style='color:#FF4D64;'>(727) 619-4255</strong>."
        ),
        body_html=body_html,
        cta_label="View Live Class Schedule",
        cta_url=f"{base_url}/brazilian-jiu-jitsu-class-schedule-saint-petersburg-florida-2",
        site=site,
    )
    return subject, html_body, "prospect_welcome"


def build_contact_status_email(quote_row: dict, new_status: str, custom_note: str = "", site: dict | None = None) -> tuple[str, str]:
    if site is None:
        site = get_site_settings()
    base_url = settings.BASE_URL.rstrip("/")

    name = html.escape(str(quote_row.get("name") or "Student"))
    program = html.escape(str(quote_row.get("program_interest") or "Fundamentals Brazilian Jiu-Jitsu"))
    pref_date = html.escape(str(quote_row.get("preferred_date") or "your upcoming session"))
    note_html = ""
    if custom_note and custom_note.strip():
        escaped_note = html.escape(custom_note.strip())
        note_html = f"""
        <div style="background-color: #09090B; border-left: 4px solid #CE1E36; padding: 14px 18px; border-radius: 8px; margin: 16px 0;">
          <div style="font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.08em; color: #FF4D64; margin-bottom: 4px;">
            Personal Note from St. Pete BJJ:
          </div>
          <div style="color: #FFFFFF; font-size: 14px; white-space: pre-wrap;">{escaped_note}</div>
        </div>
        """

    if new_status == "free_class_scheduled":
        subject = "🥋 Your Free Intro Class at St. Pete BJJ is Scheduled!"
        kicker = "Free Introductory Class Confirmed"
        headline = f"See You on the Mats, {name}!"
        intro = f"We're excited to welcome you to <strong>St. Pete Brazilian Jiu-Jitsu</strong> for your Free Introductory Class ({program} &mdash; <strong>{pref_date}</strong>)!"
        body = f"""
        {note_html}
        <div style="background-color: #18181B; border: 1px solid #27272A; border-radius: 12px; padding: 18px 20px;">
          <div style="font-size: 13px; color: #E4E4E7; line-height: 1.7;">
            &#9989; <strong>Free Loaner Gi Waiting for You:</strong> Wear a comfortable t-shirt/rashguard and athletic shorts/sweatpants.<br />
            &#9989; <strong>Arrival:</strong> Please arrive 10&ndash;15 minutes early at <strong>5540 Haines Rd N, St. Petersburg, FL 33714</strong>.<br />
            &#9989; <strong>Questions or Rescheduling?</strong> Just reply to this email or text us at <strong>(727) 619-4255</strong>.
          </div>
        </div>
        """
        cta_label = "Download Academy Waiver (PDF)"
        cta_url = f"{base_url}{site.get('waiver_url') or '/wp-content/uploads/2017/01/Waiver.pdf'}"

    elif new_status == "trial_active":
        subject = "🥋 Welcome to Your 30-Day Free Trial at St. Pete BJJ!"
        kicker = "30-Day Free Trial Active"
        headline = f"Great Job on the Mats, {name}!"
        intro = "Welcome to your <strong>30-Day Free Trial</strong> at St. Pete Brazilian Jiu-Jitsu! Our goal over the next 30 days is to help you build confidence, learn core self-defense fundamentals, and feel right at home in our academy."
        body = f"""
        {note_html}
        <div style="background-color: #18181B; border: 1px solid #27272A; border-radius: 12px; padding: 18px 20px;">
          <div style="font-size: 12px; font-weight: 800; text-transform: uppercase; color: #FF4D64; margin-bottom: 8px;">Recommended Classes During Your Trial</div>
          <div style="font-size: 13px; color: #E4E4E7; line-height: 1.7;">
            &bull; <strong>Fundamentals Gi BJJ:</strong> Mon, Wed, Thu at 6:00 PM &amp; Sat at 10:00 AM<br />
            &bull; <strong>Daytime All-Levels Gi:</strong> Mon, Wed, Thu at 11:00 AM<br />
            &bull; <strong>Judo &amp; Takedowns / No-Gi:</strong> Tuesdays starting at 6:00 PM
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
        subject = "Following Up from St. Pete Brazilian Jiu-Jitsu"
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
    return subject, html_body


def build_admin_password_reset_email(username: str, reset_url: str, ip_address: str = "127.0.0.1", site: dict | None = None) -> tuple[str, str]:
    if site is None:
        site = get_site_settings()
    now_str = datetime.now().strftime("%b %d, %Y at %I:%M %p")
    safe_user = html.escape(username)
    safe_ip = html.escape(ip_address)
    safe_url = html.escape(reset_url)

    subject = "🔐 Admin Password Reset Request — St. Pete Brazilian Jiu-Jitsu"
    body_html = f"""
    <div style="background-color: #18181B; border: 1px solid #27272A; border-radius: 12px; padding: 18px 20px; margin-bottom: 18px;">
      <div style="font-size: 12px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.08em; color: #FF4D64; margin-bottom: 8px;">
        Password Reset Request Details
      </div>
      <div style="font-size: 13px; color: #E4E4E7; line-height: 1.7;">
        <strong>Admin Account:</strong> {safe_user}<br />
        <strong>Requested At:</strong> {now_str}<br />
        <strong>Requesting IP Address:</strong> <code style="color: #FBBF24;">{safe_ip}</code><br />
        <strong>Link Expiration:</strong> 60 minutes (Single-Use Token)
      </div>
    </div>

    <div style="background-color: #09090B; border-left: 4px solid #F59E0B; padding: 14px 18px; border-radius: 8px; font-size: 13px; color: #D4D4D8;">
      <strong>Did not request this reset?</strong> You can safely ignore this email. Your current admin password will remain unchanged and nobody can access your account without clicking the secure link below.
      <div style="margin-top: 8px; font-size: 11px; color: #71717A; word-break: break-all;">
        Direct URL: {safe_url}
      </div>
    </div>
    """

    html_body = render_branded_email(
        kicker="Admin Account Security",
        headline="Reset Your Admin Console Password",
        intro_html=f"We received a request to reset the password for the <strong>{safe_user}</strong> administrator account on <strong>stpetebjj.com</strong>. Click the button below within the next 60 minutes to choose a new password:",
        body_html=body_html,
        cta_label="Reset Admin Password Now",
        cta_url=reset_url,
        site=site,
    )
    return subject, html_body


def build_admin_password_changed_email(username: str, ip_address: str = "127.0.0.1", site: dict | None = None) -> tuple[str, str]:
    if site is None:
        site = get_site_settings()
    base_url = settings.BASE_URL.rstrip("/")
    now_str = datetime.now().strftime("%b %d, %Y at %I:%M %p")
    safe_user = html.escape(username)
    safe_ip = html.escape(ip_address)

    subject = "✅ Admin Password Updated — St. Pete Brazilian Jiu-Jitsu"
    body_html = f"""
    <div style="background-color: #18181B; border: 1px solid #27272A; border-radius: 12px; padding: 18px 20px;">
      <div style="font-size: 12px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.08em; color: #34D399; margin-bottom: 8px;">
        Security Audit Confirmation
      </div>
      <div style="font-size: 13px; color: #E4E4E7; line-height: 1.7;">
        <strong>Admin Account:</strong> {safe_user}<br />
        <strong>Action:</strong> Password Successfully Changed<br />
        <strong>Timestamp:</strong> {now_str}<br />
        <strong>IP Address:</strong> <code style="color: #34D399;">{safe_ip}</code>
      </div>
    </div>
    """

    html_body = render_branded_email(
        kicker="Security Audit Notification",
        headline="Your Admin Password Was Updated",
        intro_html=f"This is an automated security confirmation that the password for administrator account <strong>{safe_user}</strong> on <strong>stpetebjj.com</strong> has been changed.",
        body_html=body_html,
        cta_label="Sign In to Admin Console",
        cta_url=f"{base_url}{settings.ADMIN_PATH}/login",
        site=site,
    )
    return subject, html_body


def build_admin_security_alert_email(event_title: str, ip_address: str, details: str, site: dict | None = None) -> tuple[str, str]:
    if site is None:
        site = get_site_settings()
    base_url = settings.BASE_URL.rstrip("/")
    now_str = datetime.now().strftime("%b %d, %Y at %I:%M %p")
    safe_title = html.escape(event_title)
    safe_ip = html.escape(ip_address)
    safe_details = html.escape(details)

    subject = f"🚨 Security Alert: {event_title} ({ip_address})"
    body_html = f"""
    <div style="background-color: #18181B; border: 1px solid #EF4444; border-radius: 12px; padding: 18px 20px;">
      <div style="font-size: 12px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.08em; color: #F87171; margin-bottom: 8px;">
        &#128680; Security &amp; Firewall Event Logged
      </div>
      <div style="font-size: 13px; color: #E4E4E7; line-height: 1.7;">
        <strong>Event Type:</strong> {safe_title}<br />
        <strong>Source IP Address:</strong> <code style="color: #F87171;">{safe_ip}</code><br />
        <strong>Timestamp:</strong> {now_str}<br />
        <strong>Details:</strong> {safe_details}
      </div>
    </div>
    """

    html_body = render_branded_email(
        kicker="Automated Security Shield",
        headline=f"Security Event Detected: {safe_title}",
        intro_html="Our automated security shield detected repeated failed login attempts or suspicious activity on <strong>stpetebjj.com</strong> and logged the IP address below:",
        body_html=body_html,
        cta_label="Review Security & IP Blacklist",
        cta_url=f"{base_url}{settings.ADMIN_PATH}?tab=security",
        site=site,
    )
    return subject, html_body


# =====================================================================
# HIGH-LEVEL DISPATCH FUNCTIONS
# =====================================================================

def send_quote_notification(quote_data: dict, quote_id: int = 0) -> bool:
    """Sends:
    1) Branded Admin New Contact/Lead Notification to academy staff (`email_quotes`).
    2) Branded Prospect Welcome & First-Class Guide (or Private/Visitor Info) Email to the student.
    """
    site = get_site_settings()
    recipients_str = site.get("email_quotes") or settings.EMAIL_QUOTES
    admin_recipients = [r.strip() for r in recipients_str.split(",") if r.strip()]

    admin_subject, admin_email_html = build_admin_new_inquiry_email(quote_data, quote_id=quote_id, site=site)
    sent_admin, _ = dispatch_email(
        recipients=admin_recipients,
        subject=admin_subject,
        html_body=admin_email_html,
        template_type="admin_new_inquiry",
        quote_id=quote_id,
        reply_to=str(quote_data.get("email") or ""),
    )

    if site.get("email_auto_reply_enabled", "true").lower() == "true" and quote_data.get("email"):
        student_subject, student_email_html, tpl_type = build_prospect_welcome_email(quote_data, site=site)
        dispatch_email(
            recipients=[str(quote_data.get("email")).strip()],
            subject=student_subject,
            html_body=student_email_html,
            template_type=tpl_type,
            quote_id=quote_id,
            reply_to=site.get("email_contact") or "info@stpetebjj.com",
        )

    return sent_admin


def send_contact_status_email(quote_row: dict, new_status: str, custom_note: str = "") -> tuple[bool, str]:
    """Sends a branded lifecycle email to the student when the Admin updates their status or sends a follow-up."""
    site = get_site_settings()
    recipient = (quote_row.get("email") or "").strip()
    if not recipient or "@" not in recipient:
        return False, "Contact does not have a valid email address."

    subject, html_body = build_contact_status_email(
        quote_row=quote_row,
        new_status=new_status,
        custom_note=custom_note,
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


def send_admin_password_reset_email(username: str, recipient_email: str, reset_url: str, ip_address: str = "127.0.0.1") -> tuple[bool, str]:
    site = get_site_settings()
    subject, html_body = build_admin_password_reset_email(username, reset_url, ip_address, site=site)
    return dispatch_email(
        recipients=[recipient_email],
        subject=subject,
        html_body=html_body,
        template_type="admin_password_reset",
        quote_id=0,
    )


def send_admin_password_changed_email(username: str, recipient_email: str, ip_address: str = "127.0.0.1") -> tuple[bool, str]:
    site = get_site_settings()
    subject, html_body = build_admin_password_changed_email(username, ip_address, site=site)
    return dispatch_email(
        recipients=[recipient_email],
        subject=subject,
        html_body=html_body,
        template_type="admin_password_changed",
        quote_id=0,
    )


def send_admin_security_alert_email(event_title: str, ip_address: str, details: str) -> tuple[bool, str]:
    site = get_site_settings()
    recipients_str = site.get("email_quotes") or site.get("email_contact") or settings.EMAIL_QUOTES
    admin_recipients = [r.strip() for r in recipients_str.split(",") if r.strip()]
    subject, html_body = build_admin_security_alert_email(event_title, ip_address, details, site=site)
    return dispatch_email(
        recipients=admin_recipients,
        subject=subject,
        html_body=html_body,
        template_type="admin_security_alert",
        quote_id=0,
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


def render_scenario_preview(scenario_key: str) -> tuple[str, str]:
    """Generates a realistic preview (subject, html_body) for any of the 10 system email scenarios."""
    site = get_site_settings()
    base_url = settings.BASE_URL.rstrip("/")
    sample_quote = {
        "id": 108,
        "name": "Marcus Rivera",
        "email": "marcus.rivera@example.com",
        "phone": "(727) 555-0194",
        "program_interest": "Free Introductory Class (Fundamentals)",
        "experience_level": "Brand New Beginner",
        "preferred_date": "Monday 6:00 PM Fundamentals",
        "message": "Looking to start Brazilian Jiu-Jitsu for self-defense and fitness. Do I need to buy a Gi before my first class?",
        "source_page": "/contact",
    }

    if scenario_key == "prospect_welcome":
        subj, html_body, _ = build_prospect_welcome_email(sample_quote, site=site)
        return subj, html_body

    if scenario_key == "admin_new_inquiry":
        return build_admin_new_inquiry_email(sample_quote, quote_id=108, site=site)

    if scenario_key == "private_or_dropin":
        special_quote = dict(sample_quote)
        special_quote["program_interest"] = "Private Lessons (Gi or No-Gi) & Visiting Drop-In"
        special_quote["experience_level"] = "Blue Belt (Visiting from Out of Town)"
        special_quote["preferred_date"] = "Thursday 11:00 AM or Private 1-on-1 Session"
        subj, html_body, _ = build_prospect_welcome_email(special_quote, site=site)
        return subj, html_body

    if scenario_key == "status_free_class_scheduled":
        return build_contact_status_email(
            sample_quote,
            "free_class_scheduled",
            custom_note="Hi Marcus! We have you confirmed for Monday at 6:00 PM. Ask for Coach Sean or Coach AJ when you walk in — we'll have an A2 loaner Gi ready for you!",
            site=site,
        )

    if scenario_key == "status_followed_up":
        return build_contact_status_email(
            sample_quote,
            "followed_up",
            custom_note="Great speaking with you earlier! Let us know if Monday at 6:00 PM or Wednesday at 6:00 PM works better for your Free Intro Class.",
            site=site,
        )

    if scenario_key == "status_trial_active":
        return build_contact_status_email(
            sample_quote,
            "trial_active",
            custom_note="Awesome job in your first class tonight! Your 30-Day Free Trial is now active.",
            site=site,
        )

    if scenario_key == "status_signed_up":
        return build_contact_status_email(
            sample_quote,
            "signed_up",
            custom_note="Welcome to the St. Pete BJJ team! Let us know if you have any questions at all.",
            site=site,
        )

    if scenario_key == "admin_password_reset":
        reset_url = f"{base_url}{settings.ADMIN_PATH}/reset-password?token=spbjj-reset-9f8a7b6c5d4e3f2a1b"
        return build_admin_password_reset_email("admin", reset_url, ip_address="72.184.112.45", site=site)

    if scenario_key == "admin_password_changed":
        return build_admin_password_changed_email("admin", ip_address="72.184.112.45", site=site)

    if scenario_key == "admin_security_alert":
        return build_admin_security_alert_email(
            "5 Failed Admin Login Attempts",
            ip_address="185.220.101.42",
            details="5 consecutive failed login attempts for username 'admin'. Temporary rate-limit warning triggered.",
            site=site,
        )

    # Default fallback
    subj, html_body, _ = build_prospect_welcome_email(sample_quote, site=site)
    return subj, html_body
