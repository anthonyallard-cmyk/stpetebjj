from fastapi import APIRouter, Request, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from app.database import db_cursor
from app.middleware import get_client_ip
from app.services.recaptcha_service import verify_recaptcha
from app.services.email_service import send_quote_notification

router = APIRouter()


class QuoteSubmission(BaseModel):
    name: str
    email: str
    phone: Optional[str] = ""
    program_interest: Optional[str] = "Free Introductory Class (Fundamentals)"
    experience_level: Optional[str] = "Brand New Beginner"
    preferred_date: Optional[str] = ""
    city: Optional[str] = "St. Petersburg"
    state: Optional[str] = "FL"
    zipcode: Optional[str] = ""
    message: Optional[str] = ""
    recaptcha_token: Optional[str] = ""
    website_url: Optional[str] = ""  # Honeypot field


@router.post("/api/quote/submit")
async def submit_quote(payload: QuoteSubmission, request: Request):
    # Honeypot trap
    if payload.website_url and payload.website_url.strip():
        return JSONResponse({"status": "ok", "message": "Thank you! We will be in touch shortly."})

    name = payload.name.strip()
    email = payload.email.strip()
    if not name or not email or "@" not in email:
        return JSONResponse(
            {"status": "error", "detail": "Please provide your name and a valid email address."},
            status_code=400,
        )

    client_ip = get_client_ip(request)
    is_valid, score = await verify_recaptcha(payload.recaptcha_token or "", client_ip)
    if not is_valid:
        return JSONResponse(
            {"status": "error", "detail": "reCAPTCHA verification failed. Please call or text (727) 619-4255."},
            status_code=400,
        )

    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO quotes (
                name, email, phone, program_interest, experience_level,
                preferred_date, city, state, zipcode, message,
                status, ip_address, recaptcha_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new', ?, ?)
            """,
            (
                name,
                email,
                (payload.phone or "").strip(),
                (payload.program_interest or "Free Introductory Class").strip(),
                (payload.experience_level or "Beginner").strip(),
                (payload.preferred_date or "").strip(),
                (payload.city or "St. Petersburg").strip(),
                (payload.state or "FL").strip(),
                (payload.zipcode or "").strip(),
                (payload.message or "").strip(),
                client_ip,
                score,
            ),
        )
        quote_id = cur.lastrowid

    send_quote_notification(payload.model_dump())

    return JSONResponse({
        "status": "ok",
        "quote_id": quote_id,
        "message": "Your Free Class / Inquiry request has been received! Remember: a clean loaner Gi is provided free for your first class. You can also text us anytime at (727) 619-4255.",
    })


@router.get("/api/search/autocomplete")
async def search_autocomplete(q: str = Query("", min_length=1)):
    term = q.strip()
    if not term:
        return JSONResponse({"results": []})

    like_q = f"%{term}%"
    results = []

    with db_cursor() as cur:
        # 1. Search Programs / Classes
        cur.execute(
            """
            SELECT name, url, badge, image, short_desc
            FROM programs
            WHERE status = 1 AND (name LIKE ? OR short_desc LIKE ? OR description LIKE ? OR level LIKE ?)
            ORDER BY sort_order ASC LIMIT 4
            """,
            (like_q, like_q, like_q, like_q),
        )
        for r in cur.fetchall():
            results.append({
                "type": "Program",
                "title": r["name"],
                "subtitle": r["badge"] or "BJJ Program",
                "url": r["url"],
                "image": r["image"] or "/wp-content/uploads/2016/10/st-pete-bjj.jpg",
            })

        # 2. Search Active Academy Instructors (featured = 1)
        cur.execute(
            """
            SELECT name, slug, rank, role, image
            FROM instructors
            WHERE status = 1 AND featured = 1 AND (name LIKE ? OR rank LIKE ? OR role LIKE ? OR bio LIKE ?)
            ORDER BY sort_order ASC LIMIT 4
            """,
            (like_q, like_q, like_q, like_q),
        )
        for r in cur.fetchall():
            results.append({
                "type": "Instructor",
                "title": r["name"],
                "subtitle": f"{r['rank']} • {r['role']}",
                "url": f"/st-pete-jiu-jitsu-professors#{r['slug']}",
                "image": r["image"],
            })

        # 3. Search Memberships & Pricing
        cur.execute(
            """
            SELECT name, price_display, billing_period, badge
            FROM memberships
            WHERE status = 1 AND (name LIKE ? OR description LIKE ? OR price_display LIKE ?)
            ORDER BY sort_order ASC LIMIT 3
            """,
            (like_q, like_q, like_q),
        )
        for r in cur.fetchall():
            results.append({
                "type": "Membership",
                "title": f"{r['name']} ({r['price_display']}{r['billing_period'] or ''})",
                "subtitle": r["badge"] or "Month-to-Month • No Contract",
                "url": "/membership",
                "image": "/static/images/logo-circle.png",
            })

        # 4. Search Galleries
        cur.execute(
            """
            SELECT title, slug, cover_image, photo_count
            FROM galleries
            WHERE status = 1 AND (title LIKE ? OR description LIKE ?)
            ORDER BY sort_order ASC LIMIT 3
            """,
            (like_q, like_q),
        )
        for r in cur.fetchall():
            results.append({
                "type": "Photo Gallery",
                "title": r["title"],
                "subtitle": f"{r['photo_count']} Academy Photos",
                "url": f"/dt_gallery/{r['slug']}",
                "image": r["cover_image"],
            })

        # 5. Search Pages & Blog Posts
        cur.execute(
            """
            SELECT title, slug, category_name, featured_image
            FROM posts
            WHERE status = 1 AND (title LIKE ? OR excerpt LIKE ? OR content LIKE ?)
            ORDER BY published_at DESC LIMIT 3
            """,
            (like_q, like_q, like_q),
        )
        for r in cur.fetchall():
            results.append({
                "type": r["category_name"] or "Mat Corner",
                "title": r["title"],
                "subtitle": "Mat Corner Article",
                "url": f"/{r['slug']}",
                "image": r["featured_image"] or "/wp-content/uploads/2016/10/st-pete-bjj.jpg",
            })

        # 6. Quick Schedule / FAQ keyword matches
        tl = term.lower()
        if any(k in tl for k in ("schedule", "time", "hour", "calendar", "open mat", "monday", "tuesday", "saturday")):
            results.insert(0, {
                "type": "Live Schedule",
                "title": "Brazilian Jiu-Jitsu Class Schedule",
                "subtitle": "Live ZenPlanner Weekly Schedule — St. Petersburg, FL",
                "url": "/brazilian-jiu-jitsu-class-schedule-saint-petersburg-florida-2",
                "image": "/static/images/logo-circle.png",
            })

    return JSONResponse({"results": results[:10]})
