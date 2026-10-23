import hashlib
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from app.config import settings, TEMPLATES_DIR, BACKUPS_DIR
from app.database import db_cursor, get_site_settings, update_site_setting
from app.services.backup_service import create_backup_archive, list_backups

router = APIRouter()
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
ADMIN_BASE = settings.ADMIN_PATH


def is_authenticated(request: Request) -> bool:
    return request.session.get("admin_authenticated") is True


def verify_password(plain_pw: str, stored_hash: str) -> bool:
    if ":" not in stored_hash:
        return False
    salt, h = stored_hash.split(":", 1)
    calc = hashlib.sha256((salt + plain_pw).encode("utf-8")).hexdigest()
    return calc == h


@router.get(f"{ADMIN_BASE}/login", response_class=HTMLResponse)
async def admin_login_page(request: Request, error: str = ""):
    if is_authenticated(request):
        return RedirectResponse(url=ADMIN_BASE, status_code=302)
    return templates.TemplateResponse(
        request,
        "admin/login.html",
        {"admin_path": ADMIN_BASE, "error": error, "site": get_site_settings()},
    )


@router.post(f"{ADMIN_BASE}/login")
async def admin_login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    with db_cursor() as cur:
        cur.execute(
            "SELECT id, username, password_hash FROM users WHERE username = ? AND is_active = 1",
            (username.strip(),),
        )
        user = cur.fetchone()
        if user and verify_password(password, user["password_hash"]):
            request.session["admin_authenticated"] = True
            request.session["admin_user"] = user["username"]
            return RedirectResponse(url=ADMIN_BASE, status_code=302)

    return templates.TemplateResponse(
        request,
        "admin/login.html",
        {
            "admin_path": ADMIN_BASE,
            "error": "Invalid username or password.",
            "site": get_site_settings(),
        },
        status_code=401,
    )


@router.get(f"{ADMIN_BASE}/logout")
async def admin_logout(request: Request):
    request.session.clear()
    return RedirectResponse(url=f"{ADMIN_BASE}/login", status_code=302)


@router.get(ADMIN_BASE, response_class=HTMLResponse)
async def admin_dashboard(request: Request, tab: str = "inquiries", msg: str = ""):
    if not is_authenticated(request):
        return RedirectResponse(url=f"{ADMIN_BASE}/login", status_code=302)

    with db_cursor() as cur:
        cur.execute("SELECT * FROM quotes ORDER BY created_at DESC LIMIT 100")
        quotes = [dict(r) for r in cur.fetchall()]

        cur.execute("SELECT * FROM programs ORDER BY sort_order ASC")
        programs = [dict(r) for r in cur.fetchall()]

        cur.execute("SELECT * FROM memberships ORDER BY sort_order ASC")
        memberships = [dict(r) for r in cur.fetchall()]

        cur.execute("SELECT * FROM instructors ORDER BY sort_order ASC")
        instructors = [dict(r) for r in cur.fetchall()]

        cur.execute("SELECT * FROM galleries ORDER BY sort_order ASC")
        galleries = [dict(r) for r in cur.fetchall()]

        cur.execute("SELECT * FROM posts ORDER BY published_at DESC")
        posts = [dict(r) for r in cur.fetchall()]

        cur.execute("SELECT * FROM security_events ORDER BY created_at DESC LIMIT 60")
        security_events = [dict(r) for r in cur.fetchall()]

        cur.execute("SELECT COUNT(*) AS c FROM quotes WHERE status = 'new'")
        new_quotes_count = cur.fetchone()["c"]

    backups = list_backups()

    return templates.TemplateResponse(
        request,
        "admin/dashboard.html",
        {
            "admin_path": ADMIN_BASE,
            "active_tab": tab,
            "msg": msg,
            "site": get_site_settings(),
            "quotes": quotes,
            "new_quotes_count": new_quotes_count,
            "programs": programs,
            "memberships": memberships,
            "instructors": instructors,
            "galleries": galleries,
            "posts": posts,
            "security_events": security_events,
            "backups": backups,
        },
    )


@router.post(f"{ADMIN_BASE}/quotes/status")
async def admin_update_quote(
    request: Request,
    quote_id: int = Form(...),
    status: str = Form(...),
    internal_notes: str = Form(""),
):
    if not is_authenticated(request):
        return RedirectResponse(url=f"{ADMIN_BASE}/login", status_code=302)
    with db_cursor() as cur:
        cur.execute(
            "UPDATE quotes SET status = ?, internal_notes = ? WHERE id = ?",
            (status, internal_notes.strip(), quote_id),
        )
    return RedirectResponse(url=f"{ADMIN_BASE}?tab=inquiries&msg=Inquiry+Updated", status_code=302)


