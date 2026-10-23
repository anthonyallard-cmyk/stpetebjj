import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
STATIC_DIR = BASE_DIR / "static"
UPLOADS_DIR = STATIC_DIR / "uploads"
TEMPLATES_DIR = BASE_DIR / "app" / "templates"
BACKUPS_DIR = BASE_DIR / "backups"

DATA_DIR.mkdir(parents=True, exist_ok=True)
BACKUPS_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "stpetebjj.db"


class Settings:
    SITE_NAME: str = os.getenv("SITE_NAME", "St. Pete Brazilian Jiu-Jitsu")
    DOMAIN: str = os.getenv("DOMAIN", "www.stpetebjj.com")
    LOCAL_DOMAIN: str = os.getenv("LOCAL_DOMAIN", "www.stpetebrazilianjiujitsu.test")
    BASE_URL: str = os.getenv("BASE_URL", "https://www.stpetebjj.com")

    SECRET_KEY: str = os.getenv("SECRET_KEY", "spbjj-super-secret-session-key-2026-x99b")
    ADMIN_PATH: str = os.getenv("ADMIN_PATH", "/admin-25263863535")

    # Contact Info
    PHONE_DISPLAY: str = "(727) 619-4255"
    PHONE_VANITY: str = "727.619.4BJJ"
    PHONE_RAW: str = "17276194255"
    EMAIL_CONTACT: str = os.getenv("EMAIL_CONTACT", "info@stpetebjj.com")
    EMAIL_QUOTES: str = os.getenv("EMAIL_QUOTES", "info@stpetebjj.com, camaraogb@gmail.com")
    ADDRESS: str = "5540 Haines Rd N, St. Petersburg, FL 33714"
    WAIVER_URL: str = "/wp-content/uploads/2017/01/Waiver.pdf"

    # ZenPlanner Studio Widget & Portal Configuration
    ZENPLANNER_PARTITION_KEY: str = "e5375747-e005-479f-bf4c-a6963ec54790"
    ZENPLANNER_CALENDAR_ID: str = "6c9eb298-1fa2-455c-b545-e89677f1cd74"
    ZENPLANNER_FREETRIAL_ID: str = "39e9efab-01e0-43e6-8211-e2b1288fa494"
    ZENPLANNER_MEMBERSHIP_ID: str = "ca2040c1-5909-4d97-871e-9f13e6fdab19"
    ZENPLANNER_PORTAL_IFRAME: str = "https://stpetebjj.zenplanner.com/zenplanner/portal/sign-up-now.cfm?type=Membership&FRAME=true"
    ZENPLANNER_PORTAL_URL: str = "https://stpetebjj.zenplanner.com/zenplanner/portal/sign-up-now.cfm"
    ZENPLANNER_DROPIN_SINGLE_URL: str = "https://stpetebjj.sites.zenplanner.com/retail-product.cfm?productId=E7951814-35D2-433C-80F1-D818ED627B01"
    ZENPLANNER_DROPIN_10PACK_URL: str = "https://stpetebjj.sites.zenplanner.com/retail-product.cfm?productId=40DB5254-3438-470D-81B8-903F19D618BE"

    # SMTP Settings
    SMTP_HOST: str = os.getenv("SMTP_HOST", "localhost")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "25"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASS: str = os.getenv("SMTP_PASS", "")
    SMTP_FROM: str = os.getenv("SMTP_FROM", "noreply@stpetebjj.com")

    # Google reCAPTCHA v3
    RECAPTCHA_SITE_KEY: str = os.getenv("RECAPTCHA_SITE_KEY", "6LeUH_0tAAAAAJ8M_xd73QUHMo4Vc8lQ32oMcyey")
    RECAPTCHA_SECRET_KEY: str = os.getenv("RECAPTCHA_SECRET_KEY", "6LeUH_0tAAAAAL7nwIF2-pNH6UVUe7Pl3j6RuZNK")
    RECAPTCHA_MIN_SCORE: float = float(os.getenv("RECAPTCHA_MIN_SCORE", "0.4"))

    # Stripe Integration Stub (Disabled by default; ready for future activation)
    STRIPE_ENABLED: bool = os.getenv("STRIPE_ENABLED", "false").lower() == "true"
    STRIPE_PUBLISHABLE_KEY: str = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
    STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")

    # IndexNow Key
    INDEXNOW_KEY: str = os.getenv("INDEXNOW_KEY", "spbjj94810294810294810294810")


settings = Settings()
