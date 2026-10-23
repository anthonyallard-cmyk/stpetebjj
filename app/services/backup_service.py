import zipfile
from datetime import datetime
from pathlib import Path
from app.config import BASE_DIR, BACKUPS_DIR, DB_PATH


def create_backup_archive() -> dict:
    """Creates a timestamped ZIP backup of the SQLite database and configuration."""
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_name = f"stpetebjj_backup_{ts}.zip"
    zip_path = BACKUPS_DIR / zip_name

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        if DB_PATH.exists():
            zf.write(DB_PATH, arcname="data/stpetebjj.db")
        for rel in ["requirements.txt", "Dockerfile", "docker-compose.yml"]:
            fp = BASE_DIR / rel
            if fp.exists():
                zf.write(fp, arcname=rel)

    size_kb = round(zip_path.stat().st_size / 1024, 1)
    return {
        "filename": zip_name,
        "path": str(zip_path),
        "size_kb": size_kb,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def list_backups() -> list[dict]:
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    items = []
    for f in sorted(BACKUPS_DIR.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True):
        st = f.stat()
        items.append({
            "filename": f.name,
            "size_kb": round(st.st_size / 1024, 1),
            "created_at": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        })
    return items
