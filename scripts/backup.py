"""Standalone CLI backup script for St. Pete Brazilian Jiu-Jitsu."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.backup_service import create_backup_archive

if __name__ == "__main__":
    info = create_backup_archive()
    print(f"Created backup: {info['filename']} ({info['size_kb']} KB)")
