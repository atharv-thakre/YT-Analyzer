import subprocess
import sys


def main():
    print("🚀 Starting FastAPI server...\n")

    try:
        subprocess.run([
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload"   # remove in production
        ])
    except KeyboardInterrupt:
        print("\n🛑 Server stopped.")


if __name__ == "__main__":
    main()