# St. Pete Brazilian Jiu-Jitsu (`stpetebjj.com`) — FastAPI + Python Edition

Modern agency-tier Python & FastAPI web platform for **St. Pete Brazilian Jiu-Jitsu** (`5540 Haines Rd N, St. Petersburg, FL 33714` • `(727) 619-4255`).

## Key Features
- **100% URL, Slug, Image Path & Source Copy Parity**: Preserves every original WordPress page slug, Mat Corner post slug, gallery slug (`/dt_gallery/...`), instructor profile (`/dt_team/...`), category archive, and `/wp-content/uploads/...` media file so zero SEO ranking is lost.
- **Canonical Domain Enforcement**: Automatically 301-redirects `stpetebrazilianjiujitsu.test` -> `www.stpetebrazilianjiujitsu.test` and `stpetebjj.com` -> `www.stpetebjj.com`.
- **Embedded ZenPlanner Schedule & Membership Tools**: Uses the exact ZenPlanner Studio widgets (`calendar`, `freetrial`, `membership`) and ZenPlanner Member Registration portal from the original site.
- **Geo-IP Firewall, WAF & Google reCAPTCHA v3**: Blocks malicious foreign IPs and automated exploit probes (`/.env`, `/wp-admin`, `/xmlrpc.php`) while allowing US/CA/MX/PR visitors and verified search engine crawlers (`Googlebot`, `Bingbot`).
- **Admin Console (`/admin-25263863535`)**: Manage free class inquiries, membership rates, instructors, security firewall logs, and one-click ZIP backups.

## Local Development (`127.0.0.1:48828`)
```bash
docker compose up -d --build
```
- **Frontend**: `http://www.stpetebrazilianjiujitsu.test:48828`
- **Admin Console**: `http://www.stpetebrazilianjiujitsu.test:48828/admin-25263863535` (`admin` / `StPeteBJJ2026!`)
