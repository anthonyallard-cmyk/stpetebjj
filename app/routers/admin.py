import hashlib
import json
import re
import time
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from app.config import settings, TEMPLATES_DIR, BACKUPS_DIR, UPLOADS_DIR
from app.database import db_cursor, get_site_settings, update_site_setting, get_social_links
from app.services.backup_service import create_backup_archive, list_backups
from app.services.ai_chat import fetch_compatible_models, PROVIDER_LABELS, PROVIDER_MODELS_CATALOG
from app.services.email_service import (
    CRM_STATUS_OPTIONS,
    CRM_STATUS_LABELS,
    send_contact_status_email,
    send_quote_notification,
    send_smtp_test_email,
)

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


def slugify(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9\s-]", "", text.lower()).strip()
    s = re.sub(r"[\s_-]+", "-", s)
    return s or f"item-{int(time.time())}"


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


# =====================================================================
# DRAG-AND-DROP IMAGE & FILE UPLOAD API
# =====================================================================
@router.post(f"{ADMIN_BASE}/upload")
async def admin_upload_file(request: Request, file: UploadFile = File(...)):
    if not is_authenticated(request):
        return JSONResponse({"ok": False, "error": "Unauthorized"}, status_code=401)

    orig_name = file.filename or "upload.jpg"
    ext = Path(orig_name).suffix.lower()
    allowed_exts = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg", ".pdf", ".ico"}
    if ext not in allowed_exts:
        return JSONResponse({"ok": False, "error": f"Unsupported file type: {ext}"}, status_code=400)

    stem = slugify(Path(orig_name).stem)[:48]
    timestamp = int(time.time() * 1000)
    safe_filename = f"{stem}-{timestamp}{ext}"

    admin_upload_dir = UPLOADS_DIR / "admin"
    admin_upload_dir.mkdir(parents=True, exist_ok=True)
    dest_path = admin_upload_dir / safe_filename

    content = await file.read()
    dest_path.write_bytes(content)

    public_url = f"/wp-content/uploads/admin/{safe_filename}"
    return JSONResponse({
        "ok": True,
        "url": public_url,
        "filename": safe_filename,
        "size_kb": round(len(content) / 1024, 1),
    })


# =====================================================================
# MAIN ADMIN DASHBOARD
# =====================================================================
@router.get(ADMIN_BASE, response_class=HTMLResponse)
async def admin_dashboard(request: Request, tab: str = "instructors", msg: str = "", status_filter: str = "all"):
    if not is_authenticated(request):
        return RedirectResponse(url=f"{ADMIN_BASE}/login", status_code=302)

    site = get_site_settings()
    try:
        extra_socials = json.loads(site.get("extra_socials_json") or "[]")
        if not isinstance(extra_socials, list):
            extra_socials = []
    except Exception:
        extra_socials = []

    with db_cursor() as cur:
        if status_filter and status_filter != "all":
            cur.execute("SELECT * FROM quotes WHERE status = ? ORDER BY created_at DESC LIMIT 150", (status_filter,))
        else:
            cur.execute("SELECT * FROM quotes ORDER BY created_at DESC LIMIT 150")
        quotes = [dict(r) for r in cur.fetchall()]

        cur.execute("SELECT status, COUNT(*) AS cnt FROM quotes GROUP BY status")
        raw_counts = {r["status"]: r["cnt"] for r in cur.fetchall()}
        crm_status_counts = {code: raw_counts.get(code, 0) for code, _, _ in CRM_STATUS_OPTIONS}
        crm_status_counts["all"] = sum(raw_counts.values())

        cur.execute("SELECT * FROM email_logs ORDER BY id DESC LIMIT 40")
        email_logs = [dict(r) for r in cur.fetchall()]

        cur.execute("SELECT * FROM programs ORDER BY sort_order ASC, id ASC")
        programs = [dict(r) for r in cur.fetchall()]

        cur.execute("SELECT * FROM memberships ORDER BY sort_order ASC, id ASC")
        memberships = [dict(r) for r in cur.fetchall()]

        cur.execute("SELECT * FROM instructors ORDER BY featured DESC, sort_order ASC, id ASC")
        instructors = [dict(r) for r in cur.fetchall()]

        cur.execute("SELECT * FROM galleries ORDER BY sort_order ASC, id ASC")
        galleries = [dict(r) for r in cur.fetchall()]
        for g in galleries:
            cur.execute("SELECT * FROM gallery_photos WHERE gallery_id = ? ORDER BY sort_order ASC, id ASC", (g["id"],))
            g["photos"] = [dict(p) for p in cur.fetchall()]

        cur.execute("SELECT * FROM posts ORDER BY published_at DESC, id DESC")
        posts = [dict(r) for r in cur.fetchall()]

        cur.execute("SELECT * FROM pages ORDER BY id ASC")
        pages = [dict(r) for r in cur.fetchall()]

        cur.execute("SELECT * FROM lineage_entries ORDER BY sort_order ASC, id ASC")
        lineage_entries = [dict(r) for r in cur.fetchall()]

        cur.execute("SELECT * FROM faqs ORDER BY sort_order ASC, id ASC")
        faqs = [dict(r) for r in cur.fetchall()]

        cur.execute("SELECT * FROM security_events ORDER BY created_at DESC LIMIT 60")
        security_events = [dict(r) for r in cur.fetchall()]

        cur.execute("SELECT COUNT(*) AS c FROM quotes WHERE status = 'new'")
        new_quotes_count = cur.fetchone()["c"]

        cur.execute("SELECT * FROM ai_chat_sessions ORDER BY updated_at DESC LIMIT 30")
        ai_sessions = [dict(r) for r in cur.fetchall()]
        for s in ai_sessions:
            cur.execute("SELECT role, content, flagged, created_at FROM ai_chat_messages WHERE session_id = ? ORDER BY id ASC", (s["session_id"],))
            s["messages"] = [dict(m) for m in cur.fetchall()]

    # List recent uploaded files in /wp-content/uploads/admin
    admin_upload_dir = UPLOADS_DIR / "admin"
    admin_upload_dir.mkdir(parents=True, exist_ok=True)
    uploaded_files = []
    for p in sorted(admin_upload_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)[:40]:
        if p.is_file():
            uploaded_files.append({
                "filename": p.name,
                "url": f"/wp-content/uploads/admin/{p.name}",
                "size_kb": round(p.stat().st_size / 1024, 1),
            })

    backups = list_backups()
    current_ai_provider = (site.get("ai_provider") or "gemini").strip().lower()
    ai_initial_models = PROVIDER_MODELS_CATALOG.get(current_ai_provider, PROVIDER_MODELS_CATALOG["gemini"])

    return templates.TemplateResponse(
        request,
        "admin/dashboard.html",
        {
            "admin_path": ADMIN_BASE,
            "active_tab": tab,
            "msg": msg,
            "status_filter": status_filter,
            "crm_statuses": CRM_STATUS_OPTIONS,
            "crm_status_labels": CRM_STATUS_LABELS,
            "crm_status_counts": crm_status_counts,
            "email_logs": email_logs,
            "site": site,
            "extra_socials": extra_socials,
            "social_links": get_social_links(site),
            "quotes": quotes,
            "new_quotes_count": new_quotes_count,
            "programs": programs,
            "memberships": memberships,
            "instructors": instructors,
            "galleries": galleries,
            "posts": posts,
            "pages": pages,
            "lineage_entries": lineage_entries,
            "faqs": faqs,
            "uploaded_files": uploaded_files,
            "security_events": security_events,
            "backups": backups,
            "ai_sessions": ai_sessions,
            "ai_providers": PROVIDER_LABELS,
            "ai_models_catalog": PROVIDER_MODELS_CATALOG,
            "ai_initial_models": ai_initial_models,
        },
    )


