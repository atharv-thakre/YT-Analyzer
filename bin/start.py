import os
import sys
import subprocess
import platform


def get_venv_python():
    if platform.system() == "Windows":
        return os.path.join("venv", "Scripts", "python.exe")
    else:
        return os.path.join("venv", "bin", "python")


def main():
    python_exec = get_venv_python()

    if not os.path.exists(python_exec):
        print("❌ venv not found! Run install/setup first.")
        sys.exit(1)

    print("🚀 Starting FastAPI server...\n")

    # Run uvicorn using venv python
    cmd = [
        python_exec,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        "0.0.0.0",   # important for Cloudflare Tunnel
        "--port",
        "8000",
        "--reload"   # remove in production
    ]

    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n🛑 Server stopped.")


if __name__ == "__main__":
    main()