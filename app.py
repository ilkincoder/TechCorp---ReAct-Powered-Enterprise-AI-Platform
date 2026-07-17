"""TechCorp Enterprise AI Platform — Launcher.

Usage:
    docker compose up --build          # Full stack (app + PostgreSQL)
    python app.py                      # Dev server (requires local PostgreSQL)
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv()

from techcorp_platform.config import APP_HOST, APP_PORT


def main():
    parser = argparse.ArgumentParser(description="TechCorp Enterprise AI Platform")
    parser.add_argument("--host", default=APP_HOST, help=f"Host (default: {APP_HOST})")
    parser.add_argument("--port", type=int, default=APP_PORT, help=f"Port (default: {APP_PORT})")
    args = parser.parse_args()

    import uvicorn
    print(f"\n  TechCorp Enterprise AI Platform v1.0.0")
    print(f"  PostgreSQL → {os.getenv('POSTGRES_HOST', 'localhost')}:{os.getenv('POSTGRES_PORT', '5432')}")
    print(f"  Server     → http://{args.host}:{args.port}")
    print(f"  API docs   → http://{args.host}:{args.port}/docs\n")
    uvicorn.run(
        "techcorp_platform.app:app",
        host=args.host,
        port=args.port,
        reload=True,
    )


if __name__ == "__main__":
    main()