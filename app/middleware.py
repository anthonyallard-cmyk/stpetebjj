from fastapi import Request
from fastapi.responses import RedirectResponse, HTMLResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.database import db_cursor
from app.services.geo_security import evaluate_request_security, log_security_event


PAGE_ID_MAP = {
    "11": "/contact",
    "46": "/news",
    "280": "/qa",
    "302": "/staff",
    "1130": "/brazilian-jiu-jitsu-class-schedule-saint-petersburg-florida-2",
    "1214": "/st-pete-bjj-photo-galleries",
    "1216": "/",
    "1230": "/st-pete-jiu-jitsu-professors",
    "1308": "/fundamentals-classes",
    "1317": "/advanced-classes",
    "1408": "/membership",
    "1447": "/upcoming-schedule",
    "1786": "/memberships",
}


def get_client_ip(request: Request) -> str:
    cf_ip = request.headers.get("cf-connecting-ip")
    if cf_ip:
        return cf_ip.strip()
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"


class CanonicalAndSecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        host_header = request.headers.get("host", "")
        hostname = host_header.split(":")[0].lower()
        port_part = f":{host_header.split(':')[1]}" if ":" in host_header else ""
        path = request.url.path
        query = request.url.query

        # 1. Canonical www. redirect for root domains
        if hostname in ("stpetebrazilianjiujitsu.test", "stpetebjj.com"):
            target_host = f"www.{hostname}{port_part}"
            scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
            target_url = f"{scheme}://{target_host}{path}"
            if query:
                target_url += f"?{query}"
            return RedirectResponse(url=target_url, status_code=301)

        # 2. Geo-IP & WAF Security Check (skip static assets for speed unless scanner path)
        if not path.startswith("/static/") and not path.startswith("/wp-content/"):
            client_ip = get_client_ip(request)
            ua = request.headers.get("user-agent", "")
            # Allow test header override for automated verification of Geo-IP blocking
            test_ip = request.headers.get("x-test-client-ip")
            eval_ip = test_ip.strip() if test_ip else client_ip

            allowed, reason, country = evaluate_request_security(eval_ip, path, ua)
            if not allowed:
                log_security_event(eval_ip, country, path, reason or "Blocked", ua)
                return HTMLResponse(
                    content=f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>403 Access Restricted — St. Pete BJJ</title>
<style>body{{background:#09090B;color:#FAFAFA;font-family:system-ui,sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;text-align:center}}
.box{{max-width:480px;padding:36px;background:#18181B;border:1px solid #27272A;border-top:4px solid #CE1E36;border-radius:16px}}
h1{{margin:0 0 12px;font-size:22px;color:#FFFFFF}}p{{color:#A1A1AA;font-size:14px;line-height:1.6}}</style></head>
<body><div class="box"><h1>Access Restricted</h1>
<p>Your connection ({country}) was blocked by our automated security firewall ({reason}). If you are in the United States and believe this is an error, please call or text (727) 619-4255.</p>
</div></body></html>""",
                    status_code=403,
                )

        # 3. Legacy WordPress ?page_id=... redirects
        if path == "/" and "page_id" in request.query_params:
            pid = request.query_params.get("page_id", "").strip()
            if pid in PAGE_ID_MAP:
                return RedirectResponse(url=PAGE_ID_MAP[pid], status_code=301)

        # 4. Trailing slash normalization (except root '/')
        if len(path) > 1 and path.endswith("/") and not path.startswith("/static/") and not path.startswith("/wp-content/"):
            clean_path = path.rstrip("/")
            target = f"{clean_path}?{query}" if query else clean_path
            return RedirectResponse(url=target, status_code=301)

        # 5. Check Legacy Redirects table
        if not path.startswith("/static/") and not path.startswith("/wp-content/") and not path.startswith("/api/"):
            try:
                with db_cursor() as cur:
                    cur.execute(
                        "SELECT id, new_path, http_status FROM legacy_redirects WHERE old_path = ?",
                        (path,),
                    )
                    row = cur.fetchone()
                    if row:
                        cur.execute(
                            "UPDATE legacy_redirects SET hit_count = hit_count + 1 WHERE id = ?",
                            (row["id"],),
                        )
                        return RedirectResponse(url=row["new_path"], status_code=row["http_status"] or 301)
            except Exception:
                pass

        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response
