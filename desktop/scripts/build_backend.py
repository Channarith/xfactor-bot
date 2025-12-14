#!/usr/bin/env python3
"""
Build the XFactor Bot backend as a standalone executable
Uses PyInstaller to create a single binary that can be bundled with Tauri
"""

import os
import sys
import shutil
import subprocess
import platform
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DESKTOP_DIR = SCRIPT_DIR.parent
TAURI_DIR = DESKTOP_DIR / "src-tauri"
BINARIES_DIR = TAURI_DIR / "binaries"

def get_target_triple():
    """Get the Rust target triple for the current platform"""
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    if system == "darwin":
        if machine == "arm64":
            return "aarch64-apple-darwin"
        else:
            return "x86_64-apple-darwin"
    elif system == "windows":
        return "x86_64-pc-windows-msvc"
    elif system == "linux":
        if machine == "aarch64":
            return "aarch64-unknown-linux-gnu"
        else:
            return "x86_64-unknown-linux-gnu"
    else:
        raise RuntimeError(f"Unsupported platform: {system}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Build XFactor Bot Backend')
    parser.add_argument('--target', type=str, help='Target triple (e.g., aarch64-apple-darwin, x86_64-apple-darwin)')
    args = parser.parse_args()
    
    print("=" * 60)
    print("Building XFactor Bot Backend")
    print("=" * 60)
    
    # Check if PyInstaller is installed
    try:
        import PyInstaller
        print(f"[OK] PyInstaller version: {PyInstaller.__version__}")
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
    
    # Create binaries directory
    BINARIES_DIR.mkdir(parents=True, exist_ok=True)
    
    # Get target triple (use argument if provided, otherwise auto-detect)
    target_triple = args.target if args.target else get_target_triple()
    print(f"[OK] Target: {target_triple}")
    
    # Check if cross-compiling (PyInstaller can only build for current platform)
    current_triple = get_target_triple()
    if target_triple != current_triple:
        print(f"[WARN] Cross-compilation requested ({target_triple}) but running on {current_triple}")
        print(f"       PyInstaller can only build for the current platform.")
        print(f"       Creating a placeholder for {target_triple}...")
        
        # Create a placeholder script that will be replaced with actual binary
        placeholder_path = BINARIES_DIR / f"xfactor-backend-{target_triple}"
        with open(placeholder_path, 'w') as f:
            f.write("#!/bin/sh\\necho 'This is a placeholder. Build on the target platform.'\\n")
        if platform.system() != "Windows":
            os.chmod(placeholder_path, 0o755)
        print(f"       Created placeholder: {placeholder_path}")
        return
    
    # Output binary name (Tauri expects name-target format)
    if platform.system() == "Windows":
        binary_name = f"xfactor-backend-{target_triple}.exe"
    else:
        binary_name = f"xfactor-backend-{target_triple}"
    
    output_path = BINARIES_DIR / binary_name
    
    # Build with PyInstaller
    print(f"\nBuilding backend executable...")
    print(f"Output: {output_path}")
    
    # Change to project root for imports to work
    os.chdir(PROJECT_ROOT)
    
    # PyInstaller command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name", f"xfactor-backend-{target_triple}",
        "--distpath", str(BINARIES_DIR),
        "--workpath", str(DESKTOP_DIR / "build"),
        "--specpath", str(DESKTOP_DIR / "build"),
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
        "--collect-all", "jinja2",
        "--collect-all", "click",
        "--collect-all", "tqdm",
        "--collect-all", "regex",
        "--collect-all", "tokenizers",
        "--collect-all", "safetensors",
        "--collect-all", "huggingface_hub",
        "--collect-all", "numba",
        "--collect-all", "langdetect",
        "--collect-all", "deep_translator",
        "--collect-all", "openpyxl",
        "--collect-all", "praw",
        "--collect-all", "prawcore",
        "--collect-all", "psycopg2",
        "--collect-all", "watchfiles",
        "--collect-all", "httptools",
        "--collect-all", "attrs",
        "--collect-all", "multidict",
        "--collect-all", "frozenlist",
        "--collect-all", "yarl",
        "--collect-all", "idna",
        "--collect-all", "charset_normalizer",
        "--collect-all", "tenacity",
        # AI/ML API clients (configurable via admin panel)
        "--collect-all", "openai",
        "--collect-all", "anthropic",
        # Exclude local ML frameworks (use API-based LLMs instead)
        "--exclude-module", "torch",
        "--exclude-module", "transformers",
        "--exclude-module", "tensorflow",
        "--exclude-module", "keras",
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
        # Entry point
        str(SCRIPT_DIR / "run_backend.py"),
    ]
    
    # Add console flag for Windows
    if platform.system() != "Windows":
        cmd.insert(3, "--windowed")  # No console on macOS/Linux
    
    print(f"\nRunning: {' '.join(cmd[:10])}...")
    
    result = subprocess.run(cmd, capture_output=False)
    
    if result.returncode != 0:
        print(f"\n[ERROR] Build failed with exit code {result.returncode}")
        sys.exit(1)
    
    # Verify output
    if output_path.exists():
        size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"\n[OK] Backend built successfully!")
        print(f"     Path: {output_path}")
        print(f"     Size: {size_mb:.1f} MB")
        
        # Make executable on Unix
        if platform.system() != "Windows":
            os.chmod(output_path, 0o755)
            print(f"     Permissions: executable")
    else:
        print(f"\n[ERROR] Output file not found: {output_path}")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("Backend build complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()