@router.post(f"{ADMIN_BASE}/memberships/update")
async def admin_update_membership(
    request: Request,
    membership_id: int = Form(...),
    name: str = Form(...),
    price_display: str = Form(...),
    billing_period: str = Form(""),
    badge: str = Form(""),
    description: str = Form(""),
    external_url: str = Form(""),
):
    if not is_authenticated(request):
        return RedirectResponse(url=f"{ADMIN_BASE}/login", status_code=302)
    with db_cursor() as cur:
        cur.execute(
            """
            UPDATE memberships
            SET name = ?, price_display = ?, billing_period = ?, badge = ?, description = ?, external_url = ?
            WHERE id = ?
            """,
            (name.strip(), price_display.strip(), billing_period.strip(), badge.strip(), description.strip(), external_url.strip(), membership_id),
        )
    return RedirectResponse(url=f"{ADMIN_BASE}?tab=memberships&msg=Membership+Rate+Updated", status_code=302)


@router.post(f"{ADMIN_BASE}/settings/update")
async def admin_update_settings(
    request: Request,
    phone: str = Form("(727) 619-4255"),
    email_contact: str = Form("info@stpetebjj.com"),
    email_quotes: str = Form("info@stpetebjj.com, camaraogb@gmail.com"),
    address: str = Form("5540 Haines Rd N, St. Petersburg, FL 33714"),
    geo_block_enabled: str = Form("0"),
    geo_allowed_countries: str = Form("US, CA, MX, PR"),
    geo_allow_search_bots: str = Form("0"),
    waf_block_scanners: str = Form("0"),
    geo_ip_whitelist: str = Form(""),
    geo_ip_blacklist: str = Form(""),
    recaptcha_site_key: str = Form(""),
    recaptcha_secret_key: str = Form(""),
    stripe_enabled: str = Form("0"),
    stripe_publishable_key: str = Form(""),
    stripe_secret_key: str = Form(""),
):
    if not is_authenticated(request):
        return RedirectResponse(url=f"{ADMIN_BASE}/login", status_code=302)

    updates = {
        "phone": phone.strip(),
        "email_contact": email_contact.strip(),
        "email_quotes": email_quotes.strip(),
        "address": address.strip(),
        "geo_block_enabled": "1" if geo_block_enabled == "1" else "0",
        "geo_allowed_countries": geo_allowed_countries.strip(),
        "geo_allow_search_bots": "1" if geo_allow_search_bots == "1" else "0",
        "waf_block_scanners": "1" if waf_block_scanners == "1" else "0",
        "geo_ip_whitelist": geo_ip_whitelist.strip(),
        "geo_ip_blacklist": geo_ip_blacklist.strip(),
        "recaptcha_site_key": recaptcha_site_key.strip(),
        "recaptcha_secret_key": recaptcha_secret_key.strip(),
        "stripe_enabled": "1" if stripe_enabled == "1" else "0",
        "stripe_publishable_key": stripe_publishable_key.strip(),
        "stripe_secret_key": stripe_secret_key.strip(),
    }
    for k, v in updates.items():
        update_site_setting(k, v)

    return RedirectResponse(url=f"{ADMIN_BASE}?tab=security&msg=Settings+Saved", status_code=302)


@router.post(f"{ADMIN_BASE}/backups/create")
async def admin_create_backup(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url=f"{ADMIN_BASE}/login", status_code=302)
    info = create_backup_archive()
    return RedirectResponse(
        url=f"{ADMIN_BASE}?tab=backups&msg=Backup+Created:+{info['filename']}",
        status_code=302,
    )


@router.get(f"{ADMIN_BASE}/backups/download/{{filename}}")
async def admin_download_backup(request: Request, filename: str):
    if not is_authenticated(request):
        return RedirectResponse(url=f"{ADMIN_BASE}/login", status_code=302)
    safe_name = filename.replace("/", "").replace("\\", "")
    fp = BACKUPS_DIR / safe_name
    if not fp.exists():
        return RedirectResponse(url=f"{ADMIN_BASE}?tab=backups", status_code=302)
    return FileResponse(path=str(fp), filename=safe_name, media_type="application/zip")
