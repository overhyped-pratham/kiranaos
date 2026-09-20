import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.app.config import settings
import uvicorn

if __name__ == "__main__":
    # Force UTF-8 for console output on Windows
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8')
    print(f"Starting KiranaOS Operator Backend on {settings.HOST}:{settings.PORT}...")
    uvicorn.run(
        "backend.app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False
    )
