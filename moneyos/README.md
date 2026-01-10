# MoneyOS

MoneyOS is a Python 3.11+ local dashboard for safe money-making workflows, task tracking, and lightweight experimentation.

## First run behavior
Running `python start.py` will:
1. Verify Python 3.11+.
2. Create a local virtual environment in `.venv` (if missing).
3. Install dependencies from `requirements.txt` into the local venv.
4. Initialize the SQLite database at `data/moneyos.db` and seed sample data.
5. Launch the web dashboard at `http://127.0.0.1:8000`.

## Start / stop
- Start: `python start.py`
- Stop: press `Ctrl+C` in the terminal running the server.

## Windows quick start
You can also run `run.bat` to activate the virtual environment and launch MoneyOS.
MoneyOS requires a full Python 3.11+ installation with pip (from python.org).

## Generate a Medium-ready article (UI)
1. Open the Assets page.
2. Click **Generate new Medium article**.
3. Fill in topic, tone, length, and audience.
4. Submit to generate a draft and open the asset detail page.

**Note:** MoneyOS uses raw Unsplash image URLs (not Markdown image tags) because Medium renders raw URLs reliably on paste.

## Data storage
- SQLite database: `data/moneyos.db`
- Logs: `logs/`

## Adding tasks and recording outcomes
- Add tasks via `app/core/task_manager.py` (see `create_task`).
- Record experiments and outcomes via `app/core/learning.py`.
- The Checklist page reads from the `tasks` table and shows Request Cards for details.

## If dependency install fails
Sometimes `pip install` is blocked by a proxy, firewall, or VPN. MoneyOS will still start in **Limited Mode** so you can access the dashboard, but some features will be unavailable until dependencies install successfully.

Fix steps (Windows):
1. Switch to home Wi-Fi or disable VPN.
2. Open Command Prompt.
3. `cd` into the MoneyOS project folder.
4. Run: `.venv\\Scripts\\activate`
5. Run: `pip install -r requirements.txt`
6. Run: `python start.py`

If the problem persists, review `logs/bootstrap_error.log` for the latest error details.

## Configuration
Default settings live in `config/settings.yaml`.

## Autopilot configuration
Autopilot runs daily at a configured local time and creates a draft-only Medium article by default. You can update topics and scheduling in the database (table `scheduler_state`). The status panel in Settings shows the last run time and result.
