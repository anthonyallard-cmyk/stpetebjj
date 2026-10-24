import json
from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.config import settings, TEMPLATES_DIR
from app.database import db_cursor, get_site_settings, get_social_links
from app.routers.sitemap import get_all_public_urls

router = APIRouter()
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def get_common_context(request: Request) -> dict:
    site = get_site_settings()
    with db_cursor() as cur:
        cur.execute("SELECT * FROM programs WHERE status = 1 ORDER BY sort_order ASC")
        programs = [dict(r) for r in cur.fetchall()]
        cur.execute("SELECT * FROM faqs WHERE status = 1 ORDER BY sort_order ASC")
        faqs = [dict(r) for r in cur.fetchall()]
    is_admin = False
    try:
        is_admin = request.session.get("admin_authenticated") is True
    except Exception:
        pass
    return {
        "request": request,
        "site": site,
        "social_links": get_social_links(site),
        "is_admin": is_admin,
        "admin_path": settings.ADMIN_PATH,
        "settings": settings,
        "nav_programs": programs,
        "faqs": faqs,
        "current_path": request.url.path,
    }


def load_memberships() -> list[dict]:
    with db_cursor() as cur:
        cur.execute("SELECT * FROM memberships WHERE status = 1 ORDER BY sort_order ASC")
        rows = []
        for r in cur.fetchall():
            d = dict(r)
            try:
                d["features"] = json.loads(d.get("features_json") or "[]")
            except Exception:
                d["features"] = []
            rows.append(d)
        return rows


@router.get("/", response_class=HTMLResponse)
async def home_page(request: Request):
    ctx = get_common_context(request)
    with db_cursor() as cur:
        cur.execute("SELECT * FROM instructors WHERE status = 1 AND featured = 1 ORDER BY sort_order ASC")
        instructors = [dict(r) for r in cur.fetchall()]

        cur.execute("SELECT * FROM galleries WHERE status = 1 ORDER BY sort_order ASC LIMIT 6")
        galleries = [dict(r) for r in cur.fetchall()]

        cur.execute("SELECT * FROM posts WHERE status = 1 ORDER BY published_at DESC LIMIT 3")
        recent_posts = [dict(r) for r in cur.fetchall()]

    ctx.update({
        "meta_title": "St. Pete Brazilian Jiu-Jitsu | Premier BJJ, No-Gi & Self-Defense Academy in St. Petersburg, FL",
        "meta_description": "Welcome to St. Pete Brazilian Jiu-Jitsu! Train authentic Gi & No-Gi BJJ, Judo Takedowns, and Self-Defense in St. Petersburg, FL under 4th Degree Black Belt Professor Sean Lynch. First class is FREE!",
        "instructors": instructors,
        "memberships": load_memberships(),
        "galleries": galleries,
        "recent_posts": recent_posts,
    })
    return templates.TemplateResponse(request, "index.html", ctx)


@router.get("/brazilian-jiu-jitsu-class-schedule-saint-petersburg-florida-2", response_class=HTMLResponse)
@router.get("/upcoming-schedule", response_class=HTMLResponse)
async def schedule_page(request: Request):
    ctx = get_common_context(request)
    is_upcoming = request.url.path == "/upcoming-schedule"
    ctx.update({
        "page_heading": "Upcoming Class Schedule" if is_upcoming else "Our Brazilian Jiu-Jitsu Class Schedule — Saint Petersburg, Florida",
        "meta_title": (
            "Upcoming Class Schedule | St. Pete Brazilian Jiu-Jitsu"
            if is_upcoming
            else "Our Brazilian Jiu-Jitsu Class Schedule - Saint Petersburg Florida | St. Pete BJJ"
        ),
        "meta_description": "Live weekly class schedule for St. Pete Brazilian Jiu-Jitsu in St. Petersburg, FL. Fundamentals, Advanced BJJ, No-Gi Submission Grappling, Judo Takedowns, and Open Mat. First class is FREE!",
    })
    return templates.TemplateResponse(request, "schedule.html", ctx)


