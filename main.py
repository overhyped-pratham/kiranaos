"""Root entrypoint for deployment platforms (Vercel, Render, AWS, etc.)"""
import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.app.main import app

__all__ = ["app"]
