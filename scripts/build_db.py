import sqlite3
import json
import hashlib
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "stpetebjj.db"


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    cur.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT DEFAULT 'admin',
        is_active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS site_settings (
        key TEXT PRIMARY KEY,
        value TEXT
    );

    CREATE TABLE IF NOT EXISTS programs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        slug TEXT UNIQUE NOT NULL,
        url TEXT NOT NULL,
        badge TEXT,
        level TEXT,
        short_desc TEXT,
        description TEXT,
        image TEXT,
        banner_image TEXT,
        sort_order INTEGER DEFAULT 0,
        featured INTEGER DEFAULT 1,
        status INTEGER DEFAULT 1,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS memberships (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        slug TEXT UNIQUE NOT NULL,
        category TEXT DEFAULT 'membership',
        price_display TEXT NOT NULL,
        billing_period TEXT,
        badge TEXT,
        description TEXT,
        features_json TEXT,
        external_url TEXT,
        featured INTEGER DEFAULT 0,
        sort_order INTEGER DEFAULT 0,
        status INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS instructors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        slug TEXT UNIQUE NOT NULL,
        rank TEXT NOT NULL,
        role TEXT NOT NULL,
        lineage TEXT,
        bio TEXT NOT NULL,
        image TEXT NOT NULL,
        featured INTEGER DEFAULT 1,
        sort_order INTEGER DEFAULT 0,
        status INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS galleries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        wp_id INTEGER,
        title TEXT NOT NULL,
        slug TEXT UNIQUE NOT NULL,
        category_slug TEXT,
        category_name TEXT,
        description TEXT,
        cover_image TEXT NOT NULL,
        photo_count INTEGER DEFAULT 0,
        sort_order INTEGER DEFAULT 0,
        status INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS gallery_photos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        gallery_id INTEGER NOT NULL,
        wp_attachment_id INTEGER,
        title TEXT,
        image_url TEXT NOT NULL,
        sort_order INTEGER DEFAULT 0,
        FOREIGN KEY (gallery_id) REFERENCES galleries(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        wp_id INTEGER,
        title TEXT NOT NULL,
        slug TEXT UNIQUE NOT NULL,
        category_slug TEXT DEFAULT 'promotions',
        category_name TEXT DEFAULT 'Academy News & Promotions',
        excerpt TEXT,
        content TEXT NOT NULL,
        featured_image TEXT,
        published_at TEXT,
        status INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS pages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        wp_id INTEGER,
        title TEXT NOT NULL,
        slug TEXT UNIQUE NOT NULL,
        meta_title TEXT,
        meta_description TEXT,
        content TEXT,
        template TEXT DEFAULT 'page.html',
        status INTEGER DEFAULT 1,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS faqs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question TEXT NOT NULL,
        answer TEXT NOT NULL,
        sort_order INTEGER DEFAULT 0,
        status INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS quotes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        phone TEXT,
        program_interest TEXT,
        experience_level TEXT,
        preferred_date TEXT,
        city TEXT,
        state TEXT,
        zipcode TEXT,
        message TEXT,
        status TEXT DEFAULT 'new',
        internal_notes TEXT DEFAULT '',
        ip_address TEXT,
        recaptcha_score REAL DEFAULT 1.0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS legacy_redirects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        old_path TEXT UNIQUE NOT NULL,
        new_path TEXT NOT NULL,
        http_status INTEGER DEFAULT 301,
        hit_count INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS security_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ip_address TEXT,
        country_code TEXT,
        request_path TEXT,
        reason TEXT,
        user_agent TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 1. Admin User
    salt = "spbjj2026"
    pw_hash = hashlib.sha256((salt + "StPeteBJJ2026!").encode("utf-8")).hexdigest()
    cur.execute(
        "INSERT OR REPLACE INTO users (id, username, password_hash, role, is_active) VALUES (1, 'admin', ?, 'admin', 1)",
        (f"{salt}:{pw_hash}",)
    )

    # 2. Site Settings
    settings_data = {
        "site_name": "St. Pete Brazilian Jiu-Jitsu",
        "tagline": "St. Petersburg's Premier Brazilian Jiu-Jitsu, Self-Defense & Submission Grappling Academy",
        "phone": "(727) 619-4255",
        "phone_vanity": "727.619.4BJJ",
        "phone_raw": "17276194255",
        "email_contact": "info@stpetebjj.com",
        "email_quotes": "info@stpetebjj.com, camaraogb@gmail.com",
        "address": "5540 Haines Rd N, St. Petersburg, FL 33714",
        "facebook_url": "https://www.facebook.com/StPeteBJJ/",
        "instagram_url": "https://www.instagram.com/StPeteBJJ/",
        "waiver_url": "/wp-content/uploads/2017/01/Waiver.pdf",
        "zenplanner_partition_key": "e5375747-e005-479f-bf4c-a6963ec54790",
        "zenplanner_calendar_id": "6c9eb298-1fa2-455c-b545-e89677f1cd74",
        "zenplanner_freetrial_id": "39e9efab-01e0-43e6-8211-e2b1288fa494",
        "zenplanner_membership_id": "ca2040c1-5909-4d97-871e-9f13e6fdab19",
        "zenplanner_signup_iframe": "https://stpetebjj.zenplanner.com/zenplanner/portal/sign-up-now.cfm?type=Membership&FRAME=true",
        "recaptcha_site_key": "6LeUH_0tAAAAAJ8M_xd73QUHMo4Vc8lQ32oMcyey",
        "recaptcha_secret_key": "6LeUH_0tAAAAAL7nwIF2-pNH6UVUe7Pl3j6RuZNK",
        "stripe_enabled": "0",
        "stripe_publishable_key": "",
        "stripe_secret_key": "",
        "geo_block_enabled": "1",
        "geo_allowed_countries": "US, CA, MX, PR",
        "geo_allow_search_bots": "1",
        "waf_block_scanners": "1",
        "geo_ip_whitelist": "",
        "geo_ip_blacklist": "",
    }
    for k, v in settings_data.items():
        cur.execute("INSERT OR REPLACE INTO site_settings (key, value) VALUES (?, ?)", (k, v))

    # 3. Programs / Classes
    cur.execute("DELETE FROM programs")
    programs_data = [
        (
            "Fundamentals Classes",
            "fundamentals-classes",
            "/fundamentals-classes",
            "16-Week Core Curriculum",
            "All Levels • Beginner Friendly",
            "Build an unshakable foundation in Brazilian Jiu-Jitsu self-defense, escapes, sweeps, takedowns, and submissions in a structured, welcoming environment.",
            """<p>At <strong>St. Pete Brazilian Jiu-Jitsu</strong>, our Fundamentals Classes are designed to benefit students beginning their journey in Brazilian Jiu-Jitsu, while also offering valuable technical adjustments to more experienced practitioners.</p>
<p>Following a structured <strong>16-week curriculum</strong>, our Fundamentals Classes build a solid foundation in self-defense using the core leverage-based techniques of Brazilian Jiu-Jitsu. Students in our Fundamentals program learn everything from escapes and sweeps, to throws and takedowns, to chokes and joint locks in a controlled, ego-free, and safe training environment.</p>
<p>Beginners are invited to join any Fundamentals class on our weekly schedule to start their Jiu-Jitsu journey—your first introductory class is always free. New students are paired with a senior student who helps guide them step-by-step through the techniques being taught.</p>
<p>Each Fundamentals class begins with a purposeful warm-up, followed by a self-defense technique before moving into core grappling principles and controlled positional sparring. For your first class, a clean loaner gi (kimono uniform) is provided at no charge—just arrive 10 minutes early so we can fit you properly.</p>""",
            "/static/images/program-fundamentals.jpg",
            "/wp-content/uploads/2016/10/Fundamental_box2.jpg",
            1, 1, 1
        ),
        (
            "Advanced Classes",
            "advanced-classes",
            "/advanced-classes",
            "3-Stripe White Belt & Above",
            "Intermediate & Advanced • Live Sparring",
            "Combine high-level self-defense with modern sport Jiu-Jitsu systems, chain passing, submission traps, and live sparring rounds.",
            """<p>Once students have earned a <strong>third stripe on their white belt</strong> (or hold a blue, purple, brown, or black belt), they are eligible to attend our <strong>Advanced Classes</strong> at St. Pete BJJ.</p>
<p>Our Advanced Classes follow a progressive curriculum that combines proven street self-defense with high-level sport Jiu-Jitsu strategies, guard retention, pressure passing, leg locks, and submission chaining. The Advanced curriculum builds directly upon the Fundamentals and dives deeper into the micro-adjustments and timing that make elite Jiu-Jitsu so effective.</p>
<p>Students looking to expand their technical arsenal, sharpen their timing, or prepare for IBJJF and FFBJJ tournaments will benefit immensely from our Advanced program. Every session includes dedicated live sparring (rolling) rounds with black, brown, purple, and blue belt training partners.</p>""",
            "/static/images/program-advanced.jpg",
            "/wp-content/uploads/2016/10/Advanced-Box2.jpg",
            2, 1, 1
        ),
        (
            "No-Gi Submission Grappling",
            "no-gi-submission-grappling",
            "/brazilian-jiu-jitsu-class-schedule-saint-petersburg-florida-2",
            "Gi & No-Gi Training",
            "Fast-Paced Clinch, Scrambles & Submissions",
            "High-pace submission grappling without the traditional kimono—focusing on underhooks, collar ties, wrestling scrambles, and high-percentage finishes.",
            """<p>Our <strong>No-Gi Submission Grappling</strong> classes train the art of Brazilian Jiu-Jitsu without the traditional kimono (gi), replacing cloth grips with natural body control: overhooks, underhooks, wrist control, collar ties, and dynamic leg entanglements.</p>
<p>Led by veteran grapplers including former Marine RECON &amp; MMA coach Shane Dunn, powerlifting record-holder Danny Watson, and NCAA wrestling qualifier Professor Brian Travis, our No-Gi sessions blend classical Brazilian Jiu-Jitsu positional control with modern wrestling scrambles and submission hunting.</p>""",
            "/static/images/hero-bjj-nogi.jpg",
            "/wp-content/uploads/2016/11/Slide-5.jpg",
            3, 1, 1
        ),
        (
            "Judo & Takedowns for BJJ",
            "judo-takedowns",
            "/brazilian-jiu-jitsu-class-schedule-saint-petersburg-florida-2",
            "Stand-Up Mastery",
            "Throws, Foot Sweeps & Grip Fighting",
            "Learn high-percentage throws, foot sweeps, breakfalls, and stand-up grip fighting from 3rd Degree Judo Black Belt & National Champion Coach JR Angeles.",
            """<p>Every fight and every tournament match begins on the feet. At St. Pete BJJ, our dedicated <strong>Judo &amp; Takedowns</strong> program is taught by <strong>Neldo &ldquo;JR&rdquo; Angeles</strong>—a 3rd Degree Black Belt in Judo, 2008 National Judo Champion, and Certified National Level Judo Coach and Referee.</p>
<p>Students learn safe breakfalls (ukemi), gripping strategies (kumi-kata), off-balancing (kuzushi), foot sweeps (ashi-waza), hip throws, and seamless transitions from standing throws directly into dominant ground pins and submissions.</p>""",
            "/wp-content/uploads/2016/11/Slide-4.jpg",
            "/wp-content/uploads/2016/11/Slide-4.jpg",
            4, 1, 1
        ),
        (
            "Juniors & Young Adults (Ages 12–18)",
            "juniors-bjj",
            "/membership",
            "Ages 12 to 18",
            "Confidence, Discipline & Practical Self-Defense",
            "Teens and young adults ages 12+ train real Brazilian Jiu-Jitsu techniques in a positive, respectful mentorship environment.",
            """<p>We welcome young adults <strong>ages 12 to 18</strong> into our Fundamentals program with a dedicated Juniors Unlimited Membership rate ($110/month). Young adults develop real-world self-defense capability, physical conditioning, composure under pressure, and lifelong confidence alongside supportive mentors.</p>""",
            "/wp-content/uploads/2015/09/1897779_896007733778295_1082388326842125729_n.jpg",
            "/wp-content/uploads/2015/09/1897779_896007733778295_1082388326842125729_n.jpg",
            5, 1, 1
        ),
        (
            "Open Mat, Seminars & Private Lessons",
            "private-instruction",
            "/contact",
            "1-on-1 & Visitor Friendly",
            "BJJ Globetrotters Recognized • Zero Politics",
            "Accelerate your progress with 1-on-1 private instruction from our black belts, attend world-champion seminars, or drop in for Open Mat.",
            """<p>In addition to our regular weekly schedule, St. Pete BJJ hosts regular <strong>Open Mat</strong> sessions, world-champion guest seminars, and <strong>1-on-1 Private Instruction</strong> tailored to your specific game. We proudly recognize <strong>BJJ Globetrotters</strong> members and welcome visiting students from all academies and affiliations with open arms.</p>""",
            "/wp-content/uploads/2019/05/Slide-1.jpg",
            "/wp-content/uploads/2019/05/Slide-1.jpg",
            6, 1, 1
        ),
    ]
    cur.executemany("""
        INSERT INTO programs (name, slug, url, badge, level, short_desc, description, image, banner_image, sort_order, featured, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, programs_data)

    # 4. Memberships
    cur.execute("DELETE FROM memberships")
    memberships_data = [
        (
            "Free Introductory Class",
            "free-intro-class",
            "trial",
            "FREE",
            "First Class",
            "No Experience Needed",
            "Your first introductory class is always free! Join any Fundamentals class on our schedule—we provide a clean loaner gi (uniform) and pair you with a senior student.",
            json.dumps([
                "Attend any Fundamentals class on our schedule",
                "Clean loaner Gi (uniform) provided free of charge",
                "Paired 1-on-1 with an experienced senior student",
                "Zero sales pressure — no contracts or hidden fees"
            ]),
            "/contact",
            0, 1, 1
        ),
        (
            "Unlimited Monthly Membership",
            "unlimited-monthly",
            "membership",
            "$130",
            "/ month",
            "Most Popular • No Contract",
            "Full unlimited access to all Fundamentals, Advanced (3-stripe+), No-Gi, Judo/Takedowns, and Open Mat sessions. Month-to-month automated billing with zero long-term contracts.",
            json.dumps([
                "Unlimited Gi & No-Gi BJJ classes every week",
                "Includes Fundamentals, Advanced, Judo & Open Mat",
                "Month-to-month billing — no long-term contract required",
                "Discounts for students, military/veterans, LEO & families"
            ]),
            "https://stpetebjj.zenplanner.com/zenplanner/portal/sign-up-now.cfm",
            1, 2, 1
        ),
        (
            "Unlimited Juniors (Ages 12–18)",
            "unlimited-juniors",
            "membership",
            "$110",
            "/ month",
            "Young Adults 12–18",
            "Unlimited monthly Fundamentals classes for young adults ages 12 to 18. Build self-defense skills, discipline, and physical fitness with month-to-month flexibility.",
            json.dumps([
                "Unlimited Fundamentals classes for ages 12 to 18",
                "Structured 16-week self-defense & grappling curriculum",
                "Month-to-month automated billing — no contract required",
                "Positive, ego-free mentorship from black belt instructors"
            ]),
            "https://stpetebjj.zenplanner.com/zenplanner/portal/sign-up-now.cfm",
            0, 3, 1
        ),
        (
            "6 Months Unlimited Package",
            "6-months-unlimited",
            "membership",
            "$700",
            "/ 6 months",
            "Save 10% • Best Value",
            "Commit to 6 months of unlimited Brazilian Jiu-Jitsu training and save 10% off the monthly rate with a single upfront payment.",
            json.dumps([
                "6 full months of unlimited Gi, No-Gi & Open Mat training",
                "Instant 10% savings ($80 off monthly rate)",
                "One simple payment — no recurring monthly bill",
                "Full access to all eligible classes on the schedule"
            ]),
            "https://stpetebjj.zenplanner.com/zenplanner/portal/sign-up-now.cfm",
            0, 4, 1
        ),
        (
            "10-Class Package",
            "10-class-package",
            "dropin",
            "$180",
            "/ 10 classes",
            "Save 10% • Flexible Punch Pass",
            "Ideal for busy professionals, shift workers, or frequent travelers who want flexible mat time with a 10% discount off single drop-in rates.",
            json.dumps([
                "10 full classes to use at your own pace",
                "10% discount compared to individual class drop-ins",
                "Valid for Fundamentals, Advanced, No-Gi & Judo classes",
                "Direct online purchase via ZenPlanner"
            ]),
            "https://stpetebjj.sites.zenplanner.com/retail-product.cfm?productId=40DB5254-3438-470D-81B8-903F19D618BE",
            0, 5, 1
        ),
        (
            "Single Class Drop-In",
            "single-class-drop-in",
            "dropin",
            "$20",
            "/ class",
            "Visitors Always Welcome",
            "Visiting St. Petersburg or dropping in for a day? All affiliations and skill levels are welcome on our mats. We proudly recognize BJJ Globetrotters!",
            json.dumps([
                "Single class mat fee for travelers & guests",
                "All academies & affiliations warmly welcomed",
                "BJJ Globetrotters members recognized",
                "Direct online registration via ZenPlanner"
            ]),
            "https://stpetebjj.sites.zenplanner.com/retail-product.cfm?productId=E7951814-35D2-433C-80F1-D818ED627B01",
            0, 6, 1
        ),
    ]
    cur.executemany("""
        INSERT INTO memberships (name, slug, category, price_display, billing_period, badge, description, features_json, external_url, featured, sort_order, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, memberships_data)

    # 5. Instructors
    cur.execute("DELETE FROM instructors")
    instructors_data = [
        (
            "Professor Sean Lynch",
            "sean-lynch",
            "4th Degree Black Belt",
            "Head Instructor & Academy Founder",
            "Carlos Gracie Jr. → Eduardo 'Veio' de Lima → Sean Lynch",
            """<p><strong>Sean Lynch</strong> began his Brazilian Jiu-Jitsu journey under Professor Eduardo &ldquo;Veio&rdquo; de Lima, a 6th degree black belt and one of the pioneers of the famed Gracie Barra team. Sean trained in several martial arts for many years before meeting Professor Eduardo when he arrived in the United States in 1999. Sean immediately fell in love with the effectiveness of Brazilian Jiu-Jitsu and became one of Eduardo&rsquo;s earliest American students.</p>
<p>In 2006, while Sean was a purple belt, Professor Eduardo asked him to begin teaching a Jiu-Jitsu program together to help spread authentic BJJ to St. Petersburg. That program grew steadily until opening an independent academy in 2013—and <strong>St. Pete Brazilian Jiu-Jitsu</strong> was born.</p>
<p>An avid world traveler who spent 18 months on an around-the-world journey, Sean has trained across Brazil, New Zealand, Thailand, and around the globe. He found Jiu-Jitsu to be a universal language of friendship, and the diverse, ego-free, welcoming atmosphere of St. Pete BJJ reflects that global spirit. Sean received his black belt in December 2009 and was awarded his <strong>4th degree in December 2023</strong>.</p>""",
            "/wp-content/uploads/2015/11/seanweb.jpg",
            1, 1, 1
        ),
        (
            'Professor Eduardo "Veio" de Lima',
            "professor-eduardo-veio-de-lima",
            "6th Degree Black Belt",
            "Lineage Master & Gracie Barra Pioneer",
            "Mitsuyo Maeda → Carlos Gracie Sr. → Carlos Gracie Jr. → Eduardo de Lima",
            """<p>A <strong>6th degree black belt</strong> in Brazilian Jiu-Jitsu under Carlos &ldquo;Carlinhos&rdquo; Gracie, Jr. and head of <strong>Gracie Barra Clearwater</strong>, Professor Eduardo &ldquo;Veio&rdquo; de Lima has won multiple gold medals in the black belt divisions at the IBJJF Pan American Championships.</p>
<p>Eduardo began training in BJJ at age nineteen in Rio de Janeiro, Brazil after his friend Renzo Gracie recommended he try a class at the original Gracie Barra Academy. For his first two years, he studied under Jean Jacques Machado (who awarded his blue and purple belts), and thereafter under Carlos Gracie, Jr., who awarded his brown and black belts—receiving his black belt in 1997 after eight years of intensive training.</p>
<p>Once promoted to black belt, Eduardo served as head instructor of Gracie Barra in Rio, where legend Roger Gracie was one of his students in the children&rsquo;s class. Coming to Florida in 2000 with the support of Carlos Gracie, Jr., Eduardo built one of Tampa Bay&rsquo;s most respected black belt lineages and mentored Professor Sean Lynch from white belt to 4th degree black belt.</p>""",
            "/wp-content/uploads/2015/09/eduardo.jpg",
            0, 99, 1
        ),
        (
            "Coach Danny Watson",
            "danny-watson",
            "BJJ Instructor & Strength Coach",
            "Gi & No-Gi Instructor • Certified Strength Coach",
            "Trained under UFC Champion Matt Serra & Professor Sean Lynch",
            """<p><strong>Danny Watson</strong> first started training Brazilian Jiu-Jitsu in 2007 in New York under UFC Welterweight Champion Matt Serra. After relocating to Florida in 2016, he joined the St. Pete BJJ family.</p>
<p>Danny enjoys teaching and training both in the traditional kimono (Gi) and in No-Gi submission grappling. In addition to his decades on the mats, Danny is a Certified Strength &amp; Conditioning Coach and holds multiple state records in competitive powerlifting.</p>""",
            "/wp-content/uploads/2025/03/Danny2.jpg",
            1, 3, 1
        ),
        (
            "Coach Shane Dunn",
            "shane-dunn",
            "Veteran Grappler & MMA Coach",
            "No-Gi Submission Grappling Instructor",
            "Sergio Monteiro (Murilo Bustamante Lineage)",
            """<p>A former member of <strong>U.S. Marine Force RECON</strong>, <strong>Shane Dunn</strong> has been training Brazilian Jiu-Jitsu since the early 1990s, when he began studying under Sergio Monteiro, a 2nd degree black belt under Brazilian Top Team co-founder Murilo Bustamante.</p>
<p>While his early foundation was built in the Gi, Shane adapted his style to No-Gi grappling in the late 1990s to compete in Mixed Martial Arts during its formative era. Since then, Shane has competed extensively in submission grappling and coached numerous accomplished MMA fighters. His decades of pressure grappling expertise anchor our No-Gi program at St. Pete BJJ.</p>""",
            "/wp-content/uploads/2015/11/SHANE-web.jpg",
            1, 4, 1
        ),
        (
            "Professor Brian Travis",
            "brian-travis",
            "Black Belt • 2x NCAA Wrestling Qualifier",
            "Gi & No-Gi Instructor",
            "Black Belt under World Champion AJ Agazarm",
            """<p><strong>Brian Travis</strong> is a Brazilian Jiu-Jitsu black belt under World Champion AJ Agazarm and has been training Jiu-Jitsu since the age of 7. Growing up in Florida, Brian also competed in folkstyle and freestyle wrestling through college—earning multiple Florida State place-winner honors and qualifying twice for the <strong>NCAA Division III National Championships</strong>.</p>
<p>Following his collegiate wrestling career, Brian traveled internationally and competed across all major IBJJF championships. Today, he brings elite takedown mechanics, scramble awareness, and technical precision to our classes while enjoying the camaraderie of the St. Pete BJJ mat room.</p>""",
            "/wp-content/uploads/2023/02/brianweb.webp",
            1, 5, 1
        ),
        (
            'Coach Neldo "JR" Angeles',
            "neldo-jr-angeles",
            "3rd Degree Judo Black Belt • BJJ Brown Belt",
            "Judo & Takedowns Instructor",
            "USA Judo National Champion, Certified National Coach & Referee",
            """<p><strong>Neldo &ldquo;JR&rdquo; Angeles</strong> leads our dedicated Judo and Takedowns classes at St. Pete Brazilian Jiu-Jitsu. JR is a <strong>3rd Degree Black Belt in Judo</strong> who has been training and competing since 2005.</p>
<p>He is a 2008 Novice National Judo Champion, a Certified National Level Judo Coach, and a Certified National Level Judo Referee. JR began cross-training in Brazilian Jiu-Jitsu in 2017 and holds the rank of BJJ brown belt, specializing in adapting high-percentage Judo throws and foot sweeps directly for Gi and No-Gi grappling.</p>""",
            "/wp-content/uploads/2023/02/JR3.webp",
            1, 6, 1
        ),
        (
            'Professor Prentice Gerald "Jerry" Outlaw Jr.',
            "jerry-outlaw",
            "Black Belt",
            "Fundamentals & All-Levels Instructor",
            "Black Belt under Professor Sean Lynch (Nov 2024)",
            """<p><strong>Prentice Gerald &ldquo;Jerry&rdquo; Outlaw Jr.</strong> is a Brazilian Jiu-Jitsu black belt under Professor Sean Lynch. Jerry trained in various martial arts before beginning his dedicated study of Brazilian Jiu-Jitsu in 2014, earning his black belt in November 2024.</p>
<p>A lifelong professional touring musician whose career has taken him around the globe, Jerry now in his sixth decade both teaches and trains for the love of martial arts, physical and mental longevity, and sharing the art of Jiu-Jitsu with students of every age.</p>""",
            "/wp-content/uploads/2025/03/jOutlaw.jpg",
            1, 7, 1
        ),
        (
            'Professor Rodrigo "Manilha" Guimaraes',
            "rodrigo-manilha-guimaraes",
            "3rd Degree Black Belt",
            "Brazilian Jiu-Jitsu Instructor",
            "Carlos Gracie Jr. → Eduardo 'Veio' de Lima → Rodrigo Guimaraes",
            """<p>Hailing from Recife, Brazil, <strong>Rodrigo &ldquo;Manilha&rdquo; Guimaraes</strong> is a <strong>3rd degree black belt</strong> in Brazilian Jiu-Jitsu under Professor Eduardo &ldquo;Veio&rdquo; de Lima. A lifelong martial artist with authentic Brazilian technical roots, Rodrigo embodies the joy of Jiu-Jitsu—training and teaching to stay sharp, build community, and share technical flow on the mats.</p>""",
            "/wp-content/uploads/2015/11/rodrigoweb.jpg",
            1, 8, 1
        ),
    ]
    cur.executemany("""
        INSERT INTO instructors (name, slug, rank, role, lineage, bio, image, featured, sort_order, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, instructors_data)

    # 6. Galleries & Photos (Exact mapping from spb-db)
    cur.execute("DELETE FROM gallery_photos")
    cur.execute("DELETE FROM galleries")

    # Map of attachment IDs to relative URLs from spb-db
    att_map = {
        1140: "/wp-content/uploads/2015/09/1897779_896007733778295_1082388326842125729_n.jpg",
        1141: "/wp-content/uploads/2015/09/1907589_849125741799828_1439112446862324032_n.jpg",
        1142: "/wp-content/uploads/2015/09/1935515_257862924259449_725263544_n.jpg",
        1143: "/wp-content/uploads/2015/09/10369577_890618874317181_8978166967203622704_n.jpg",
        1144: "/wp-content/uploads/2015/09/11257780_890618864317182_7384411988974465858_n.jpg",
        1146: "/wp-content/uploads/2015/09/1532000_636794079699663_806380614_n.jpg",
        1147: "/wp-content/uploads/2015/09/1959989_767948639917539_7329040930744886015_n.jpg",
        1149: "/wp-content/uploads/2015/09/292001_257864040926004_732781136_n.jpg",
        1150: "/wp-content/uploads/2015/09/302948_257606267618448_609988187_n.jpg",
        1151: "/wp-content/uploads/2015/09/302948_257606274285114_183297974_n.jpg",
        1152: "/wp-content/uploads/2015/09/324275_296780220367719_1048157134_o.jpg",
        1153: "/wp-content/uploads/2015/09/532251_461133050599101_110411014_n.jpg",
        1154: "/wp-content/uploads/2015/09/1378402_767963729916030_5735521928657608664_n.jpg",
        1155: "/wp-content/uploads/2015/09/1455062_767949729917430_2032536127957503491_n.jpg",
        1156: "/wp-content/uploads/2015/09/1471935_767964009916002_4005629508980227686_n.jpg",
        1157: "/wp-content/uploads/2015/09/1489082_771945029517900_2018886777649780568_n.jpg",
        1158: "/wp-content/uploads/2015/09/1601118_767963823249354_6397445097089723745_n.jpg",
        1159: "/wp-content/uploads/2015/09/1620661_767964146582655_8604283614759882071_n.jpg",
        1160: "/wp-content/uploads/2015/09/1620702_767964186582651_3013619733567918518_n.jpg",
        1161: "/wp-content/uploads/2015/09/1622061_838464182865984_9033867675915424487_n.jpg",
        1162: "/wp-content/uploads/2015/09/1798683_653229848056086_1560339769_n.jpg",
        1163: "/wp-content/uploads/2015/09/1901721_767948626584207_8182292131205504472_n.jpg",
        1164: "/wp-content/uploads/2015/09/1926674_767963979916005_1726745312653461030_n.jpg",
        1165: "/wp-content/uploads/2015/09/1975002_767947593250977_8239855109981397015_n.jpg",
        1166: "/wp-content/uploads/2015/09/10354082_767948196584250_6026825629021252623_n.jpg",
        1167: "/wp-content/uploads/2015/09/10362833_712261135486290_3025352146661040942_n.jpg",
        1168: "/wp-content/uploads/2015/09/10365827_767952963250440_6024955052558730307_n.jpg",
        1169: "/wp-content/uploads/2015/09/10367192_712261742152896_8185577875677759920_n.jpg",
        1170: "/wp-content/uploads/2015/09/10376267_771944946184575_7448697068234383085_n.jpg",
        1171: "/wp-content/uploads/2015/09/10386359_767946669917736_3647318301272083162_n.jpg",
        1172: "/wp-content/uploads/2015/09/10387313_767964099915993_7867196195285087355_n.jpg",
        1173: "/wp-content/uploads/2015/09/10403332_767952016583868_5073050187988540049_n.jpg",
        1174: "/wp-content/uploads/2015/09/10408748_767964166582653_5586144465861506311_n.jpg",
        1175: "/wp-content/uploads/2015/09/10428617_856418874403848_2369308583660122488_n.jpg",
        1176: "/wp-content/uploads/2015/09/10433264_767946689917734_5228438080541704769_n.jpg",
        1177: "/wp-content/uploads/2015/09/10435641_712261285486275_7374996317415255694_n.jpg",
        1178: "/wp-content/uploads/2015/09/10457958_838460666199669_2554972200427710647_n.jpg",
        1179: "/wp-content/uploads/2015/09/10458380_767951236583946_6744507175319917492_n.jpg",
        1180: "/wp-content/uploads/2015/09/10481865_767963669916036_2216926297991694421_n.jpg",
        1181: "/wp-content/uploads/2015/09/10502049_771945096184560_2196818459671041043_n.jpg",
        1182: "/wp-content/uploads/2015/09/10514628_767963779916025_2212978587422271738_n.jpg",
        1183: "/wp-content/uploads/2015/09/10520687_767963973249339_837252171335969568_n.jpg",
        1184: "/wp-content/uploads/2015/09/10622733_767951743250562_4900765998451010290_n.jpg",
        1185: "/wp-content/uploads/2015/09/10624912_767951193250617_5311294669585136618_n.jpg",
        1186: "/wp-content/uploads/2015/09/10628303_767949546584115_5373254881404812891_n.jpg",
        1187: "/wp-content/uploads/2015/09/10649499_767964039915999_5323975110848059492_n.jpg",
        1188: "/wp-content/uploads/2015/09/10659321_767963653249371_8471588449625610475_n.jpg",
        1189: "/wp-content/uploads/2015/09/10670129_767963726582697_2509494818531419200_n.jpg",
        1190: "/wp-content/uploads/2015/09/10676291_767951149917288_3897599853727209521_n.jpg",
        1191: "/wp-content/uploads/2015/09/10678796_767948586584211_8942296912023676077_n.jpg",
        1192: "/wp-content/uploads/2015/09/10703921_767963579916045_4399063868032591331_n.jpg",
        1193: "/wp-content/uploads/2015/09/10704186_767963859916017_8844494117885679021_n.jpg",
        1194: "/wp-content/uploads/2015/09/10710917_767946606584409_4125113774399821268_n.jpg",
        1195: "/wp-content/uploads/2015/09/10730767_771944986184571_1017101738183442376_n.jpg",
        1196: "/wp-content/uploads/2015/09/11045438_858266057552463_5669059341296284675_n.jpg",
        1197: "/wp-content/uploads/2015/09/11390047_896904717021930_6039914535399058020_n.jpg",
        1198: "/wp-content/uploads/2015/09/12002780_944009478978120_6084790358667406500_n.jpg",
        1200: "/wp-content/uploads/2015/09/10403028_877148138997588_2771288685534000023_n.jpg",
        1201: "/wp-content/uploads/2015/09/10409388_712261712152899_4520805056043575737_n.jpg",
        1202: "/wp-content/uploads/2015/09/10430381_712260725486331_8905454638307668262_n.jpg",
        1203: "/wp-content/uploads/2015/09/10441139_712259728819764_2725144912956835396_n.jpg",
        1204: "/wp-content/uploads/2015/09/10464370_712260405486363_4354995091919274952_n.jpg",
        1205: "/wp-content/uploads/2015/09/11212755_879054898806912_7606239492939957289_n.jpg",
        1206: "/wp-content/uploads/2015/09/12352_712261268819610_832867683498336150_n.jpg",
        1207: "/wp-content/uploads/2015/09/316253_257863997592675_1065589447_n.jpg",
        1208: "/wp-content/uploads/2015/09/10372070_712262492152821_7908509629804531324_n.jpg",
        1209: "/wp-content/uploads/2015/09/10402868_712261122152958_1837568722256366710_n.jpg",
        1211: "/wp-content/uploads/2015/09/11990471_944009428978125_3848278330912418121_n.jpg",
        1212: "/wp-content/uploads/2015/09/1621814_767951276583942_6380243999071444397_n.jpg",
        1373: "/wp-content/uploads/2015/11/seanweb.jpg",
        1375: "/wp-content/uploads/2016/11/Slide-4.jpg",
        1378: "/wp-content/uploads/2016/11/armbarweb.jpg",
        1379: "/wp-content/uploads/2016/11/classphotoweb.jpg",
        1380: "/wp-content/uploads/2016/11/goofyweb.jpg",
        1382: "/wp-content/uploads/2016/11/guardpassweb.jpg",
        1383: "/wp-content/uploads/2016/11/scrambleweb.jpg",
        1384: "/wp-content/uploads/2016/11/scissorsweepweb.jpg",
    }

    galleries_def = [
        (
            1377,
            "Same School, New Logo",
            "school-new-logo",
            "st-pete-bjj",
            "St. Pete BJJ",
            "Action shots from the St. Pete Brazilian Jiu-Jitsu mats featuring our Sunshine Skyway Enso crest, guard passes, armbars, scissor sweeps, and team training.",
            att_map[1375],
            [1375, 1384, 1383, 1382, 1380, 1379, 1378, 1373],
            1
        ),
        (
            1148,
            "General Training",
            "general-training",
            "st-pete-brazilian-jiu-jitsu",
            "St. Pete Brazilian Jiu-Jitsu",
            "50 candid photos from daily Gi and No-Gi classes, belt promotions, open mats, and team camaraderie at St. Pete BJJ.",
            att_map[1162],
            list(range(1149, 1199)),
            2
        ),
        (
            1199,
            "BJJ Seminars",
            "bjj-seminars",
            "st-pete-bjj",
            "St. Pete BJJ",
            "Special guest seminars, black belt instruction, and packed mats with world-class Brazilian Jiu-Jitsu competitors and professors.",
            att_map[1200],
            [1200, 1201, 1202, 1203, 1204, 1205, 1206, 1207, 1208, 1209],
            3
        ),
        (
            1139,
            "Youth BJJ Classes",
            "youth-bjj-classes",
            "kids-brazilian-jiu-jitsu",
            "Youth & Junior Brazilian Jiu-Jitsu",
            "Historic photos from youth and junior Brazilian Jiu-Jitsu training sessions and self-defense fundamentals.",
            att_map[1143],
            [1140, 1141, 1142, 1143, 1144],
            4
        ),
        (
            1145,
            "Physical Fitness",
            "physical-fitness",
            "st-pete-bjj",
            "St. Pete BJJ",
            "Conditioning, functional strength, flexibility, and full-body workouts on the mats at St. Pete Brazilian Jiu-Jitsu.",
            att_map[1146],
            [1146, 1147],
            5
        ),
        (
            1210,
            "Women's BJJ Classes",
            "womens-bjj-classes",
            "womens-brazilian-jiu-jitsu",
            "Women's Brazilian Jiu-Jitsu",
            "Empowering women with practical leverage-based self-defense, technical grappling, and a supportive training community.",
            att_map[1211],
            [1211, 1212],
            6
        ),
    ]

    for wp_id, title, slug, cat_slug, cat_name, desc, cover, item_ids, sort_ord in galleries_def:
        cur.execute("""
            INSERT INTO galleries (wp_id, title, slug, category_slug, category_name, description, cover_image, photo_count, sort_order, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, (wp_id, title, slug, cat_slug, cat_name, desc, cover, len(item_ids), sort_ord))
        gal_id = cur.lastrowid
        for idx, aid in enumerate(item_ids):
            if aid in att_map:
                cur.execute("""
                    INSERT INTO gallery_photos (gallery_id, wp_attachment_id, title, image_url, sort_order)
                    VALUES (?, ?, ?, ?, ?)
                """, (gal_id, aid, f"{title} — Photo {idx + 1}", att_map[aid], idx + 1))

    # 7. Blog Posts ("Mat Corner")
    cur.execute("DELETE FROM posts")
    posts_data = [
        (
            1522,
            "Come Roll For A Good Cause!",
            "come-roll-good-cause",
            "eventsgatherings",
            "Events & Gatherings",
            "Community fundraiser seminar with Professor Fabiano Estrela supporting Jenn's battle against stage 4 glioblastoma.",
            """<p>Professor Rodrigo&rsquo;s girlfriend Jenn is battling stage 4 glioblastoma brain cancer. Let&rsquo;s come together as a Brazilian Jiu-Jitsu community and support Jenn in her fight.</p>
<p>Professor Fabiano Estrela of Gracie Barra Clearwater will be teaching a special seminar on half-guard attacks utilizing the Lockdown position (in the Gi) to raise support for Jenn&rsquo;s battle against cancer. All proceeds are donated directly to Jenn&rsquo;s fundraiser. Please come out, share the mats, and support a great cause!</p>
<figure class="my-6"><img src="/wp-content/uploads/2017/09/rodrigofundraiser.jpg" alt="Come Roll For A Good Cause Seminar" class="rounded-2xl shadow-lg max-w-lg mx-auto"></figure>""",
            "/wp-content/uploads/2017/09/rodrigofundraiser.jpg",
            "2017-09-22"
        ),
        (
            1508,
            "A Tale of Two Blues!",
            "tale-two-blues",
            "promotions",
            "Belt Promotions",
            "Congratulations to our newest blue belts Eric Cobelens and Sean Watson after competing at the FFBJJ State Championships!",
            """<p>Congratulations to our newest blue belts <strong>Eric Cobelens</strong> and <strong>Sean Watson</strong>! Professor Sean Lynch awarded their blue belts after these two competed for the final time as white belts at the FFBJJ State Championships.</p>
<p>Sean and Eric began their BJJ journey together in January 2016 and have challenged and sharpened each other since day one. Sean has competed multiple times since starting his Jiu-Jitsu journey, winning gold in his division at the IBJJF Miami Spring Open and bronze at the FFBJJ State Championships.</p>
<blockquote>&ldquo;My friend Eric Cobelens received a Jiu-Jitsu voucher and asked me if I wanted to come. Coming from ten years in Taekwondo, I wanted to try something new. I was hooked the first day. Professor Sean Lynch was so welcoming and chill, as were the students. The game changer was Sean saying come as many times as you want until you decide if Jiu-Jitsu is for you—he wasn&rsquo;t trying to make a hard sale, which was so refreshing. Everyone here is humble and strong at the same time.&rdquo; — Sean Watson</blockquote>
<div class="grid grid-cols-1 sm:grid-cols-2 gap-4 my-6">
    <img src="/wp-content/uploads/2017/08/seanrearnaked-web.jpg" alt="Sean Watson Rear Naked Choke" class="rounded-xl shadow">
    <img src="/wp-content/uploads/2017/08/ericezekiel-web.jpg" alt="Eric Cobelens Competition" class="rounded-xl shadow">
</div>
<p>Eric also medaled and won gold for the first time at the FFBJJ State Championship:</p>
<blockquote>&ldquo;It started when I got bored with running and was looking for a real self-defense class. My favorite thing about BJJ is the community you form while training with others. We all feel safe and respected when stepping onto the mat.&rdquo; — Eric Cobelens</blockquote>""",
            "/wp-content/uploads/2017/08/ericandsean-web.jpg",
            "2017-08-24"
        ),
        (
            1501,
            "Jeff Semonick Seminar was a Success!",
            "jeff-semonick-seminar-success",
            "eventsgatherings",
            "Events & Gatherings",
            "Eduardo de Lima's first black belt, Professor Jeff Semonick, visited St. Pete BJJ to share effective old-school Jiu-Jitsu.",
            """<p>Professor Eduardo de Lima&rsquo;s very first black belt, <strong>Professor Jeff Semonick</strong>, visited St. Pete BJJ and taught an outstanding seminar focused on high-percentage, old-school Brazilian Jiu-Jitsu pressure and fundamentals. Thank you to everyone who came out to train, and thank you to Professor Jeff for sharing his Jiu-Jitsu with our academy! OSS!</p>
<div class="grid grid-cols-1 sm:grid-cols-2 gap-4 my-6">
    <img src="/wp-content/uploads/2017/07/sim4web.jpg" alt="Jeff Semonick Seminar at St. Pete BJJ" class="rounded-xl shadow">
    <img src="/wp-content/uploads/2017/07/sem6web.jpg" alt="Seminar Instruction" class="rounded-xl shadow">
    <img src="/wp-content/uploads/2017/07/sem5web.jpg" alt="Technique Drilling" class="rounded-xl shadow">
    <img src="/wp-content/uploads/2017/07/sem3web.jpg" alt="St. Pete BJJ Seminar Group" class="rounded-xl shadow">
</div>""",
            "/wp-content/uploads/2017/07/sim4web.jpg",
            "2017-07-29"
        ),
        (
            1492,
            "Congratulations, Kelly!",
            "congratulations-kelly",
            "promotions",
            "Belt Promotions",
            "Congratulations to Kelly for receiving his brown belt from Professors Eduardo de Lima and Sean Lynch!",
            """<p>Congratulations to <strong>Kelly</strong> on receiving his <strong>brown belt</strong> in Brazilian Jiu-Jitsu from Professors Eduardo de Lima and Sean Lynch!</p>
<p>Kelly started training BJJ in 2012 and has progressed steadily through his technical, high-energy game.</p>
<blockquote>&ldquo;I started because I love MMA, where BJJ was proven to be the most effective individual self-defense system. What I love about BJJ is its real-world effectiveness and the confidence boost it has given me—plus the friendships and bonds I&rsquo;ve made in class, trusting my BJJ brothers and sisters with my safety and well-being.&rdquo; — Kelly</blockquote>""",
            "/wp-content/uploads/2017/02/kellyweb.jpg",
            "2017-02-17"
        ),
        (
            1486,
            "Congratulations, Sebastian!",
            "congratulations-sebastian",
            "promotions",
            "Belt Promotions",
            "Congratulations to St. Pete BJJ's newest purple belt, Sebastian! At 53 years young, he brings a positive spirit and deep practical knowledge to the mats.",
            """<p>Congratulations to St. Pete BJJ&rsquo;s newest purple belt, <strong>Sebastian</strong>! At 53 years young, Sebastian brings a warm, positive attitude to the mats along with a deep and practical understanding of Brazilian Jiu-Jitsu.</p>
<blockquote>&ldquo;At the church I attend, my friend is a brown belt in Jiu-Jitsu and told me I&rsquo;d either love it or hate it. That was three and a half years ago, and I love it. Professor Sean Lynch is remarkable, and these are some of the kindest, most technical people I&rsquo;ve ever met—it&rsquo;s my family. To be able to train with full intensity yet complete control and mutual trust—there&rsquo;s something truly beautiful about that.&rdquo; — Sebastian</blockquote>""",
            "/wp-content/uploads/2017/02/sebastianpromoweb.jpg",
            "2017-02-09"
        ),
        (
            1458,
            "New Year Special",
            "new-year-special",
            "promotions",
            "Academy News & Promotions",
            "Start your Brazilian Jiu-Jitsu journey in St. Petersburg—no prior fitness or martial arts experience required.",
            """<p>The start of the New Year is always a time of reflection and making positive changes in our lives. We believe that Brazilian Jiu-Jitsu changes lives for the better, and it is our mission to share the art with the St. Petersburg community.</p>
<p>If you have been thinking about trying Brazilian Jiu-Jitsu, there is no better time than right now—you don&rsquo;t need to &ldquo;get in shape first&rdquo; before stepping onto the mats. Training BJJ is how you get in shape while learning a lifelong skill!</p>""",
            "/wp-content/uploads/2015/09/newyearaddweb.jpg",
            "2017-01-04"
        ),
        (
            1430,
            "Holiday Cheer",
            "holiday-cheer",
            "eventsgatherings",
            "Events & Gatherings",
            "World champion AJ Agazarm and Professor Greg 'Trog' Soares visit St. Pete BJJ over the holidays as Brian Travis earns his purple belt.",
            """<p>We have been fortunate to welcome several special guests and black belt instructors onto our mats during the holidays, including our friend Greg Soares (&ldquo;Trog&rdquo;) sharing leg-drag passing details in Advanced class, and a surprise visit from World Champion <strong>AJ Agazarm</strong>.</p>
<p>After teaching his latest competition-tested techniques, AJ shared the story of his very first Jiu-Jitsu class years ago when Rich Travis encouraged him to keep training—and then promoted Rich&rsquo;s youngest son, collegiate wrestler <strong>Brian Travis</strong>, on our mats. A wonderful example of how Jiu-Jitsu pays it forward across generations!</p>
<div class="grid grid-cols-1 sm:grid-cols-2 gap-4 my-6">
    <img src="/wp-content/uploads/2016/12/seangregrichweb.jpg" alt="Sean Lynch, Greg Soares and Rich Travis" class="rounded-xl shadow">
    <img src="/wp-content/uploads/2016/12/IMG_3538.jpg" alt="AJ Agazarm and Brian Travis Promotion" class="rounded-xl shadow">
</div>""",
            "/wp-content/uploads/2016/12/seangregrichweb.jpg",
            "2016-12-28"
        ),
        (
            1406,
            "Holiday Schedule",
            "holiday-schedule-2",
            "eventsgatherings",
            "Events & Gatherings",
            "Christmas and New Year's Day academy training schedule update.",
            """<p>Please note our holiday mat schedule for Christmas and New Year&rsquo;s Day. All other classes throughout the week follow our normal St. Pete BJJ class schedule, including the final training session of the year on New Year&rsquo;s Eve!</p>""",
            "/wp-content/uploads/2016/11/Slide-4.jpg",
            "2016-12-19"
        ),
        (
            1394,
            "Closed Saturday December 17th",
            "closed-saturday-december-17th",
            "eventsgatherings",
            "Events & Gatherings",
            "Academy facility upgrades and mat renovations announcement.",
            """<p>Please note we will be closed Saturday, December 17th for exciting academy facility renovations, resuming our regular schedule Sunday evening for Open Mat from 5:00 PM to 7:00 PM.</p>""",
            "/wp-content/uploads/2019/05/Slide2web.jpg",
            "2016-12-14"
        ),
        (
            1388,
            "Christmas Party!",
            "christmas-party",
            "eventsgatherings",
            "Events & Gatherings",
            "Annual St. Pete BJJ academy holiday gathering and UFC watch party.",
            """<p>Our annual St. Pete BJJ school Christmas &amp; UFC gathering is coming up! Please sign up at the front desk so we have a head count for food and refreshments.</p>""",
            "/wp-content/uploads/2016/12/Christmas1.jpg",
            "2016-12-02"
        ),
        (
            1366,
            "Holiday Schedule — Thanksgiving",
            "holiday-schedule",
            "eventsgatherings",
            "Events & Gatherings",
            "Thanksgiving week training schedule and weekend classes.",
            """<p>Just a reminder that the academy is closed on Thanksgiving Day, while all other classes throughout the week and weekend remain on schedule so you can roll off those extra Thanksgiving calories!</p>""",
            "/wp-content/uploads/2016/11/1ekxj1.jpg",
            "2016-11-21"
        ),
        (
            1355,
            "UFC 205!!",
            "ufc-205",
            "eventsgatherings",
            "Events & Gatherings",
            "St. Pete BJJ team gathering to watch historic UFC 205 together.",
            """<p>The St. Pete BJJ team is gathering this Saturday night to watch UFC 205 together! Bring your favorite food or drink and join the team off the mats.</p>""",
            "/wp-content/uploads/2016/11/ufc205.png",
            "2016-11-10"
        ),
        (
            1352,
            "Newest Blue Belt",
            "newest-blue-belt",
            "promotions",
            "Belt Promotions",
            "Recognizing David House on his promotion to Blue Belt at St. Pete BJJ!",
            """<p>We&rsquo;d like to recognize <strong>David House</strong> on his promotion to <strong>Blue Belt</strong>! David is a busy finance professional and father of three young children who consistently makes time in his schedule for Brazilian Jiu-Jitsu. Congratulations David—well earned!</p>""",
            "/wp-content/uploads/2016/11/daveBlue.jpg",
            "2016-11-10"
        ),
        (
            1560,
            "Seminar this Saturday November 5th",
            "hello-world-2",
            "eventsgatherings",
            "Events & Gatherings",
            "Welcoming guest black belt instructor Matt Kirtley for a special Saturday seminar at St. Pete BJJ.",
            """<p>We welcome guest black belt instructor <strong>Matt Kirtley</strong> to St. Pete Brazilian Jiu-Jitsu for a special Saturday afternoon seminar! Clear your schedule and bring a notebook for an awesome afternoon of technical instruction.</p>""",
            "/wp-content/uploads/2015/01/kirtley.jpg",
            "2016-11-01"
        ),
    ]
    cur.executemany("""
        INSERT INTO posts (wp_id, title, slug, category_slug, category_name, excerpt, content, featured_image, published_at, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
    """, posts_data)

    # 8. FAQs (from Contact page + QA page, preserving all original text & links + SEO improvements)
    cur.execute("DELETE FROM faqs")
    faqs_data = [
        (
            "Do you have kids classes?",
            'Sorry, no, we currently do not offer classes for younger children, but we do teach young adults (ages 12 and up) in our classes with a discounted Unlimited Juniors membership ($110/month). For younger children\'s classes in the area, we recommend contacting <a href="https://gbclearwater.com/" target="_blank" rel="noopener" class="text-crimson-500 underline font-semibold">Gracie Barra Clearwater</a> or <a href="https://suncoastbjj.squarespace.com/" target="_blank" rel="noopener" class="text-crimson-500 underline font-semibold">Suncoast BJJ</a>—both offer excellent instruction for children.',
            1
        ),
        (
            "How do I know if jiu-jitsu is right for me?",
            "You don't know until you try, right? Why not come take a free introductory class with us today! Anyone can learn Brazilian Jiu-Jitsu. We have people on our mats from young adults to grandparents all looking to help each other improve. Jiu-Jitsu will improve your fitness, flexibility, stamina, and confidence, and may be one of the most fun and rewarding workouts you can experience.",
            2
        ),
        (
            "What should I expect for my first class?",
            "Expect a warm welcome from our students and staff! Beginners are invited to join in any Fundamentals class to begin their Jiu-Jitsu journey. Here you will be paired with a senior student who will help you work through the techniques being taught. Our Fundamentals class format begins with a short warm-up, followed by a self-defense technique before moving onto more detailed instruction on the topic of the week. The class wraps up with controlled positional sparring for the opportunity to test what you have just learned in a safe, cooperative setting.",
            3
        ),
        (
            "What do/can I wear to class?",
            "For your first class, a clean loaner gi (uniform) will be provided to you free of charge. You can wear athletic shorts or spats under the gi if you prefer, and a t-shirt, rash guard, or sports bra will provide extra comfort. Please arrive 10 minutes before class so we can fit your uniform, and bring a water bottle and small towel. When looking to purchase a gi for yourself, there are tons of choices available on the market—a white or blue gi is preferred, but we really don't care what color you choose to wear as long as it's clean! We also have gis in stock at the academy available for purchase.",
            4
        ),
        (
            "How much does it cost? Are there contracts?",
            "We have a number of affordable payment options and all our prices are published transparently right here on the website—no long-term contracts and no hidden fees ($130/month Unlimited Adult, $110/month Unlimited Juniors ages 12–18, $700 for 6 Months Unlimited, $180 for a 10-Class Package, or $20 for a Single Drop-In). However, it's best to try a free class first to see how you like Jiu-Jitsu, our school, and our environment. Relax—we are lovers of the art, not used car salesmen (no offense to used car salesmen!), and you will never be pressured to join or sign up.",
            5
        ),
        (
            "Do you offer discounts for students, military, or law enforcement?",
            "Yes! We proudly offer membership discounts for students, military/veterans, and law enforcement officers, as well as couples and family memberships.",
            6
        ),
        (
            "Are visitors and BJJ Globetrotters welcome to drop in?",
            "Absolutely! At St. Pete BJJ, we pride ourselves on creating a fun, welcoming, and clean training atmosphere with zero politics. We welcome guests of all skill levels and visitors from other academies ($20 single class drop-in), and we officially recognize BJJ Globetrotters members.",
            7
        ),
    ]
    cur.executemany("INSERT INTO faqs (question, answer, sort_order, status) VALUES (?, ?, ?, 1)", faqs_data)

    # 9. Pages (Exact WordPress slugs & SEO metadata)
    cur.execute("DELETE FROM pages")
    pages_data = [
        (
            1216,
            "St. Pete Brazilian Jiu-Jitsu — St. Petersburg, FL",
            "home",
            "St. Pete Brazilian Jiu-Jitsu | Premier BJJ & Self-Defense Academy in St. Petersburg, FL",
            "Train authentic Brazilian Jiu-Jitsu, No-Gi Submission Grappling, and Judo Takedowns in St. Petersburg, FL under 4th Degree Black Belt Professor Sean Lynch. Free introductory class, no contracts!",
            "Welcome to St. Pete Brazilian Jiu-Jitsu! Whether you're brand new to the art of Brazilian Jiu-Jitsu, a seasoned competitor, or anything in between, at St. Pete BJJ you'll find a welcoming and positive environment to bring your skills to the next level.",
            "index.html"
        ),
        (
            1130,
            "Our Brazilian Jiu-Jitsu Class Schedule — St. Petersburg, Florida",
            "brazilian-jiu-jitsu-class-schedule-saint-petersburg-florida-2",
            "Brazilian Jiu-Jitsu Class Schedule | St. Pete BJJ — St. Petersburg, FL",
            "View the live Brazilian Jiu-Jitsu, Fundamentals, Advanced, No-Gi Grappling, Judo Takedowns, and Open Mat schedule at St. Pete BJJ in St. Petersburg, FL. Text or call (727) 619-4255.",
            "Live ZenPlanner class schedule for St. Pete Brazilian Jiu-Jitsu at 5540 Haines Rd N, St. Petersburg, FL 33714.",
            "schedule.html"
        ),
        (
            1447,
            "Upcoming Schedule",
            "upcoming-schedule",
            "Upcoming Class Schedule & Calendar | St. Pete Brazilian Jiu-Jitsu",
            "Check upcoming classes, open mats, and seminar sessions on the official St. Pete Brazilian Jiu-Jitsu schedule.",
            "Upcoming class schedule and calendar for St. Pete Brazilian Jiu-Jitsu.",
            "schedule.html"
        ),
        (
            1408,
            "Jiu-Jitsu Membership",
            "membership",
            "Jiu-Jitsu Membership & Transparent Pricing | St. Pete BJJ",
            "Transparent Brazilian Jiu-Jitsu membership pricing in St. Petersburg, FL. First introductory class is free! $130/mo Unlimited, $110/mo Juniors, $20 Drop-ins. Month-to-month, no contracts.",
            "Transparent month-to-month Brazilian Jiu-Jitsu memberships and class packages at St. Pete BJJ.",
            "membership.html"
        ),
        (
            1786,
            "Memberships",
            "memberships",
            "Memberships & Online Registration | St. Pete Brazilian Jiu-Jitsu",
            "Sign up online for St. Pete Brazilian Jiu-Jitsu memberships, 10-class packages, or drop-ins via ZenPlanner. Month-to-month with no contracts.",
            "Online membership portal and registration for St. Pete Brazilian Jiu-Jitsu.",
            "membership.html"
        ),
        (
            1230,
            "Instructors",
            "st-pete-jiu-jitsu-professors",
            "Black Belt Instructors & Professors | St. Pete Brazilian Jiu-Jitsu",
            "Meet the black belt professors and coaches at St. Pete Brazilian Jiu-Jitsu in St. Petersburg, FL, led by 4th Degree Black Belt Professor Sean Lynch.",
            "Meet our lineage black belt professors and specialized grappling coaches at St. Pete Brazilian Jiu-Jitsu.",
            "instructors.html"
        ),
        (
            302,
            "Our Team",
            "staff",
            "Our Coaching Team & Black Belt Lineage | St. Pete Brazilian Jiu-Jitsu",
            "Meet the coaching staff, black belt professors, and instructors at St. Pete Brazilian Jiu-Jitsu in St. Petersburg, FL.",
            "Meet the coaching staff at St. Pete Brazilian Jiu-Jitsu.",
            "instructors.html"
        ),
        (
            1214,
            "St. Pete BJJ — Photo Galleries",
            "st-pete-bjj-photo-galleries",
            "Academy Photo Galleries | St. Pete Brazilian Jiu-Jitsu",
            "Browse 70+ photos from Gi and No-Gi classes, belt promotions, seminars, and team training on the mats at St. Pete Brazilian Jiu-Jitsu.",
            "Explore photo galleries from training, seminars, and belt promotions at St. Pete BJJ.",
            "galleries.html"
        ),
        (
            11,
            "Contact St. Pete BJJ",
            "contact",
            "Contact St. Pete BJJ & Book Your Free Class | 5540 Haines Rd N, St. Petersburg, FL",
            "Book your free introductory Brazilian Jiu-Jitsu class at St. Pete BJJ! Located at 5540 Haines Rd N, St. Petersburg, FL 33714. Text or call (727) 619-4255.",
            "Contact St. Pete Brazilian Jiu-Jitsu at 5540 Haines Rd N, St. Petersburg, FL 33714 or register for your free trial class.",
            "contact.html"
        ),
        (
            1308,
            "Fundamentals Classes",
            "fundamentals-classes",
            "BJJ Fundamentals Classes (16-Week Curriculum) | St. Pete Brazilian Jiu-Jitsu",
            "At St. Pete BJJ, our 16-week Fundamentals Classes are designed for beginners and experienced students alike to master core Brazilian Jiu-Jitsu self-defense, escapes, sweeps, and submissions.",
            "16-week Fundamentals Brazilian Jiu-Jitsu curriculum at St. Pete BJJ.",
            "program_detail.html"
        ),
        (
            1317,
            "Advanced Classes",
            "advanced-classes",
            "Advanced BJJ & Competition Classes | St. Pete Brazilian Jiu-Jitsu",
            "Our Advanced Brazilian Jiu-Jitsu classes in St. Petersburg, FL combine self-defense and modern sport Jiu-Jitsu strategies, takedowns, and live sparring for 3-stripe white belts and above.",
            "Advanced Brazilian Jiu-Jitsu curriculum and live sparring at St. Pete BJJ.",
            "program_detail.html"
        ),
        (
            46,
            "Mat Corner — Academy News & Promotions",
            "news",
            "Mat Corner — Belt Promotions, Seminars & Academy News | St. Pete BJJ",
            "Read the latest belt promotions, seminar recaps, competition results, and community stories from the mats at St. Pete Brazilian Jiu-Jitsu.",
            "Mat Corner: news, belt promotions, and seminar updates from St. Pete BJJ.",
            "news.html"
        ),
        (
            280,
            "Frequently Asked Questions",
            "qa",
            "Frequently Asked Questions (FAQ) | St. Pete Brazilian Jiu-Jitsu",
            "Everything you need to know before your first free Brazilian Jiu-Jitsu class at St. Pete BJJ: what to wear, free loaner gi, transparent pricing, and class expectations.",
            "Frequently asked questions about starting Brazilian Jiu-Jitsu at St. Pete BJJ.",
            "faq.html"
        ),
    ]
    cur.executemany("""
        INSERT INTO pages (wp_id, title, slug, meta_title, meta_description, content, template, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 1)
    """, pages_data)

    # 10. Legacy Redirects (Query strings, old demo routes, convenience aliases)
    cur.execute("DELETE FROM legacy_redirects")
    redirects_data = [
        ("/?page_id=11", "/contact", 301),
        ("/?page_id=1308", "/fundamentals-classes", 301),
        ("/?page_id=1317", "/advanced-classes", 301),
        ("/?page_id=1130", "/brazilian-jiu-jitsu-class-schedule-saint-petersburg-florida-2", 301),
        ("/?page_id=1214", "/st-pete-bjj-photo-galleries", 301),
        ("/?page_id=1230", "/st-pete-jiu-jitsu-professors", 301),
        ("/?page_id=1408", "/membership", 301),
        ("/?page_id=1786", "/memberships", 301),
        ("/home", "/", 301),
        ("/schedule", "/brazilian-jiu-jitsu-class-schedule-saint-petersburg-florida-2", 301),
        ("/instructors", "/st-pete-jiu-jitsu-professors", 301),
        ("/professors", "/st-pete-jiu-jitsu-professors", 301),
        ("/photos", "/st-pete-bjj-photo-galleries", 301),
        ("/faq", "/qa", 301),
        ("/wp-sitemap.xml", "/sitemap.xml", 301),
        ("/sitemap_index.xml", "/sitemap.xml", 301),
    ]
    cur.executemany("""
        INSERT INTO legacy_redirects (old_path, new_path, http_status)
        VALUES (?, ?, ?)
    """, redirects_data)

    conn.commit()
    conn.close()
    print(f"Database initialized successfully at {DB_PATH}")


if __name__ == "__main__":
    init_db()