@router.get("/membership", response_class=HTMLResponse)
@router.get("/memberships", response_class=HTMLResponse)
async def membership_page(request: Request):
    ctx = get_common_context(request)
    is_plural = request.url.path == "/memberships"
    ctx.update({
        "page_heading": "Memberships & Online Registration" if is_plural else "Jiu-Jitsu Membership & Transparent Rates",
        "is_memberships_widget_page": is_plural,
        "meta_title": (
            "Memberships | St. Pete Brazilian Jiu-Jitsu"
            if is_plural
            else "Jiu-Jitsu Membership & Rates | St. Pete Brazilian Jiu-Jitsu"
        ),
        "meta_description": "Your first introductory class is always free! Transparent month-to-month BJJ membership rates ($130/mo Unlimited, $110/mo Juniors, $700 6-Month Unlimited, $180 10-Class Package, $20 Drop-In) with no contracts.",
        "memberships": load_memberships(),
    })
    return templates.TemplateResponse(request, "membership.html", ctx)


@router.get("/st-pete-jiu-jitsu-professors", response_class=HTMLResponse)
@router.get("/staff", response_class=HTMLResponse)
@router.get("/dt_team", response_class=HTMLResponse)
@router.get("/dt_team_category/{cat_slug}", response_class=HTMLResponse)
async def instructors_page(request: Request, cat_slug: str = ""):
    ctx = get_common_context(request)
    with db_cursor() as cur:
        cur.execute("SELECT * FROM instructors WHERE status = 1 AND featured = 1 ORDER BY sort_order ASC")
        instructors = [dict(r) for r in cur.fetchall()]
    is_staff = request.url.path == "/staff"
    ctx.update({
        "page_heading": "Our Coaching Team" if is_staff else "Instructors",
        "meta_title": "Instructors | St. Pete Brazilian Jiu-Jitsu",
        "meta_description": "Meet the instructors at St. Pete Brazilian Jiu-Jitsu: 4th Degree Black Belt Sean Lynch, Danny Watson, Shane Dunn, Brian Travis, Neldo 'JR' Angeles, Prentice Gerald 'Jerry' Outlaw Jr., and Rodrigo 'Manilha' Guimaraes.",
        "instructors": instructors,
    })
    return templates.TemplateResponse(request, "instructors.html", ctx)


@router.get("/lineage", response_class=HTMLResponse)
@router.get("/dt_team/professor-eduardo-veio-de-lima", response_class=HTMLResponse)
async def lineage_page(request: Request):
    ctx = get_common_context(request)
    with db_cursor() as cur:
        cur.execute("SELECT * FROM lineage_entries WHERE status = 1 ORDER BY sort_order ASC, id ASC")
        lineage_entries = [dict(r) for r in cur.fetchall()]
        cur.execute("SELECT * FROM instructors WHERE slug = 'professor-eduardo-veio-de-lima'")
        row = cur.fetchone()
        eduardo = dict(row) if row else {}
        cur.execute("SELECT * FROM instructors WHERE slug = 'sean-lynch'")
        sean_row = cur.fetchone()
        sean = dict(sean_row) if sean_row else {}

    ctx.update({
        "lineage_entries": lineage_entries,
        "eduardo": eduardo,
        "sean": sean,
        "meta_title": 'Our Lineage: Mitsuyo Maeda → Carlos Gracie → Carlos Gracie Jr. → Eduardo "Veio" de Lima → Sean Lynch | St. Pete BJJ',
        "meta_description": 'Explore the direct Brazilian Jiu-Jitsu lineage of St. Pete BJJ: from Mitsuyo Maeda and Carlos Gracie Sr. to Carlos Gracie Jr., 6th Degree Black Belt Professor Eduardo "Veio" de Lima, and 4th Degree Black Belt Professor Sean Lynch.',
    })
    return templates.TemplateResponse(request, "lineage.html", ctx)


@router.get("/dt_team/{slug}", response_class=HTMLResponse)
async def instructor_detail_page(request: Request, slug: str):
    if slug == "professor-eduardo-veio-de-lima":
        return await lineage_page(request)
    ctx = get_common_context(request)
    with db_cursor() as cur:
        cur.execute("SELECT * FROM instructors WHERE slug = ? AND status = 1", (slug,))
        row = cur.fetchone()
        if not row:
            return RedirectResponse(url="/st-pete-jiu-jitsu-professors", status_code=302)
        instructor = dict(row)
        cur.execute("SELECT * FROM instructors WHERE status = 1 AND featured = 1 ORDER BY sort_order ASC")
        all_instructors = [dict(r) for r in cur.fetchall()]

    ctx.update({
        "instructor": instructor,
        "all_instructors": all_instructors,
        "meta_title": f"{instructor['name']} — {instructor['rank']} | St. Pete Brazilian Jiu-Jitsu",
        "meta_description": f"Learn about {instructor['name']} ({instructor['rank']}), {instructor['role']} at St. Pete Brazilian Jiu-Jitsu in St. Petersburg, FL.",
    })
    return templates.TemplateResponse(request, "instructor_detail.html", ctx)


