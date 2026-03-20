import os
import sys
import platform
import subprocess


def in_venv():
    # Detect if already inside virtual environment
    return sys.prefix != sys.base_prefix


def get_venv_python():
    if platform.system() == "Windows":
        return os.path.join("venv", "Scripts", "python.exe")
    return os.path.join("venv", "bin", "python")


def main():
    if in_venv():
        print("✅ Already inside virtual environment.")
        return

    python_exec = get_venv_python()

    if not os.path.exists(python_exec):
        print("❌ venv not found!")
        sys.exit(1)

    print("🔁 Switching to virtual environment...\n")

    # Re-run same script inside venv
    subprocess.run([python_exec] + sys.argv)


if __name__ == "__main__":
    main()