from datetime import datetime
from fastapi import APIRouter, Request
from fastapi.responses import Response, PlainTextResponse, JSONResponse, FileResponse
from app.config import settings, STATIC_DIR
from app.database import db_cursor

router = APIRouter()


@router.get("/favicon.ico", include_in_schema=False)
async def favicon_ico():
    return FileResponse(str(STATIC_DIR / "favicon.ico"), media_type="image/x-icon")


def get_all_public_urls() -> list[dict]:
    """Returns all canonical URLs on stpetebjj.com for XML and HTML sitemaps."""
    today = datetime.now().strftime("%Y-%m-%d")
    urls = [
        {"loc": "/", "priority": "1.0", "changefreq": "weekly", "lastmod": today, "title": "Home — St. Pete Brazilian Jiu-Jitsu"},
        {"loc": "/brazilian-jiu-jitsu-class-schedule-saint-petersburg-florida-2", "priority": "0.95", "changefreq": "daily", "lastmod": today, "title": "Our Brazilian Jiu-Jitsu Class Schedule — Saint Petersburg, Florida"},
        {"loc": "/upcoming-schedule", "priority": "0.80", "changefreq": "weekly", "lastmod": today, "title": "Upcoming Schedule"},
        {"loc": "/fundamentals-classes", "priority": "0.95", "changefreq": "monthly", "lastmod": today, "title": "Fundamentals Classes (16-Week BJJ Curriculum)"},
        {"loc": "/advanced-classes", "priority": "0.95", "changefreq": "monthly", "lastmod": today, "title": "Advanced Classes (Self-Defense & Sport BJJ)"},
        {"loc": "/membership", "priority": "0.95", "changefreq": "monthly", "lastmod": today, "title": "Jiu-Jitsu Membership & Pricing"},
        {"loc": "/memberships", "priority": "0.85", "changefreq": "monthly", "lastmod": today, "title": "Memberships & Online Registration"},
        {"loc": "/st-pete-jiu-jitsu-professors", "priority": "0.90", "changefreq": "monthly", "lastmod": today, "title": "Black Belt Instructors & Professors"},
        {"loc": "/staff", "priority": "0.80", "changefreq": "monthly", "lastmod": today, "title": "Our Team"},
        {"loc": "/dt_team/professor-eduardo-veio-de-lima", "priority": "0.85", "changefreq": "monthly", "lastmod": today, "title": 'Professor Eduardo "Veio" de Lima — 6th Degree Black Belt'},
        {"loc": "/st-pete-bjj-photo-galleries", "priority": "0.85", "changefreq": "monthly", "lastmod": today, "title": "St. Pete BJJ — Photo Galleries"},
        {"loc": "/news", "priority": "0.85", "changefreq": "weekly", "lastmod": today, "title": "Mat Corner — Academy News & Belt Promotions"},
        {"loc": "/contact", "priority": "0.90", "changefreq": "monthly", "lastmod": today, "title": "Contact St. Pete BJJ & Book Your Free Class"},
        {"loc": "/qa", "priority": "0.80", "changefreq": "monthly", "lastmod": today, "title": "Frequently Asked Questions (FAQ)"},
        {"loc": "/sitemap", "priority": "0.60", "changefreq": "monthly", "lastmod": today, "title": "HTML Sitemap"},
    ]

    with db_cursor() as cur:
        cur.execute("SELECT slug, title FROM galleries WHERE status = 1 ORDER BY sort_order ASC")
        for g in cur.fetchall():
            urls.append({
                "loc": f"/dt_gallery/{g['slug']}",
                "priority": "0.75",
                "changefreq": "monthly",
                "lastmod": today,
                "title": f"Gallery: {g['title']}",
            })

        cur.execute("SELECT slug, title, published_at FROM posts WHERE status = 1 ORDER BY published_at DESC")
        for p in cur.fetchall():
            urls.append({
                "loc": f"/{p['slug']}",
                "priority": "0.70",
                "changefreq": "yearly",
                "lastmod": p["published_at"] or today,
                "title": p["title"],
            })

    return urls


@router.get("/sitemap.xml")
async def sitemap_xml(request: Request):
    base = settings.BASE_URL.rstrip("/")
    urls = get_all_public_urls()
    xml_items = []
    for u in urls:
        xml_items.append(
            f"""  <url>
    <loc>{base}{u['loc']}</loc>
    <lastmod>{u['lastmod']}</lastmod>
    <changefreq>{u['changefreq']}</changefreq>
    <priority>{u['priority']}</priority>
  </url>"""
        )
    xml_str = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(xml_items)
        + "\n</urlset>"
    )
    return Response(content=xml_str, media_type="application/xml")


@router.get("/robots.txt")
async def robots_txt():
    base = settings.BASE_URL.rstrip("/")
    txt = f"""User-agent: *
Allow: /
Disallow: {settings.ADMIN_PATH}
Disallow: /api/

Sitemap: {base}/sitemap.xml
"""
    return PlainTextResponse(content=txt)


@router.get(f"/{settings.INDEXNOW_KEY}.txt")
async def indexnow_key_file():
    return PlainTextResponse(content=settings.INDEXNOW_KEY)


@router.post("/api/indexnow")
async def trigger_indexnow():
    urls = [f"{settings.BASE_URL.rstrip('/')}{u['loc']}" for u in get_all_public_urls()]
    return JSONResponse({
        "status": "ok",
        "submitted_count": len(urls),
        "key": settings.INDEXNOW_KEY,
        "urls": urls[:10],
    })