@router.get("/st-pete-bjj-photo-galleries", response_class=HTMLResponse)
@router.get("/dt_gallery", response_class=HTMLResponse)
@router.get("/dt_gallery_category/{cat_slug}", response_class=HTMLResponse)
async def galleries_page(request: Request, cat_slug: str = ""):
    ctx = get_common_context(request)
    with db_cursor() as cur:
        if cat_slug:
            cur.execute("SELECT * FROM galleries WHERE status = 1 AND category_slug = ? ORDER BY sort_order ASC", (cat_slug,))
            galleries = [dict(r) for r in cur.fetchall()]
            if not galleries:
                cur.execute("SELECT * FROM galleries WHERE status = 1 ORDER BY sort_order ASC")
                galleries = [dict(r) for r in cur.fetchall()]
        else:
            cur.execute("SELECT * FROM galleries WHERE status = 1 ORDER BY sort_order ASC")
            galleries = [dict(r) for r in cur.fetchall()]

        cur.execute("""
            SELECT gp.*, g.title AS gallery_title, g.slug AS gallery_slug
            FROM gallery_photos gp
            JOIN galleries g ON g.id = gp.gallery_id
            ORDER BY g.sort_order ASC, gp.sort_order ASC
        """)
        all_photos = [dict(r) for r in cur.fetchall()]

    ctx.update({
        "galleries": galleries,
        "all_photos": all_photos,
        "active_category": cat_slug,
        "meta_title": "St. Pete BJJ - Photo Galleries | Academy Training, Seminars & Promotions",
        "meta_description": "Browse 70+ authentic photos from Gi & No-Gi training, belt promotions, seminars, women's BJJ, and team camaraderie at St. Pete Brazilian Jiu-Jitsu.",
    })
    return templates.TemplateResponse(request, "galleries.html", ctx)


@router.get("/dt_gallery/{slug}", response_class=HTMLResponse)
async def gallery_detail_page(request: Request, slug: str):
    ctx = get_common_context(request)
    with db_cursor() as cur:
        cur.execute("SELECT * FROM galleries WHERE slug = ? AND status = 1", (slug,))
        row = cur.fetchone()
        if not row:
            return RedirectResponse(url="/st-pete-bjj-photo-galleries", status_code=302)
        gallery = dict(row)
        cur.execute("SELECT * FROM gallery_photos WHERE gallery_id = ? ORDER BY sort_order ASC", (gallery["id"],))
        photos = [dict(r) for r in cur.fetchall()]
        cur.execute("SELECT * FROM galleries WHERE status = 1 ORDER BY sort_order ASC")
        all_galleries = [dict(r) for r in cur.fetchall()]

    ctx.update({
        "gallery": gallery,
        "photos": photos,
        "all_galleries": all_galleries,
        "meta_title": f"{gallery['title']} — Photo Gallery | St. Pete Brazilian Jiu-Jitsu",
        "meta_description": gallery["description"],
    })
    return templates.TemplateResponse(request, "gallery_detail.html", ctx)


@router.get("/fundamentals-classes", response_class=HTMLResponse)
@router.get("/advanced-classes", response_class=HTMLResponse)
async def program_detail_page(request: Request):
    ctx = get_common_context(request)
    slug = request.url.path.lstrip("/")
    with db_cursor() as cur:
        cur.execute("SELECT * FROM programs WHERE slug = ? AND status = 1", (slug,))
        row = cur.fetchone()
        program = dict(row) if row else ctx["nav_programs"][0]
        cur.execute("SELECT * FROM instructors WHERE status = 1 ORDER BY sort_order ASC LIMIT 4")
        instructors = [dict(r) for r in cur.fetchall()]

    ctx.update({
        "program": program,
        "instructors": instructors,
        "meta_title": f"{program['name']} | St. Pete Brazilian Jiu-Jitsu — St. Petersburg, FL",
        "meta_description": program["short_desc"],
    })
    return templates.TemplateResponse(request, "program_detail.html", ctx)


