from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from app.config import settings, STATIC_DIR, UPLOADS_DIR, DB_PATH
from app.database import ensure_cms_schema
from app.middleware import CanonicalAndSecurityMiddleware
from app.routers import sitemap, quote, admin, chat, frontend
from app.services.geo_security import load_geo_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not DB_PATH.exists():
        from scripts.build_db import init_db
        init_db()
    ensure_cms_schema()
    load_geo_db()
    yield


app = FastAPI(
    title="St. Pete Brazilian Jiu-Jitsu",
    description="Premier Brazilian Jiu-Jitsu, No-Gi Submission Grappling & Self-Defense Academy in St. Petersburg, FL",
    version="2.0.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
)

# Mount static assets and preserve 100% of /wp-content/uploads/... URLs
STATIC_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/wp-content/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="wp_uploads")

# Middleware
app.add_middleware(CanonicalAndSecurityMiddleware)
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY, max_age=86400 * 7)

# Routers
app.include_router(sitemap.router)
app.include_router(quote.router)
app.include_router(admin.router)
app.include_router(chat.router)
app.include_router(frontend.router)
