from app.config import settings
from app.database import get_site_settings


def get_stripe_status() -> dict:
    """Returns current Stripe payment configuration status (disabled by default)."""
    cfg = get_site_settings()
    enabled = cfg.get("stripe_enabled", "0") == "1" or settings.STRIPE_ENABLED
    pub_key = cfg.get("stripe_publishable_key") or settings.STRIPE_PUBLISHABLE_KEY
    return {
        "enabled": enabled and bool(pub_key),
        "publishable_key": pub_key,
        "mode": "live" if pub_key.startswith("pk_live_") else "test",
    }