@router.get("/news", response_class=HTMLResponse)
@router.get("/category/{cat_slug}", response_class=HTMLResponse)
@router.get("/tag/{tag_slug}", response_class=HTMLResponse)
@router.get("/author/{author_slug}", response_class=HTMLResponse)
@router.get("/{year:int}/{month:int}", response_class=HTMLResponse)
async def news_archive_page(
    request: Request,
    cat_slug: str = "",
    tag_slug: str = "",
    author_slug: str = "",
    year: int = 0,
    month: int = 0,
):
    ctx = get_common_context(request)
    with db_cursor() as cur:
        if cat_slug and cat_slug != "uncategorized":
            cur.execute("SELECT * FROM posts WHERE status = 1 AND category_slug = ? ORDER BY published_at DESC", (cat_slug,))
            posts = [dict(r) for r in cur.fetchall()]
            if not posts:
                cur.execute("SELECT * FROM posts WHERE status = 1 ORDER BY published_at DESC")
                posts = [dict(r) for r in cur.fetchall()]
        elif year and month:
            ym_prefix = f"{year:04d}-{month:02d}"
            cur.execute("SELECT * FROM posts WHERE status = 1 AND published_at LIKE ? ORDER BY published_at DESC", (f"{ym_prefix}%",))
            posts = [dict(r) for r in cur.fetchall()]
            if not posts:
                cur.execute("SELECT * FROM posts WHERE status = 1 ORDER BY published_at DESC")
                posts = [dict(r) for r in cur.fetchall()]
        else:
            cur.execute("SELECT * FROM posts WHERE status = 1 ORDER BY published_at DESC")
            posts = [dict(r) for r in cur.fetchall()]

    heading = "Mat Corner — Academy News, Seminars & Belt Promotions"
    if cat_slug == "promotions":
        heading = "Mat Corner — Belt Promotions"
    elif cat_slug == "eventsgatherings":
        heading = "Mat Corner — Events, Seminars & Gatherings"
    elif year and month:
        heading = f"Mat Corner Archive — {year}-{month:02d}"

    ctx.update({
        "posts": posts,
        "page_heading": heading,
        "active_category": cat_slug,
        "meta_title": f"{heading} | St. Pete Brazilian Jiu-Jitsu",
        "meta_description": "Read the latest belt promotions, guest black belt seminar recaps, tournament results, and academy announcements from St. Pete Brazilian Jiu-Jitsu.",
    })
    return templates.TemplateResponse(request, "news.html", ctx)


@router.get("/contact", response_class=HTMLResponse)
async def contact_page(request: Request):
    ctx = get_common_context(request)
    ctx.update({
        "meta_title": "Contact St. Pete BJJ & Book Your Free Class | 5540 Haines Rd N, St. Petersburg, FL",
        "meta_description": "Contact St. Pete Brazilian Jiu-Jitsu at 5540 Haines Rd N, St. Petersburg, FL 33714. Text (preferred) or call (727) 619-4255, or register online for your free introductory class!",
    })
    return templates.TemplateResponse(request, "contact.html", ctx)


@router.get("/qa", response_class=HTMLResponse)
async def faq_page(request: Request):
    ctx = get_common_context(request)
    ctx.update({
        "meta_title": "Frequently Asked Questions (FAQ) | St. Pete Brazilian Jiu-Jitsu",
        "meta_description": "Answers to frequently asked questions about starting Brazilian Jiu-Jitsu in St. Petersburg, FL: free loaner gi, what to expect in your first class, transparent month-to-month rates, and teens ages 12+.",
    })
    return templates.TemplateResponse(request, "faq.html", ctx)


@router.get("/sitemap", response_class=HTMLResponse)
async def html_sitemap_page(request: Request):
    ctx = get_common_context(request)
    ctx.update({
        "urls": get_all_public_urls(),
        "meta_title": "HTML Sitemap | St. Pete Brazilian Jiu-Jitsu",
        "meta_description": "Complete index of pages, class schedules, programs, instructors, photo galleries, and Mat Corner articles on St. Pete Brazilian Jiu-Jitsu.",
    })
    return templates.TemplateResponse(request, "sitemap_html.html", ctx)


