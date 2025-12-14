#!/usr/bin/env python3
"""Build x64 backend using Rosetta (for building x64 on ARM Mac)"""
import os
import sys
import subprocess
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
BINARIES_DIR = SCRIPT_DIR.parent / "src-tauri" / "binaries"

def main():
    print("=" * 60)
    print("Building x64 backend via Rosetta")
    print("=" * 60)
    
    # Ensure binaries dir exists
    BINARIES_DIR.mkdir(parents=True, exist_ok=True)
    
    output_name = "xfactor-backend-x86_64-apple-darwin"
    output_path = BINARIES_DIR / output_name
    
    run_backend = SCRIPT_DIR / "run_backend.py"
    
    cmd = [
        "arch", "-x86_64", sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name", output_name,
        "--distpath", str(BINARIES_DIR),
        "--workpath", str(SCRIPT_DIR.parent / "build"),
        "--specpath", str(SCRIPT_DIR.parent / "build"),
        # Collect all submodules for all key packages
        # Web framework
        "--collect-all", "uvicorn",
        "--collect-all", "uvloop",
        "--collect-all", "fastapi",
        "--collect-all", "starlette",
        "--collect-all", "pydantic",
        "--collect-all", "pydantic_settings",
        "--collect-all", "python_multipart",
        # HTTP/WebSocket clients
        "--collect-all", "httpx",
        "--collect-all", "httpcore",
        "--collect-all", "h11",
        "--collect-all", "websockets",
        "--collect-all", "websocket",
        "--collect-all", "aiohttp",
        "--collect-all", "aiosignal",
        "--collect-all", "aiohappyeyeballs",
        "--collect-all", "requests",
        "--collect-all", "urllib3",
        # Data processing
        "--collect-all", "pandas",
        "--collect-all", "pandas_ta",
        "--collect-all", "ta",
        "--collect-all", "numpy",
        "--collect-all", "polars",
        # Trading
        "--collect-all", "ib_insync",
        # Database
        "--collect-all", "sqlalchemy",
        "--collect-all", "asyncpg",
        "--collect-all", "redis",
        # Async
        "--collect-all", "anyio",
        "--collect-all", "sniffio",
        "--collect-all", "nest_asyncio",
        # Scheduling
        "--collect-all", "apscheduler",
        # Scraping/Parsing
        "--collect-all", "beautifulsoup4",
        "--collect-all", "bs4",
        "--collect-all", "feedparser",
        "--collect-all", "lxml",
        # Other utilities
        "--collect-all", "orjson",
        "--collect-all", "python_dotenv",
        "--collect-all", "loguru",
        "--collect-all", "pytz",
        "--collect-all", "dateutil",
        "--collect-all", "certifi",
        "--collect-all", "yaml",
        # AI/ML packages (large but needed)
        "--collect-all", "torch",
        "--collect-all", "transformers",
        "--collect-all", "openai",
        # Exclude unused packages
        "--exclude-module", "tkinter",
        "--exclude-module", "matplotlib",
        "--exclude-module", "PIL",
        "--exclude-module", "cv2",
        "--exclude-module", "tensorflow",
        "--exclude-module", "keras",
        "--exclude-module", "jax",
        "--exclude-module", "flax",
        "--exclude-module", "optax",
        "--exclude-module", "IPython",
        "--exclude-module", "jupyter",
        "--exclude-module", "notebook",
        "--exclude-module", "playwright",
        # Clean build
        "--clean",
        "--noconfirm",
        str(run_backend)
    ]
    
    print(f"\nRunning: {' '.join(cmd[:8])}...")
    os.chdir(PROJECT_ROOT)
    result = subprocess.run(cmd)
    
    if result.returncode == 0 and output_path.exists():
        os.chmod(output_path, 0o755)
        size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"\n[OK] x64 backend built successfully!")
        print(f"     Path: {output_path}")
        print(f"     Size: {size_mb:.1f} MB")
    else:
        print("\n[ERROR] Build failed")
        return 1
    
    print("\n" + "=" * 60)
    print("x64 backend build complete!")
    print("=" * 60)
    return 0

if __name__ == "__main__":
    sys.exit(main())
