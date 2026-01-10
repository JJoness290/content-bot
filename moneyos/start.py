#!/usr/bin/env python3
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
try:
    import venv
except ImportError:
    print("Embedded/portable Python detected (missing venv module).")
    print("Please install Python 3.11+ from python.org (full installer with pip).")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent
APP_DIR = ROOT / "app"
REQUIREMENTS = ROOT / "requirements.txt"
LOG_DIR = ROOT / "logs"
BOOTSTRAP_ERROR_LOG = LOG_DIR / "bootstrap_error.log"
VENV_DIR = ROOT / ".venv"

if APP_DIR.exists():
    # Ensure imports like `from app.core import db` work regardless of cwd.
    root_str = str(ROOT)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)

os.chdir(ROOT)


def ensure_python_version() -> None:
    if sys.version_info < (3, 11):
        print("MoneyOS requires Python 3.11 or newer.")
        sys.exit(1)


def ensure_pip_available() -> None:
    try:
        import pip  # noqa: F401
    except ImportError:
        print("Pip is missing. MoneyOS requires the full system Python installation.")
        print("Please install Python 3.11+ from python.org (not embedded/portable builds).")
        sys.exit(1)


def log_bootstrap_error(message: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().isoformat()
    BOOTSTRAP_ERROR_LOG.write_text(f"{timestamp}\n{message}\n", encoding="utf-8")


def venv_python() -> Path:
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def ensure_venv() -> None:
    if VENV_DIR.exists():
        return
    builder = venv.EnvBuilder(with_pip=True, clear=False)
    builder.create(VENV_DIR)


def ensure_in_venv() -> None:
    ensure_venv()
    venv_py = venv_python()
    if Path(sys.executable).resolve() != venv_py.resolve():
        # Re-exec into the venv so all subsequent commands use the same interpreter.
        os.execv(str(venv_py), [str(venv_py), str(ROOT / "start.py"), *sys.argv[1:]])


def install_requirements() -> None:
    if not REQUIREMENTS.exists():
        print("requirements.txt not found.")
        log_bootstrap_error(
            f"Python: {sys.executable}\nCommand: pip install -r {REQUIREMENTS}\n"
            "Error: requirements.txt missing."
        )
        sys.exit(1)
    try:
        subprocess.run(
            [str(sys.executable), "-m", "pip", "install", "-r", str(REQUIREMENTS)],
            check=True,
            text=True,
            capture_output=True,
            timeout=300,
        )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr or ""
        message = (
            f"Python: {sys.executable}\n"
            f"Command: {' '.join(exc.cmd) if exc.cmd else 'pip install'}\n"
            f"Error: {stderr.strip() or 'Unknown error'}"
        )
        log_bootstrap_error(message)
        print("Dependency installation failed. See logs/bootstrap_error.log for details.")
        if stderr:
            print(stderr)
        sys.exit(exc.returncode)
    except subprocess.TimeoutExpired as exc:
        message = (
            f"Python: {sys.executable}\n"
            f"Command: {exc.cmd}\n"
            f"Error: pip install timed out after {exc.timeout} seconds."
        )
        log_bootstrap_error(message)
        print("Dependency installation timed out. See logs/bootstrap_error.log for details.")
        sys.exit(1)


def init_database() -> None:
    from app.core import db

    db.run_migrations()
    db.seed_data()


def start_server() -> None:
    host = os.environ.get("MONEYOS_HOST", "127.0.0.1")
    port = os.environ.get("MONEYOS_PORT", "8000")
    print("Open http://127.0.0.1:8000 in your browser")
    print("Starting MoneyOS server...")
    subprocess.run(
        [
            str(sys.executable),
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            host,
            "--port",
            port,
        ],
        check=True,
        cwd=str(ROOT),
    )


def main() -> None:
    ensure_python_version()
    ensure_pip_available()
    print("VENV MODE")
    ensure_in_venv()
    install_requirements()
    init_database()
    start_server()


if __name__ == "__main__":
    main()