# =====================================================================
# INQUIRIES & CRM LEAD PIPELINE CRUD + BRANDED EMAILS
# =====================================================================
@router.post(f"{ADMIN_BASE}/quotes/status")
async def admin_update_quote(
    request: Request,
    quote_id: int = Form(...),
    status: str = Form(...),
    internal_notes: str = Form(""),
    assigned_to: str = Form(""),
    follow_up_date: str = Form(""),
    preferred_date: str = Form(""),
    send_status_email: str = Form("0"),
    custom_email_note: str = Form(""),
):
    if not is_authenticated(request):
        return RedirectResponse(url=f"{ADMIN_BASE}/login", status_code=302)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    quote_row = None
    with db_cursor() as cur:
        cur.execute(
            """
            UPDATE quotes
            SET status = ?, internal_notes = ?, assigned_to = ?, follow_up_date = ?,
                preferred_date = COALESCE(NULLIF(?, ''), preferred_date),
                updated_at = ?
            WHERE id = ?
            """,
            (
                status.strip(),
                internal_notes.strip(),
                assigned_to.strip(),
                follow_up_date.strip(),
                preferred_date.strip(),
                now_str,
                quote_id,
            ),
        )
        cur.execute("SELECT * FROM quotes WHERE id = ?", (quote_id,))
        row = cur.fetchone()
        if row:
            quote_row = dict(row)

    status_label = CRM_STATUS_LABELS.get(status, status)
    msg_text = f"Contact+Updated+to+{status_label.replace(' ', '+')}"

    if send_status_email == "1" and quote_row:
        sent_ok, _ = send_contact_status_email(
            quote_row=quote_row,
            new_status=status.strip(),
            custom_note=custom_email_note.strip(),
        )
        if sent_ok:
            msg_text += "+%26+Branded+Email+Sent+via+SMTP"
        else:
            msg_text += "+%26+Branded+Email+Logged+to+Outbox"

    return RedirectResponse(url=f"{ADMIN_BASE}?tab=inquiries&msg={msg_text}", status_code=302)


