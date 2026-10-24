import json
import sqlite3
from contextlib import contextmanager
from app.config import DB_PATH


def get_db_connection():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


@contextmanager
def db_cursor():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_site_settings() -> dict:
    with db_cursor() as cur:
        cur.execute("SELECT key, value FROM site_settings")
        return {row["key"]: row["value"] for row in cur.fetchall()}


def update_site_setting(key: str, value: str):
    with db_cursor() as cur:
        cur.execute(
            "INSERT INTO site_settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )


SOCIAL_SVG_ICONS = {
    "facebook": '<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M22 12c0-5.523-4.477-10-10-10S2 6.477 2 12c0 4.991 3.657 9.128 8.438 9.878v-6.987h-2.54V12h2.54V9.797c0-2.506 1.492-3.89 3.777-3.89 1.094 0 2.238.195 2.238.195v2.46h-1.26c-1.243 0-1.63.771-1.63 1.562V12h2.773l-.443 2.89h-2.33v6.988C18.343 21.128 22 16.991 22 12z"/></svg>',
    "instagram": '<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M12.315 2c2.43 0 2.784.013 3.808.06 1.064.049 1.791.218 2.427.465a4.902 4.902 0 011.772 1.153 4.902 4.902 0 011.153 1.772c.247.636.416 1.363.465 2.427.048 1.067.06 1.407.06 4.123v.08c0 2.643-.012 2.987-.06 4.043-.049 1.064-.218 1.791-.465 2.427a4.902 4.902 0 01-1.153 1.772 4.902 4.902 0 01-1.772 1.153c-.636.247-1.363.416-2.427.465-1.067.048-1.407.06-4.123.06h-.08c-2.643 0-2.987-.012-4.043-.06-1.064-.049-1.791-.218-2.427-.465a4.902 4.902 0 01-1.772-1.153 4.902 4.902 0 01-1.153-1.772c-.247-.636-.416-1.363-.465-2.427-.047-1.024-.06-1.379-.06-3.808v-.63c0-2.43.013-2.784.06-3.808.049-1.064.218-1.791.465-2.427a4.902 4.902 0 011.153-1.772A4.902 4.902 0 015.45 2.525c.636-.247 1.363-.416 2.427-.465C8.901 2.013 9.256 2 11.685 2h.63zm-.081 1.802h-.468c-2.456 0-2.784.011-3.807.058-.975.045-1.504.207-1.857.344-.467.182-.8.398-1.15.748-.35.35-.566.683-.748 1.15-.137.353-.3.882-.344 1.857-.047 1.023-.058 1.351-.058 3.807v.468c0 2.456.011 2.784.058 3.807.045.975.207.1504.344 1.857.182.466.399.8.748 1.15.35.35.683.566 1.15.748.353.137.882.3 1.857.344 1.054.048 1.37.058 4.041.058h.08c2.597 0 2.917-.01 3.96-.058.976-.045 1.505-.207 1.858-.344.466-.182.8-.398 1.15-.748.35-.35.566-.683.748-1.15.137-.353.3-.882.344-1.857.048-1.055.058-1.37.058-4.041v-.08c0-2.597-.01-2.917-.058-3.96-.045-.976-.207-1.505-.344-1.858a3.097 3.097 0 00-.748-1.15 3.098 3.098 0 00-1.15-.748c-.353-.137-.882-.3-1.857-.344-1.023-.047-1.351-.058-3.807-.058zM12 6.865a5.135 5.135 0 110 10.27 5.135 5.135 0 010-10.27zm0 1.802a3.333 3.333 0 100 6.666 3.333 3.333 0 000-6.666zm5.338-3.205a1.2 1.2 0 110 2.4 1.2 1.2 0 010-2.4z"/></svg>',
    "youtube": '<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M23.498 6.186a3.016 3.016 0 00-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 00.502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 002.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 002.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/></svg>',
    "tiktok": '<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M19.59 6.69a4.83 4.83 0 01-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 01-5.2 1.74 2.89 2.89 0 012.31-4.64 2.93 2.93 0 01.88.13V9.4a6.84 6.84 0 00-1-.05A6.33 6.33 0 005 20.1a6.34 6.34 0 0010.86-4.43v-7a8.16 8.16 0 004.77 1.52v-3.4a4.85 4.85 0 01-1-.1z"/></svg>',
    "twitter": '<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>',
    "linkedin": '<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M19 3a2 2 0 012 2v14a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h14m-.5 15.5v-5.3a3.26 3.26 0 00-3.26-3.26c-.85 0-1.84.52-2.28 1.3v-1.11h-2.79v8.37h2.79v-4.93c0-.77.62-1.4 1.39-1.4a1.4 1.4 0 011.4 1.4v4.93h2.75M6.88 8.56a1.68 1.68 0 001.68-1.68c0-.93-.75-1.69-1.68-1.69a1.69 1.69 0 00-1.69 1.69c0 .93.76 1.68 1.69 1.68m1.39 9.94v-8.37H5.5v8.37h2.77z"/></svg>',
    "yelp": '<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M12.14 11.18L9.28 4.21c-.2-.49-.84-.66-1.3-.32L5.1 5.98c-.45.33-.52.97-.15 1.39l5.56 6.26c.48.54 1.37.2 1.63-.45zm-.82 2.91l-6.11 1.68c-.55.15-.87.72-.68 1.26l1.05 2.95c.19.53.78.8 1.3.58l5.39-2.27c.64-.27.67-1.18.05-1.52l-1-.68zm2.47.49l1.46 5.98c.13.55.71.88 1.26.71l2.99-.94c.54-.17.83-.75.63-1.28l-2.21-5.88c-.25-.66-1.16-.72-1.51-.11l-2.62 1.52zm.71-2.55l5.95-1.64c.55-.15.86-.73.67-1.27l-1.08-2.94c-.2-.53-.8-.79-1.32-.56l-5.35 2.38c-.63.28-.65 1.19-.02 1.52l1.15.51z"/></svg>',
    "globe": '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9"/></svg>',
}


def get_social_links(site: dict | None = None) -> list[dict]:
    if site is None:
        site = get_site_settings()
    links = []
    platforms = [
        ("facebook_url", "Facebook", "facebook"),
        ("instagram_url", "Instagram", "instagram"),
        ("youtube_url", "YouTube", "youtube"),
        ("tiktok_url", "TikTok", "tiktok"),
        ("twitter_url", "X / Twitter", "twitter"),
        ("yelp_url", "Yelp", "yelp"),
        ("linkedin_url", "LinkedIn", "linkedin"),
    ]
    for key, label, icon_key in platforms:
        url = (site.get(key) or "").strip()
        if url:
            links.append({
                "key": key,
                "name": label,
                "url": url,
                "icon_svg": SOCIAL_SVG_ICONS.get(icon_key, SOCIAL_SVG_ICONS["globe"]),
            })

    extra_raw = site.get("extra_socials_json") or "[]"
    try:
        extras = json.loads(extra_raw)
        if isinstance(extras, list):
            for item in extras:
                name = (item.get("name") or "").strip()
                url = (item.get("url") or "").strip()
                if name and url:
                    lower = name.lower()
                    icon_key = "globe"
                    for k in SOCIAL_SVG_ICONS:
                        if k in lower:
                            icon_key = k
                            break
                    links.append({
                        "key": "custom",
                        "name": name,
                        "url": url,
                        "icon_svg": SOCIAL_SVG_ICONS[icon_key],
                    })
    except Exception:
        pass

    return links


DEFAULT_HOME_WELCOME_HTML = """<p>Welcome to <strong>St. Pete Brazilian Jiu-Jitsu</strong>! Whether you're brand new to the wonderful art of Brazilian Jiu-Jitsu, a seasoned competitor, or anything in between, at St. Pete BJJ you'll find a welcoming and positive environment to bring your skills to the next level!</p>
<p><strong>At St. Pete BJJ, we are dedicated to helping our students reach their goals.</strong> For those looking to get in shape and have fun, our Brazilian Jiu-Jitsu classes will have you burning calories and enjoying it! People from all walks of life, at any level of fitness, will benefit from BJJ. <strong>We will not only teach you the incredibly effective art of Brazilian Jiu-Jitsu, but increase your flexibility, stamina, strength and self-confidence along the way!</strong></p>
<p>For students who want to learn the basics and improve their skills in self-defense, our <a href="/fundamentals-classes">Fundamental classes</a> will teach you the vital self-defense techniques that form the foundation of Brazilian Jiu-Jitsu. <strong>Students in our fundamentals classes will learn everything from escapes and sweeps, to throws and takedowns, to chokes and joint locks.</strong> Even advanced students benefit from our Fundamentals classes as they hone the minor details that make these techniques so successful.</p>
<p>Once they have a firm grasp of the fundamentals of BJJ, our students are able to attend our <a href="/advanced-classes">Advanced classes</a>. The Advanced curriculum builds upon the basics and dives deeper into the vast array of techniques available to the Jiu-Jitsu practitioner.</p>
<p><strong>In addition to our regular class schedule, we often welcome guest instructors and offer seminars from top competitors and teachers in the Brazilian Jiu-Jitsu world.</strong></p>
<p><strong>At St. Pete BJJ, we pride ourselves in creating a fun, welcoming and clean training atmosphere. We welcome guests of all skill levels and visitors from other academies.</strong> Please feel free to <a href="/contact">contact us</a> or drop by to find out why St. Pete BJJ is such a great place to train in the art of Brazilian Jiu-Jitsu.</p>"""


def ensure_cms_schema():
    """Ensures all CMS tables, columns, and default editable site_settings exist."""
    with db_cursor() as cur:
        # 1. Add hero_image to pages if missing
        cur.execute("PRAGMA table_info(pages)")
        page_cols = {row["name"] for row in cur.fetchall()}
        if "hero_image" not in page_cols:
            cur.execute("ALTER TABLE pages ADD COLUMN hero_image TEXT DEFAULT '/wp-content/uploads/2019/05/Slide-1.jpg'")

        # 2. Create lineage_entries table for the /lineage page
        cur.execute("""
        CREATE TABLE IF NOT EXISTS lineage_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            generation_badge TEXT NOT NULL,
            name TEXT NOT NULL,
            image TEXT NOT NULL,
            bio TEXT NOT NULL,
            sort_order INTEGER DEFAULT 0,
            status INTEGER DEFAULT 1
        )
        """)
        cur.execute("SELECT COUNT(*) AS c FROM lineage_entries")
        if cur.fetchone()["c"] == 0:
            seed_lineage = [
                (
                    "Generation 01 • Kodokan Judo & Jiu-Jitsu Pioneer (1878–1941)",
                    "Mitsuyo “Count Koma” Maeda",
                    "/static/images/lineage/mitsuyo-maeda.jpg",
                    "<p>Trained directly at the Kodokan in Tokyo under Judo founder Jigoro Kano, Mitsuyo Maeda traveled the world accepting challenge matches against wrestlers, boxers, and martial artists of every style. Arriving in Belém, Brazil in 1914, Maeda befriended Gastão Gracie and began teaching the art of ground fighting and leverage-based submissions to Gastão’s eldest son, Carlos Gracie.</p>",
                    1,
                ),
                (
                    "Generation 02 • Founder of Brazilian Jiu-Jitsu (1902–1994)",
                    "Grandmaster Carlos Gracie Sr.",
                    "/static/images/lineage/carlos-gracie-sr.jpg",
                    "<p>As Maeda’s premier Brazilian student, Carlos Gracie Sr. opened the first Gracie Jiu-Jitsu Academy in Brazil in 1925 alongside his brothers, including Hélio Gracie. Together they refined traditional Japanese techniques into a leverage-and-timing system designed so a smaller defender could overcome a larger, stronger opponent.</p>",
                    2,
                ),
                (
                    "Generation 03 • 8th Degree Coral Belt • Founder of IBJJF & Gracie Barra",
                    "Master Carlos “Carlinhos” Gracie Jr.",
                    "/static/images/lineage/carlos-gracie-jr.jpg",
                    "<p>Son of Grandmaster Carlos Gracie Sr., Carlos “Carlinhos” Gracie Jr. dedicated his life to organizing and spreading Brazilian Jiu-Jitsu globally—founding the International Brazilian Jiu-Jitsu Federation (IBJJF), the Confederation of Brazilian Jiu-Jitsu (CBJJ), and the famed Gracie Barra team in Rio de Janeiro in 1986.</p>",
                    3,
                ),
                (
                    "Generation 04 • Sean Lynch's Instructor (Retired)",
                    "Professor Eduardo “Veio” de Lima",
                    "/wp-content/uploads/2015/09/eduardo.jpg",
                    "<p>A 6th degree black belt under Carlos “Carlinhos” Gracie Jr., Eduardo “Veio” de Lima began training at age nineteen in Rio de Janeiro at the original Gracie Barra Academy—studying for his first two years under Jean Jacques Machado (blue and purple belt) and thereafter under Carlos Gracie Jr. (brown and black belt, 1997), winning multiple gold medals at the IBJJF Pan American Championships.</p><p>After serving as head instructor of Gracie Barra in Rio (where young Roger Gracie was in his kids’ class), Eduardo moved to Florida in 1999/2000. Sean Lynch became one of his earliest American students, earning his black belt from Eduardo in December 2009. <em>(Professor Eduardo is now retired and is not involved in the operation or instruction of St. Pete Brazilian Jiu-Jitsu.)</em></p>",
                    4,
                ),
                (
                    "Generation 05 • 4th Degree Black Belt • Founder & Head Instructor",
                    "Professor Sean Lynch — St. Pete Brazilian Jiu-Jitsu",
                    "/wp-content/uploads/2015/11/seanweb.jpg",
                    "<p>Sean Lynch began training under Eduardo de Lima upon his arrival in the United States in 1999, began teaching in St. Petersburg in 2006, and opened <strong>St. Pete Brazilian Jiu-Jitsu</strong> as a 100% independent academy in 2013. Awarded his black belt in December 2009 and his <strong>4th degree in December 2023</strong>, Sean and our coaching staff carry this lineage forward in an open, ego-free environment.</p>",
                    5,
                ),
            ]
            cur.executemany(
                "INSERT INTO lineage_entries (generation_badge, name, image, bio, sort_order, status) VALUES (?, ?, ?, ?, ?, 1)",
                seed_lineage,
            )

        # 3. Ensure default editable site_settings exist (INSERT OR IGNORE so admin edits are never overwritten)
        default_settings = {
            "site_name": "St. Pete Brazilian Jiu-Jitsu",
            "tagline": "St. Petersburg's Premier Brazilian Jiu-Jitsu, No-Gi & Self-Defense Academy",
            "phone": "(727) 619-4255",
            "phone_vanity": "727.619.4BJJ",
            "email_contact": "info@stpetebjj.com",
            "email_quotes": "info@stpetebjj.com, camaraogb@gmail.com",
            "address": "5540 Haines Rd N, St. Petersburg, FL 33714",
            "logo_url": "/static/images/logo-medallion.png",
            "favicon_url": "/wp-content/uploads/2016/10/favicon.png",
            "waiver_url": "/wp-content/uploads/2017/01/Waiver.pdf",
            "google_maps_url": "https://maps.app.goo.gl/m6PtQRRiCUu4HEZQ7",
            "google_rating": "5.0",
            "google_reviews_count": "54",
            "facebook_url": "https://www.facebook.com/StPeteBJJ/",
            "instagram_url": "https://www.instagram.com/StPeteBJJ/",
            "youtube_url": "",
            "tiktok_url": "",
            "twitter_url": "",
            "yelp_url": "",
            "linkedin_url": "",
            "extra_socials_json": "[]",
            "hero_kicker": "St. Petersburg's Premier Brazilian Jiu-Jitsu Academy",
            "hero_headline_html": 'AUTHENTIC <span class="text-[#CE1E36]">BRAZILIAN JIU-JITSU</span> IN ST. PETE.',
            "hero_subtitle_html": 'Train world-class Gi &amp; No-Gi Jiu-Jitsu, practical Self-Defense, and Judo Takedowns under <strong class="text-white">4th Degree Black Belt Professor Sean Lynch</strong> and our experienced coaching staff. Welcoming, ego-free, and zero long-term contracts.',
            "hero_slide_1": "/static/images/hero-bjj-gi.jpg",
            "hero_slide_2": "/wp-content/uploads/2019/02/BJJ_Promotions_2019-65.jpg",
            "hero_slide_3": "/static/images/hero-bjj-nogi.jpg",
            "hero_slide_4": "/wp-content/uploads/2019/05/Slide-1.jpg",
            "home_welcome_kicker": "Welcome to Our Academy",
            "home_welcome_heading_html": 'St. Pete BJJ — <span class="text-[#CE1E36]">Where Technique Meets Community</span>',
            "home_welcome_body_html": DEFAULT_HOME_WELCOME_HTML,
            "home_fundamentals_box_img": "/wp-content/uploads/2015/09/Fundamental_box1.jpg",
            "home_advanced_box_img": "/wp-content/uploads/2015/09/advanced_box.jpg",
            "home_showcase_img_1": "/wp-content/uploads/2019/02/BJJ_Promotions_2019-65.jpg",
            "home_showcase_img_2": "/wp-content/uploads/2019/05/AJ1web.jpg",
            "ai_enabled": "true",
            "ai_provider": "gemini",
            "ai_model": "gemini-2.5-flash",
            "ai_max_messages_per_session": "15",
            "ai_max_messages_per_ip_day": "40",
            "ai_openai_key": "",
            "ai_gemini_key": "",
            "ai_anthropic_key": "",
            "ai_xai_key": "",
            "ai_openrouter_key": "",
            "ai_deepseek_key": "",
            "ai_custom_instructions": "",
        }
        for k, v in default_settings.items():
            cur.execute("INSERT OR IGNORE INTO site_settings (key, value) VALUES (?, ?)", (k, v))

        # 4. Create AI Chat Session & Message tables
        cur.execute("""
        CREATE TABLE IF NOT EXISTS ai_chat_sessions (
            session_id TEXT PRIMARY KEY,
            ip_address TEXT NOT NULL,
            messages_count INTEGER DEFAULT 0,
            terminated INTEGER DEFAULT 0,
            termination_reason TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS ai_chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            actions_json TEXT DEFAULT '[]',
            flagged INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)
