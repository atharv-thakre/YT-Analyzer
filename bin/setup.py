import os
import sys
import subprocess
import platform

VENV_DIR = "venv"


def run_command(cmd, shell=False):
    """Run a command and stream output live."""
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            shell=shell
        )

        for line in process.stdout:
            print(line, end="")

        process.wait()

        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, cmd)

    except Exception as e:
        print(f"\n❌ Error running command: {cmd}")
        print(f"Details: {e}")
        sys.exit(1)


def get_venv_python():
    """Return path to venv python executable."""
    if platform.system() == "Windows":
        return os.path.join(VENV_DIR, "Scripts", "python.exe")
    else:
        return os.path.join(VENV_DIR, "bin", "python")


def create_venv():
    """Create virtual environment if not exists."""
    if not os.path.exists(VENV_DIR):
        print("📦 Creating virtual environment...")
        run_command([sys.executable, "-m", "venv", VENV_DIR])
    else:
        print("✅ Virtual environment already exists.")


def upgrade_pip(python_exec):
    """Upgrade pip, setuptools, wheel."""
    print("⬆️ Upgrading pip, setuptools, wheel...")
    run_command([python_exec, "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"])


def install_requirements(python_exec):
    """Install requirements.txt."""
    if not os.path.exists("requirements.txt"):
        print("⚠️ No requirements.txt found. Skipping...")
        return

    print("📥 Installing dependencies...")
    run_command([python_exec, "-m", "pip", "install", "-r", "requirements.txt"])


def main():
    print("🚀 Starting setup...\n")

    # Step 1: Create venv
    create_venv()

    # Step 2: Get venv python
    python_exec = get_venv_python()

    if not os.path.exists(python_exec):
        print("❌ venv python not found!")
        sys.exit(1)

    # Step 3: Upgrade pip tools
    upgrade_pip(python_exec)

    # Step 4: Install requirements
    install_requirements(python_exec)

    print("\n✅ Setup complete!")
    print(f"\n👉 To run your app:")
    if platform.system() == "Windows":
        print(f"   {VENV_DIR}\\Scripts\\activate")
    else:
        print(f"   source {VENV_DIR}/bin/activate")

    print("   python -m bin.run\n")


if __name__ == "__main__":
    main()