import os
import subprocess
import sys


def load_env():
    """Simple .env loader (no external deps)"""
    if not os.path.exists(".env"):
        print("❌ .env file not found!")
        sys.exit(1)

    with open(".env") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                key, _, value = line.partition("=")
                os.environ[key.strip()] = value.strip()


def main():
    print("🌐 Starting Cloudflare Tunnel...\n")

    load_env()

    token = os.environ.get("CLOUDFLARE_TOKEN")

    if not token:
        print("❌ CLOUDFLARE_TOKEN not found in .env")
        sys.exit(1)

    try:
        subprocess.run([
            "cloudflared",
            "tunnel",
            "run",
            "--token",
            token
        ])
    except KeyboardInterrupt:
        print("\n🛑 Tunnel stopped.")


if __name__ == "__main__":
    main()