@router.post(f"{ADMIN_BASE}/quotes/add")
async def admin_add_quote(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(""),
    program_interest: str = Form("Free Introductory Class (Fundamentals)"),
    experience_level: str = Form("Brand New Beginner"),
    preferred_date: str = Form(""),
    status: str = Form("new"),
    assigned_to: str = Form("Professor Sean"),
    internal_notes: str = Form(""),
    send_welcome: str = Form("1"),
):
    if not is_authenticated(request):
        return RedirectResponse(url=f"{ADMIN_BASE}/login", status_code=302)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO quotes (
                name, email, phone, program_interest, experience_level,
                preferred_date, status, assigned_to, internal_notes,
                source_page, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Admin Walk-In / Phone', ?)
            """,
            (
                name.strip(),
                email.strip(),
                phone.strip(),
                program_interest.strip(),
                experience_level.strip(),
                preferred_date.strip(),
                status.strip(),
                assigned_to.strip(),
                internal_notes.strip(),
                now_str,
            ),
        )
        quote_id = cur.lastrowid

    if send_welcome == "1":
        send_quote_notification(
            {
                "name": name.strip(),
                "email": email.strip(),
                "phone": phone.strip(),
                "program_interest": program_interest.strip(),
                "experience_level": experience_level.strip(),
                "preferred_date": preferred_date.strip(),
                "message": internal_notes.strip() or "Added via Admin CRM.",
                "source_page": "Admin CRM",
            },
            quote_id=quote_id or 0,
        )

    return RedirectResponse(url=f"{ADMIN_BASE}?tab=inquiries&msg=New+Contact+Added+to+CRM", status_code=302)


@router.post(f"{ADMIN_BASE}/smtp/save")
async def admin_save_smtp_settings(
    request: Request,
    smtp_host: str = Form("localhost"),
    smtp_port: str = Form("587"),
    smtp_encryption: str = Form("starttls"),
    smtp_user: str = Form(""),
    smtp_pass: str = Form(""),
    smtp_from_email: str = Form("info@stpetebjj.com"),
    smtp_from_name: str = Form("St. Pete Brazilian Jiu-Jitsu"),
    email_quotes: str = Form("info@stpetebjj.com, camaraogb@gmail.com"),
    email_auto_reply_enabled: str = Form("true"),
):
    if not is_authenticated(request):
        return RedirectResponse(url=f"{ADMIN_BASE}/login", status_code=302)

    update_site_setting("smtp_host", smtp_host.strip() or "localhost")
    update_site_setting("smtp_port", smtp_port.strip() or "587")
    update_site_setting("smtp_encryption", smtp_encryption.strip().lower())
    update_site_setting("smtp_user", smtp_user.strip())
    if not smtp_pass.startswith("••••"):
        update_site_setting("smtp_pass", smtp_pass.strip())
    update_site_setting("smtp_from_email", smtp_from_email.strip() or "info@stpetebjj.com")
    update_site_setting("smtp_from_name", smtp_from_name.strip() or "St. Pete Brazilian Jiu-Jitsu")
    update_site_setting("email_quotes", email_quotes.strip())
    update_site_setting("email_auto_reply_enabled", "true" if email_auto_reply_enabled == "true" else "false")

    return RedirectResponse(url=f"{ADMIN_BASE}?tab=inquiries&msg=Plesk+SMTP+%26+Branded+Email+Settings+Saved", status_code=302)


@router.post(f"{ADMIN_BASE}/smtp/test")
async def admin_test_smtp(request: Request, test_recipient: str = Form(...)):
    if not is_authenticated(request):
        return RedirectResponse(url=f"{ADMIN_BASE}/login", status_code=302)
    sent_ok, detail = send_smtp_test_email(test_recipient.strip())
    if sent_ok:
        msg = f"Branded+Test+Email+Delivered+to+{test_recipient.strip()}"
    else:
        msg = f"Branded+Test+Email+Generated+%26+Saved+in+Outbox+Log+(SMTP:+{detail[:50].replace(' ', '+')})"
    return RedirectResponse(url=f"{ADMIN_BASE}?tab=inquiries&msg={msg}", status_code=302)


@router.get(f"{ADMIN_BASE}/emails/{{email_id}}/preview", response_class=HTMLResponse)
async def admin_preview_email(request: Request, email_id: int):
    if not is_authenticated(request):
        return RedirectResponse(url=f"{ADMIN_BASE}/login", status_code=302)
    with db_cursor() as cur:
        cur.execute("SELECT html_body FROM email_logs WHERE id = ?", (email_id,))
        row = cur.fetchone()
        if not row or not row["html_body"]:
            return HTMLResponse("<p>Email preview not found.</p>", status_code=404)
        return HTMLResponse(row["html_body"])


@router.post(f"{ADMIN_BASE}/quotes/delete")
async def admin_delete_quote(request: Request, quote_id: int = Form(...)):
    if not is_authenticated(request):
        return RedirectResponse(url=f"{ADMIN_BASE}/login", status_code=302)
    with db_cursor() as cur:
        cur.execute("DELETE FROM quotes WHERE id = ?", (quote_id,))
    return RedirectResponse(url=f"{ADMIN_BASE}?tab=inquiries&msg=Inquiry+Deleted", status_code=302)


# =====================================================================
# INSTRUCTORS CRUD (Add, Edit, Upload Photo, Rich Text Bio, Delete)
# =====================================================================
@router.post(f"{ADMIN_BASE}/instructors/save")
async def admin_save_instructor(
    request: Request,
    instructor_id: int = Form(0),
    name: str = Form(...),
    slug: str = Form(""),
    rank: str = Form("Black Belt"),
    role: str = Form("Instructor"),
    lineage: str = Form(""),
    image: str = Form("/static/images/logo-medallion.png"),
    bio: str = Form(""),
    sort_order: int = Form(10),
    featured: str = Form("0"),
):
    if not is_authenticated(request):
        return RedirectResponse(url=f"{ADMIN_BASE}/login", status_code=302)

    clean_slug = slug.strip() or slugify(name)
    is_featured = 1 if featured == "1" else 0
    clean_img = image.strip() or "/static/images/logo-medallion.png"

    with db_cursor() as cur:
        if instructor_id > 0:
            cur.execute(
                """
                UPDATE instructors
                SET name = ?, slug = ?, rank = ?, role = ?, lineage = ?, image = ?, bio = ?, sort_order = ?, featured = ?, status = 1
                WHERE id = ?
                """,
                (name.strip(), clean_slug, rank.strip(), role.strip(), lineage.strip(), clean_img, bio.strip(), sort_order, is_featured, instructor_id),
            )
            action_msg = f"Instructor+{name.strip().replace(' ', '+')}+Updated"
        else:
            cur.execute(
                """
                INSERT INTO instructors (name, slug, rank, role, lineage, bio, image, featured, sort_order, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                """,
                (name.strip(), clean_slug, rank.strip(), role.strip(), lineage.strip(), bio.strip(), clean_img, is_featured, sort_order),
            )
            action_msg = f"New+Instructor+{name.strip().replace(' ', '+')}+Added"

    return RedirectResponse(url=f"{ADMIN_BASE}?tab=instructors&msg={action_msg}", status_code=302)


@router.post(f"{ADMIN_BASE}/instructors/delete")
async def admin_delete_instructor(request: Request, instructor_id: int = Form(...)):
    if not is_authenticated(request):
        return RedirectResponse(url=f"{ADMIN_BASE}/login", status_code=302)
    with db_cursor() as cur:
        cur.execute("DELETE FROM instructors WHERE id = ?", (instructor_id,))
    return RedirectResponse(url=f"{ADMIN_BASE}?tab=instructors&msg=Instructor+Removed", status_code=302)


# =====================================================================
# BLOG / MAT CORNER POSTS CRUD (Add, Edit, Upload Photo, Rich Text, Delete)
# =====================================================================
CATEGORY_LABELS = {
    "promotions": "Belt Promotions",
    "eventsgatherings": "Events & Gatherings",
    "seminars": "BJJ Seminars",
    "uncategorized": "Academy News",
}


@router.post(f"{ADMIN_BASE}/posts/save")
async def admin_save_post(
    request: Request,
    post_id: int = Form(0),
    title: str = Form(...),
    slug: str = Form(""),
    category_slug: str = Form("promotions"),
    published_at: str = Form(""),
    featured_image: str = Form(""),
    excerpt: str = Form(""),
    content: str = Form(""),
    status: str = Form("1"),
):
    if not is_authenticated(request):
        return RedirectResponse(url=f"{ADMIN_BASE}/login", status_code=302)

    clean_slug = slug.strip().strip("/") or slugify(title)
    cat_name = CATEGORY_LABELS.get(category_slug, "Academy News & Promotions")
    pub_date = published_at.strip() or datetime.now().strftime("%Y-%m-%d")
    is_active = 1 if status == "1" else 0
    feat_img = featured_image.strip() or "/wp-content/uploads/2019/02/BJJ_Promotions_2019-65.jpg"
    clean_excerpt = excerpt.strip()
    if not clean_excerpt and content:
        plain = re.sub(r"<[^>]+>", "", content).strip()
        clean_excerpt = plain[:180] + ("..." if len(plain) > 180 else "")

    with db_cursor() as cur:
        if post_id > 0:
            cur.execute(
                """
                UPDATE posts
                SET title = ?, slug = ?, category_slug = ?, category_name = ?, excerpt = ?, content = ?, featured_image = ?, published_at = ?, status = ?
                WHERE id = ?
                """,
                (title.strip(), clean_slug, category_slug, cat_name, clean_excerpt, content.strip(), feat_img, pub_date, is_active, post_id),
            )
            action_msg = "Blog+Post+Updated"
        else:
            cur.execute(
                """
                INSERT INTO posts (title, slug, category_slug, category_name, excerpt, content, featured_image, published_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (title.strip(), clean_slug, category_slug, cat_name, clean_excerpt, content.strip(), feat_img, pub_date, is_active),
            )
            action_msg = "New+Blog+Post+Published"

    return RedirectResponse(url=f"{ADMIN_BASE}?tab=posts&msg={action_msg}", status_code=302)


@router.post(f"{ADMIN_BASE}/posts/delete")
async def admin_delete_post(request: Request, post_id: int = Form(...)):
    if not is_authenticated(request):
        return RedirectResponse(url=f"{ADMIN_BASE}/login", status_code=302)
    with db_cursor() as cur:
        cur.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    return RedirectResponse(url=f"{ADMIN_BASE}?tab=posts&msg=Blog+Post+Deleted", status_code=302)


# =====================================================================
# PAGES, HOMEPAGE AREAS, PROGRAMS, LINEAGE & FAQS CRUD
# =====================================================================
@router.post(f"{ADMIN_BASE}/homepage/save")
async def admin_save_homepage(
    request: Request,
    hero_kicker: str = Form(""),
    hero_headline_html: str = Form(""),
    hero_subtitle_html: str = Form(""),
    hero_slide_1: str = Form(""),
    hero_slide_2: str = Form(""),
    hero_slide_3: str = Form(""),
    hero_slide_4: str = Form(""),
    home_welcome_kicker: str = Form(""),
    home_welcome_heading_html: str = Form(""),
    home_welcome_body_html: str = Form(""),
    home_fundamentals_box_img: str = Form(""),
    home_advanced_box_img: str = Form(""),
    home_showcase_img_1: str = Form(""),
    home_showcase_img_2: str = Form(""),
):
    if not is_authenticated(request):
        return RedirectResponse(url=f"{ADMIN_BASE}/login", status_code=302)

    updates = {
        "hero_kicker": hero_kicker.strip(),
        "hero_headline_html": hero_headline_html.strip(),
        "hero_subtitle_html": hero_subtitle_html.strip(),
        "hero_slide_1": hero_slide_1.strip(),
        "hero_slide_2": hero_slide_2.strip(),
        "hero_slide_3": hero_slide_3.strip(),
        "hero_slide_4": hero_slide_4.strip(),
        "home_welcome_kicker": home_welcome_kicker.strip(),
        "home_welcome_heading_html": home_welcome_heading_html.strip(),
        "home_welcome_body_html": home_welcome_body_html.strip(),
        "home_fundamentals_box_img": home_fundamentals_box_img.strip(),
        "home_advanced_box_img": home_advanced_box_img.strip(),
        "home_showcase_img_1": home_showcase_img_1.strip(),
        "home_showcase_img_2": home_showcase_img_2.strip(),
    }
    for k, v in updates.items():
        if v:
            update_site_setting(k, v)

    return RedirectResponse(url=f"{ADMIN_BASE}?tab=pages&msg=Homepage+Text+and+Images+Updated", status_code=302)


@router.post(f"{ADMIN_BASE}/programs/save")
async def admin_save_program(
    request: Request,
    program_id: int = Form(0),
    name: str = Form(...),
    slug: str = Form(""),
    badge: str = Form("Core Curriculum"),
    level: str = Form("All Levels"),
    short_desc: str = Form(""),
    description: str = Form(""),
    image: str = Form("/static/images/program-fundamentals.jpg"),
    banner_image: str = Form(""),
    sort_order: int = Form(1),
):
    if not is_authenticated(request):
        return RedirectResponse(url=f"{ADMIN_BASE}/login", status_code=302)

    clean_slug = slug.strip().strip("/") or slugify(name)
    url = f"/{clean_slug}"
    with db_cursor() as cur:
        if program_id > 0:
            cur.execute(
                """
                UPDATE programs
                SET name = ?, slug = ?, url = ?, badge = ?, level = ?, short_desc = ?, description = ?, image = ?, banner_image = ?, sort_order = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (name.strip(), clean_slug, url, badge.strip(), level.strip(), short_desc.strip(), description.strip(), image.strip(), banner_image.strip(), sort_order, program_id),
            )
            action_msg = f"Program+{name.strip().replace(' ', '+')}+Updated"
        else:
            cur.execute(
                """
                INSERT INTO programs (name, slug, url, badge, level, short_desc, description, image, banner_image, sort_order, featured, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 1)
                """,
                (name.strip(), clean_slug, url, badge.strip(), level.strip(), short_desc.strip(), description.strip(), image.strip(), banner_image.strip(), sort_order),
            )
            action_msg = f"New+Program+{name.strip().replace(' ', '+')}+Created"

    return RedirectResponse(url=f"{ADMIN_BASE}?tab=pages&msg={action_msg}", status_code=302)


@router.post(f"{ADMIN_BASE}/programs/delete")
async def admin_delete_program(request: Request, program_id: int = Form(...)):
    if not is_authenticated(request):
        return RedirectResponse(url=f"{ADMIN_BASE}/login", status_code=302)
    with db_cursor() as cur:
        cur.execute("DELETE FROM programs WHERE id = ?", (program_id,))
    return RedirectResponse(url=f"{ADMIN_BASE}?tab=pages&msg=Program+Deleted", status_code=302)


@router.post(f"{ADMIN_BASE}/pages/save")
async def admin_save_custom_page(
    request: Request,
    page_id: int = Form(0),
    title: str = Form(...),
    slug: str = Form(""),
    meta_title: str = Form(""),
    meta_description: str = Form(""),
    hero_image: str = Form("/wp-content/uploads/2019/05/Slide-1.jpg"),
    content: str = Form(""),
):
    if not is_authenticated(request):
        return RedirectResponse(url=f"{ADMIN_BASE}/login", status_code=302)

    clean_slug = slug.strip().strip("/") or slugify(title)
    m_title = meta_title.strip() or f"{title.strip()} | St. Pete Brazilian Jiu-Jitsu"
    with db_cursor() as cur:
        if page_id > 0:
            cur.execute(
                """
                UPDATE pages
                SET title = ?, slug = ?, meta_title = ?, meta_description = ?, hero_image = ?, content = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (title.strip(), clean_slug, m_title, meta_description.strip(), hero_image.strip(), content.strip(), page_id),
            )
            action_msg = f"Page+{title.strip().replace(' ', '+')}+Updated"
        else:
            cur.execute(
                """
                INSERT INTO pages (title, slug, meta_title, meta_description, hero_image, content, template, status)
                VALUES (?, ?, ?, ?, ?, ?, 'page_custom.html', 1)
                """,
                (title.strip(), clean_slug, m_title, meta_description.strip(), hero_image.strip(), content.strip()),
            )
            action_msg = f"New+Page+/{clean_slug}+Created"

    return RedirectResponse(url=f"{ADMIN_BASE}?tab=pages&msg={action_msg}", status_code=302)


@router.post(f"{ADMIN_BASE}/pages/delete")
async def admin_delete_custom_page(request: Request, page_id: int = Form(...)):
    if not is_authenticated(request):
        return RedirectResponse(url=f"{ADMIN_BASE}/login", status_code=302)
    with db_cursor() as cur:
        cur.execute("DELETE FROM pages WHERE id = ?", (page_id,))
    return RedirectResponse(url=f"{ADMIN_BASE}?tab=pages&msg=Page+Deleted", status_code=302)


@router.post(f"{ADMIN_BASE}/lineage/save")
async def admin_save_lineage(
    request: Request,
    entry_id: int = Form(0),
    generation_badge: str = Form(...),
    name: str = Form(...),
    image: str = Form("/static/images/logo-medallion.png"),
    bio: str = Form(""),
    sort_order: int = Form(1),
):
    if not is_authenticated(request):
        return RedirectResponse(url=f"{ADMIN_BASE}/login", status_code=302)
    with db_cursor() as cur:
        if entry_id > 0:
            cur.execute(
                "UPDATE lineage_entries SET generation_badge = ?, name = ?, image = ?, bio = ?, sort_order = ? WHERE id = ?",
                (generation_badge.strip(), name.strip(), image.strip(), bio.strip(), sort_order, entry_id),
            )
        else:
            cur.execute(
                "INSERT INTO lineage_entries (generation_badge, name, image, bio, sort_order, status) VALUES (?, ?, ?, ?, ?, 1)",
                (generation_badge.strip(), name.strip(), image.strip(), bio.strip(), sort_order),
            )
    return RedirectResponse(url=f"{ADMIN_BASE}?tab=pages&msg=Lineage+Entry+Saved", status_code=302)


@router.post(f"{ADMIN_BASE}/lineage/delete")
async def admin_delete_lineage(request: Request, entry_id: int = Form(...)):
    if not is_authenticated(request):
        return RedirectResponse(url=f"{ADMIN_BASE}/login", status_code=302)
    with db_cursor() as cur:
        cur.execute("DELETE FROM lineage_entries WHERE id = ?", (entry_id,))
    return RedirectResponse(url=f"{ADMIN_BASE}?tab=pages&msg=Lineage+Entry+Removed", status_code=302)


@router.post(f"{ADMIN_BASE}/faqs/save")
async def admin_save_faq(
    request: Request,
    faq_id: int = Form(0),
    question: str = Form(...),
    answer: str = Form(...),
    sort_order: int = Form(1),
):
    if not is_authenticated(request):
        return RedirectResponse(url=f"{ADMIN_BASE}/login", status_code=302)
    with db_cursor() as cur:
        if faq_id > 0:
            cur.execute(
                "UPDATE faqs SET question = ?, answer = ?, sort_order = ? WHERE id = ?",
                (question.strip(), answer.strip(), sort_order, faq_id),
            )
        else:
            cur.execute(
                "INSERT INTO faqs (question, answer, sort_order, status) VALUES (?, ?, ?, 1)",
                (question.strip(), answer.strip(), sort_order),
            )
    return RedirectResponse(url=f"{ADMIN_BASE}?tab=pages&msg=FAQ+Saved", status_code=302)


@router.post(f"{ADMIN_BASE}/faqs/delete")
async def admin_delete_faq(request: Request, faq_id: int = Form(...)):
    if not is_authenticated(request):
        return RedirectResponse(url=f"{ADMIN_BASE}/login", status_code=302)
    with db_cursor() as cur:
        cur.execute("DELETE FROM faqs WHERE id = ?", (faq_id,))
    return RedirectResponse(url=f"{ADMIN_BASE}?tab=pages&msg=FAQ+Removed", status_code=302)


# =====================================================================
# PHOTO GALLERIES CRUD
# =====================================================================
@router.post(f"{ADMIN_BASE}/galleries/save")
async def admin_save_gallery(
    request: Request,
    gallery_id: int = Form(0),
    title: str = Form(...),
    slug: str = Form(""),
    description: str = Form(""),
    cover_image: str = Form(""),
    sort_order: int = Form(1),
):
    if not is_authenticated(request):
        return RedirectResponse(url=f"{ADMIN_BASE}/login", status_code=302)

    clean_slug = slug.strip().strip("/") or slugify(title)
    with db_cursor() as cur:
        if gallery_id > 0:
            cur.execute(
                "UPDATE galleries SET title = ?, slug = ?, description = ?, cover_image = ?, sort_order = ? WHERE id = ?",
                (title.strip(), clean_slug, description.strip(), cover_image.strip(), sort_order, gallery_id),
            )
        else:
            cur.execute(
                """
                INSERT INTO galleries (title, slug, category_slug, category_name, description, cover_image, photo_count, sort_order, status)
                VALUES (?, ?, 'st-pete-bjj', 'St. Pete BJJ', ?, ?, 0, ?, 1)
                """,
                (title.strip(), clean_slug, description.strip(), cover_image.strip() or "/wp-content/uploads/2019/05/Slide-1.jpg", sort_order),
            )
    return RedirectResponse(url=f"{ADMIN_BASE}?tab=galleries&msg=Gallery+Saved", status_code=302)


@router.post(f"{ADMIN_BASE}/galleries/photos/add")
async def admin_add_gallery_photo(
    request: Request,
    gallery_id: int = Form(...),
    image_url: str = Form(...),
    title: str = Form(""),
):
    if not is_authenticated(request):
        return RedirectResponse(url=f"{ADMIN_BASE}/login", status_code=302)
    urls = [u.strip() for u in image_url.split(",") if u.strip()]
    with db_cursor() as cur:
        for u in urls:
            cur.execute(
                "INSERT INTO gallery_photos (gallery_id, title, image_url, sort_order) VALUES (?, ?, ?, 10)",
                (gallery_id, title.strip() or "St. Pete BJJ Training", u),
            )
        cur.execute("SELECT COUNT(*) AS c FROM gallery_photos WHERE gallery_id = ?", (gallery_id,))
        cnt = cur.fetchone()["c"]
        cur.execute("UPDATE galleries SET photo_count = ? WHERE id = ?", (cnt, gallery_id))
    return RedirectResponse(url=f"{ADMIN_BASE}?tab=galleries&msg=Added+{len(urls)}+Photo(s)+to+Gallery", status_code=302)


@router.post(f"{ADMIN_BASE}/galleries/photos/delete")
async def admin_delete_gallery_photo(
    request: Request,
    photo_id: int = Form(...),
    gallery_id: int = Form(...),
):
    if not is_authenticated(request):
        return RedirectResponse(url=f"{ADMIN_BASE}/login", status_code=302)
    with db_cursor() as cur:
        cur.execute("DELETE FROM gallery_photos WHERE id = ?", (photo_id,))
        cur.execute("SELECT COUNT(*) AS c FROM gallery_photos WHERE gallery_id = ?", (gallery_id,))
        cnt = cur.fetchone()["c"]
        cur.execute("UPDATE galleries SET photo_count = ? WHERE id = ?", (cnt, gallery_id))
    return RedirectResponse(url=f"{ADMIN_BASE}?tab=galleries&msg=Photo+Removed+from+Gallery", status_code=302)


# =====================================================================
# MEMBERSHIPS CRUD
# =====================================================================
@router.post(f"{ADMIN_BASE}/memberships/update")
async def admin_update_membership(
    request: Request,
    membership_id: int = Form(0),
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
        if membership_id > 0:
            cur.execute(
                """
                UPDATE memberships
                SET name = ?, price_display = ?, billing_period = ?, badge = ?, description = ?, external_url = ?
                WHERE id = ?
                """,
                (name.strip(), price_display.strip(), billing_period.strip(), badge.strip(), description.strip(), external_url.strip(), membership_id),
            )
        else:
            cur.execute(
                """
                INSERT INTO memberships (name, slug, category, price_display, billing_period, badge, description, features_json, external_url, featured, sort_order, status)
                VALUES (?, ?, 'membership', ?, ?, ?, ?, '[]', ?, 0, 10, 1)
                """,
                (name.strip(), slugify(name), price_display.strip(), billing_period.strip(), badge.strip(), description.strip(), external_url.strip()),
            )
    return RedirectResponse(url=f"{ADMIN_BASE}?tab=memberships&msg=Membership+Rate+Saved", status_code=302)


@router.post(f"{ADMIN_BASE}/memberships/delete")
async def admin_delete_membership(request: Request, membership_id: int = Form(...)):
    if not is_authenticated(request):
        return RedirectResponse(url=f"{ADMIN_BASE}/login", status_code=302)
    with db_cursor() as cur:
        cur.execute("DELETE FROM memberships WHERE id = ?", (membership_id,))
    return RedirectResponse(url=f"{ADMIN_BASE}?tab=memberships&msg=Membership+Rate+Deleted", status_code=302)


# =====================================================================
# SITE SETTINGS & SOCIAL MEDIA MANAGER
# =====================================================================
@router.post(f"{ADMIN_BASE}/site-settings/save")
async def admin_save_site_settings(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url=f"{ADMIN_BASE}/login", status_code=302)

    form = await request.form()
    keys = [
        "site_name",
        "tagline",
        "phone",
        "phone_vanity",
        "email_contact",
        "email_quotes",
        "address",
        "logo_url",
        "favicon_url",
        "waiver_url",
        "google_maps_url",
        "google_rating",
        "google_reviews_count",
        "facebook_url",
        "instagram_url",
        "youtube_url",
        "tiktok_url",
        "twitter_url",
        "yelp_url",
        "linkedin_url",
        "recaptcha_site_key",
        "recaptcha_secret_key",
        "smtp_host",
        "smtp_port",
        "smtp_encryption",
        "smtp_user",
        "smtp_pass",
        "smtp_from_email",
        "smtp_from_name",
        "email_auto_reply_enabled",
    ]
    for k in keys:
        if k in form:
            val = str(form.get(k) or "").strip()
            if k in ("smtp_pass", "recaptcha_secret_key") and val.startswith("••••"):
                continue
            update_site_setting(k, val)

    # Process dynamic custom social media links (custom_social_name[] and custom_social_url[])
    names = form.getlist("custom_social_name")
    urls = form.getlist("custom_social_url")
    extras = []
    for n, u in zip(names, urls):
        n_clean = str(n).strip()
        u_clean = str(u).strip()
        if n_clean and u_clean:
            extras.append({"name": n_clean, "url": u_clean})
    update_site_setting("extra_socials_json", json.dumps(extras))

    return RedirectResponse(url=f"{ADMIN_BASE}?tab=settings&msg=Site+Settings+%26+Social+Media+Links+Saved", status_code=302)


# =====================================================================
# SECURITY & BACKUPS
# =====================================================================
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

    return RedirectResponse(url=f"{ADMIN_BASE}?tab=security&msg=Security+Settings+Saved", status_code=302)


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


# =====================================================================
# AI CHAT SUPPORT AGENT — PROVIDER / MODEL FETCHER & SETTINGS
# =====================================================================
@router.get(f"{ADMIN_BASE}/ai/models")
async def admin_get_ai_models(request: Request, provider: str = "gemini", api_key: str = ""):
    if not is_authenticated(request):
        return JSONResponse({"ok": False, "error": "Unauthorized"}, status_code=401)
    result = fetch_compatible_models(provider=provider, api_key_override=api_key)
    result["ok"] = True
    return JSONResponse(result)


@router.post(f"{ADMIN_BASE}/ai/models")
async def admin_post_ai_models(request: Request):
    if not is_authenticated(request):
        return JSONResponse({"ok": False, "error": "Unauthorized"}, status_code=401)
    body = await request.json()
    provider = body.get("provider", "gemini")
    api_key = body.get("api_key", "")
    result = fetch_compatible_models(provider=provider, api_key_override=api_key)
    result["ok"] = True
    return JSONResponse(result)


@router.post(f"{ADMIN_BASE}/ai/save")
async def admin_save_ai_settings(
    request: Request,
    ai_enabled: str = Form("false"),
    ai_provider: str = Form("gemini"),
    ai_model: str = Form("gemini-2.5-flash"),
    ai_max_messages_per_session: str = Form("15"),
    ai_max_messages_per_ip_day: str = Form("40"),
    ai_gemini_key: str = Form(""),
    ai_openai_key: str = Form(""),
    ai_anthropic_key: str = Form(""),
    ai_xai_key: str = Form(""),
    ai_deepseek_key: str = Form(""),
    ai_openrouter_key: str = Form(""),
    ai_custom_instructions: str = Form(""),
):
    if not is_authenticated(request):
        return RedirectResponse(url=f"{ADMIN_BASE}/login", status_code=302)

    update_site_setting("ai_enabled", "true" if ai_enabled == "true" else "false")
    update_site_setting("ai_provider", ai_provider.strip().lower())
    update_site_setting("ai_model", ai_model.strip())
    update_site_setting("ai_max_messages_per_session", ai_max_messages_per_session.strip() or "15")
    update_site_setting("ai_max_messages_per_ip_day", ai_max_messages_per_ip_day.strip() or "40")
    update_site_setting("ai_custom_instructions", ai_custom_instructions.strip())

    # Update API keys (allowing blank to clear or keeping existing if masked)
    key_fields = {
        "ai_gemini_key": ai_gemini_key.strip(),
        "ai_openai_key": ai_openai_key.strip(),
        "ai_anthropic_key": ai_anthropic_key.strip(),
        "ai_xai_key": ai_xai_key.strip(),
        "ai_deepseek_key": ai_deepseek_key.strip(),
        "ai_openrouter_key": ai_openrouter_key.strip(),
    }
    for k, val in key_fields.items():
        if not val.startswith("••••"):
            update_site_setting(k, val)

    return RedirectResponse(
        url=f"{ADMIN_BASE}?tab=ai-agent&msg=AI+Chat+Provider+(+{ai_provider.upper()}+/+Model:+{ai_model.strip()}+)+Saved+to+Database",
        status_code=302,
    )


@router.post(f"{ADMIN_BASE}/ai/sessions/unlock")
async def admin_unlock_ai_session(request: Request, session_id: str = Form(...)):
    if not is_authenticated(request):
        return RedirectResponse(url=f"{ADMIN_BASE}/login", status_code=302)
    with db_cursor() as cur:
        cur.execute(
            "UPDATE ai_chat_sessions SET terminated = 0, termination_reason = '', messages_count = 0, updated_at = CURRENT_TIMESTAMP WHERE session_id = ?",
            (session_id,),
        )
    return RedirectResponse(url=f"{ADMIN_BASE}?tab=ai-agent&msg=Chat+Session+Unlocked+%26+Reset", status_code=302)


@router.post(f"{ADMIN_BASE}/ai/sessions/delete")
async def admin_delete_ai_session(request: Request, session_id: str = Form(...)):
    if not is_authenticated(request):
        return RedirectResponse(url=f"{ADMIN_BASE}/login", status_code=302)
    with db_cursor() as cur:
        cur.execute("DELETE FROM ai_chat_messages WHERE session_id = ?", (session_id,))
        cur.execute("DELETE FROM ai_chat_sessions WHERE session_id = ?", (session_id,))
    return RedirectResponse(url=f"{ADMIN_BASE}?tab=ai-agent&msg=Chat+Session+Deleted", status_code=302)