@router.get("/search", response_class=HTMLResponse)
async def search_page(request: Request, q: str = Query("")):
    ctx = get_common_context(request)
    term = q.strip()
    like_q = f"%{term}%" if term else "%"
    with db_cursor() as cur:
        cur.execute(
            "SELECT * FROM programs WHERE status = 1 AND (name LIKE ? OR description LIKE ?) ORDER BY sort_order ASC",
            (like_q, like_q),
        )
        matched_programs = [dict(r) for r in cur.fetchall()]

        cur.execute(
            "SELECT * FROM instructors WHERE status = 1 AND (name LIKE ? OR bio LIKE ? OR rank LIKE ?) ORDER BY sort_order ASC",
            (like_q, like_q, like_q),
        )
        matched_instructors = [dict(r) for r in cur.fetchall()]

        cur.execute(
            "SELECT * FROM posts WHERE status = 1 AND (title LIKE ? OR content LIKE ?) ORDER BY published_at DESC",
            (like_q, like_q),
        )
        matched_posts = [dict(r) for r in cur.fetchall()]

    ctx.update({
        "query": term,
        "matched_programs": matched_programs,
        "matched_instructors": matched_instructors,
        "matched_posts": matched_posts,
        "meta_title": f"Search Results for '{term}' | St. Pete Brazilian Jiu-Jitsu" if term else "Search | St. Pete Brazilian Jiu-Jitsu",
        "meta_description": "Search classes, black belt instructors, memberships, and articles at St. Pete Brazilian Jiu-Jitsu.",
    })
    return templates.TemplateResponse(request, "search.html", ctx)


@router.get("/{post_slug}", response_class=HTMLResponse)
async def post_or_catchall_page(request: Request, post_slug: str):
    ctx = get_common_context(request)
    with db_cursor() as cur:
        cur.execute("SELECT * FROM posts WHERE slug = ? AND status = 1", (post_slug,))
        row = cur.fetchone()
        if row:
            post = dict(row)
            cur.execute("SELECT * FROM posts WHERE status = 1 AND slug != ? ORDER BY published_at DESC LIMIT 4", (post_slug,))
            related_posts = [dict(r) for r in cur.fetchall()]
            ctx.update({
                "post": post,
                "related_posts": related_posts,
                "meta_title": f"{post['title']} | Mat Corner — St. Pete Brazilian Jiu-Jitsu",
                "meta_description": post["excerpt"] or post["title"],
            })
            return templates.TemplateResponse(request, "post_detail.html", ctx)

        # Check if it's a program slug accessed at root
        cur.execute("SELECT * FROM programs WHERE slug = ? AND status = 1", (post_slug,))
        prog_row = cur.fetchone()
        if prog_row:
            program = dict(prog_row)
            cur.execute("SELECT * FROM instructors WHERE status = 1 AND featured = 1 ORDER BY sort_order ASC LIMIT 4")
            instructors = [dict(r) for r in cur.fetchall()]
            ctx.update({
                "program": program,
                "instructors": instructors,
                "meta_title": f"{program['name']} | St. Pete Brazilian Jiu-Jitsu — St. Petersburg, FL",
                "meta_description": program["short_desc"],
            })
            return templates.TemplateResponse(request, "program_detail.html", ctx)

        # Check if it's a custom page in the pages table
        cur.execute("SELECT * FROM pages WHERE slug = ? AND status = 1", (post_slug,))
        page_row = cur.fetchone()
        if page_row:
            custom_page = dict(page_row)
            ctx.update({
                "custom_page": custom_page,
                "meta_title": custom_page.get("meta_title") or f"{custom_page['title']} | St. Pete Brazilian Jiu-Jitsu",
                "meta_description": custom_page.get("meta_description") or custom_page["title"],
            })
            return templates.TemplateResponse(request, "page_custom.html", ctx)

        # Check if it's a gallery slug accessed at root
        cur.execute("SELECT slug FROM galleries WHERE slug = ? AND status = 1", (post_slug,))
        if cur.fetchone():
            return RedirectResponse(url=f"/dt_gallery/{post_slug}", status_code=301)

        # Check if it's an instructor slug accessed at root
        cur.execute("SELECT slug FROM instructors WHERE slug = ? AND status = 1", (post_slug,))
        if cur.fetchone():
            return RedirectResponse(url=f"/dt_team/{post_slug}", status_code=301)

    ctx.update({
        "meta_title": "Page Not Found | St. Pete Brazilian Jiu-Jitsu",
        "meta_description": "Explore Brazilian Jiu-Jitsu classes, live schedules, and memberships at St. Pete BJJ in St. Petersburg, FL.",
    })
    return templates.TemplateResponse(request, "404.html", ctx, status_code=404)
