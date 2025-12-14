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
        "--collect-all", "fastapi",
        "--collect-all", "starlette",
        "--collect-all", "pydantic",
        "--collect-all", "pydantic_settings",
        # HTTP/WebSocket clients
        "--collect-all", "httpx",
        "--collect-all", "httpcore",
        "--collect-all", "websockets",
        "--collect-all", "websocket",
        "--collect-all", "aiohttp",
        "--collect-all", "requests",
        "--collect-all", "urllib3",
        # Data processing
        "--collect-all", "pandas",
        "--collect-all", "pandas_ta",
        "--collect-all", "numpy",
        "--collect-all", "polars",
        # Async
        "--collect-all", "anyio",
        "--collect-all", "sniffio",
        # Other utilities
        "--collect-all", "orjson",
        "--collect-all", "python_dotenv",
        "--collect-all", "loguru",
        # Exclude large unused packages
        "--exclude-module", "tkinter",
        "--exclude-module", "matplotlib",
        "--exclude-module", "PIL",
        "--exclude-module", "cv2",
        "--exclude-module", "torch",
        "--exclude-module", "tensorflow",
        "--exclude-module", "transformers",
        "--exclude-module", "keras",
        "--exclude-module", "jax",
        "--exclude-module", "flax",
        "--exclude-module", "optax",
        "--exclude-module", "IPython",
        "--exclude-module", "jupyter",
        "--exclude-module", "notebook",
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
