import subprocess
import sys
import os


def run(cmd):
    try:
        result = subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        print(f"\n❌ Failed: {' '.join(cmd)}")
        sys.exit(1)


def main():
    print("🚀 Installing dependencies...\n")

    # Upgrade pip
    print("⬆️ Upgrading pip...")
    run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])

    # Install basic build tools (prevents many errors)
    print("🔧 Installing core tools...")
    run([sys.executable, "-m", "pip", "install", "--upgrade", "setuptools", "wheel"])

    # Install requirements
    if os.path.exists("requirements.txt"):
        print("📥 Installing requirements...")
        run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    else:
        print("⚠️ requirements.txt not found, skipping...")

    print("\n✅ Installation complete!")
    print("👉 python -n bin.start     {for env boot}\n")
    print("👉 python -n bin.run      {for direct boot}\n")


if __name__ == "__main__":
    main()