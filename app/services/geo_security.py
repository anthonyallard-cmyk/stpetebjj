import bisect
import csv
import ipaddress
import logging
from pathlib import Path
from typing import Tuple, Optional
from app.config import DATA_DIR
from app.database import db_cursor, get_site_settings

logger = logging.getLogger(__name__)

GEO_CSV_PATH = DATA_DIR / "ipv4_country.csv"

_ip_starts: list[int] = []
_ip_ends: list[int] = []
_ip_countries: list[str] = []
_geo_loaded: bool = False

# Known legitimate search engine & social crawler User-Agent substrings
SEARCH_BOT_SIGNATURES = (
    "googlebot",
    "bingbot",
    "slurp",
    "duckduckbot",
    "applebot",
    "facebookexternalhit",
    "facebot",
    "twitterbot",
    "linkedinbot",
    "pinterestbot",
    "indexnow",
)

# Common exploit scanner / malicious bot path patterns
SCANNER_PATH_PATTERNS = (
    "/wp-admin",
    "/wp-login.php",
    "/xmlrpc.php",
    "/.env",
    "/.git",
    "/phpmyadmin",
    "/pma",
    "/vendor/phpunit",
    "/cgi-bin/",
    "/boaform/",
    "/actuator/",
    "/wp-includes/wlwmanifest.xml",
    "/wp-config",
)


def load_geo_db():
    """Loads IPv4 country ranges into sorted lists for O(log N) lookup."""
    global _ip_starts, _ip_ends, _ip_countries, _geo_loaded
    if _geo_loaded:
        return
    if not GEO_CSV_PATH.exists():
        logger.warning(f"GeoIP CSV not found at {GEO_CSV_PATH}")
        _geo_loaded = True
        return

    starts = []
    ends = []
    countries = []
    try:
        with open(GEO_CSV_PATH, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) < 3:
                    continue
                try:
                    r0, r1 = row[0].strip(), row[1].strip()
                    s_int = int(r0) if r0.isdigit() else int(ipaddress.IPv4Address(r0))
                    e_int = int(r1) if r1.isdigit() else int(ipaddress.IPv4Address(r1))
                    cc = row[2].strip().upper()
                    starts.append(s_int)
                    ends.append(e_int)
                    countries.append(cc)
                except Exception:
                    continue
        _ip_starts = starts
        _ip_ends = ends
        _ip_countries = countries
        _geo_loaded = True
        logger.info(f"Loaded {len(_ip_starts)} IPv4 GeoIP ranges.")
    except Exception as e:
        logger.error(f"Error loading GeoIP CSV: {e}")
        _geo_loaded = True


def lookup_country(ip_str: str) -> str:
    """Returns 2-letter ISO country code or 'LOCAL' / 'UNKNOWN'."""
    if not ip_str:
        return "LOCAL"
    try:
        ip_obj = ipaddress.ip_address(ip_str)
        if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local:
            return "LOCAL"
        if isinstance(ip_obj, ipaddress.IPv6Address):
            if ip_obj.ipv4_mapped:
                ip_obj = ip_obj.ipv4_mapped
            else:
                return "US"
        load_geo_db()
        if not _ip_starts:
            return "UNKNOWN"
        ip_int = int(ip_obj)
        idx = bisect.bisect_right(_ip_starts, ip_int) - 1
        if idx >= 0 and _ip_starts[idx] <= ip_int <= _ip_ends[idx]:
            return _ip_countries[idx]
        return "UNKNOWN"
    except Exception:
        return "UNKNOWN"


def is_ip_in_list(ip_str: str, raw_list: str) -> bool:
    if not raw_list or not ip_str:
        return False
    try:
        target = ipaddress.ip_address(ip_str)
    except ValueError:
        return False

    for token in raw_list.replace("\n", ",").split(","):
        entry = token.strip()
        if not entry:
            continue
        try:
            if "/" in entry:
                if target in ipaddress.ip_network(entry, strict=False):
                    return True
            else:
                if target == ipaddress.ip_address(entry):
                    return True
        except ValueError:
            continue
    return False


def log_security_event(ip_str: str, country: str, path: str, reason: str, user_agent: str):
    try:
        with db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO security_events (ip_address, country_code, request_path, reason, user_agent)
                VALUES (?, ?, ?, ?, ?)
                """,
                (ip_str, country, path[:255], reason[:120], (user_agent or "")[:255]),
            )
    except Exception as e:
        logger.error(f"Failed to log security event: {e}")


def evaluate_request_security(
    ip_str: str, path: str, user_agent: str
) -> Tuple[bool, Optional[str], str]:
    """
    Evaluates whether a request should be allowed.
    Returns (allowed: bool, block_reason: Optional[str], country_code: str)
    """
    country = lookup_country(ip_str)
    if country == "LOCAL":
        return True, None, country

    cfg = get_site_settings()
    whitelist = cfg.get("geo_ip_whitelist", "")
    blacklist = cfg.get("geo_ip_blacklist", "")

    if is_ip_in_list(ip_str, whitelist):
        return True, None, country

    if is_ip_in_list(ip_str, blacklist):
        return False, "IP Blacklisted", country

    # Check WAF exploit scanner paths
    if cfg.get("waf_block_scanners", "1") == "1":
        lower_path = path.lower()
        for pat in SCANNER_PATH_PATTERNS:
            if lower_path.startswith(pat) or pat in lower_path:
                return False, f"WAF Exploit Probe ({pat})", country

    # Check Geo-IP Blocking
    if cfg.get("geo_block_enabled", "1") == "1":
        # Allow verified search engine crawler signatures if configured
        if cfg.get("geo_allow_search_bots", "1") == "1" and user_agent:
            ua_lower = user_agent.lower()
            if any(bot in ua_lower for bot in SEARCH_BOT_SIGNATURES):
                return True, None, country

        allowed_raw = cfg.get("geo_allowed_countries", "US, CA, MX, PR")
        allowed_set = {c.strip().upper() for c in allowed_raw.split(",") if c.strip()}
        if country not in allowed_set and country != "UNKNOWN":
            return False, f"Foreign Geo-IP Blocked ({country})", country

    return True, None, country
