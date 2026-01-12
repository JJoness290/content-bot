import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "moneyos.db"


def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def run_migrations() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                status TEXT NOT NULL,
                category TEXT NOT NULL,
                details_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                decision TEXT NOT NULL,
                reason TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS metrics_daily (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stream TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                value REAL NOT NULL,
                date TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS experiments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                hypothesis TEXT NOT NULL,
                variants_json TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                outcome_json TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS lessons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                confidence REAL NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS assets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uuid TEXT,
                type TEXT NOT NULL,
                platform TEXT NOT NULL,
                title TEXT NOT NULL,
                status TEXT NOT NULL,
                content_md TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS scheduler_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                last_run_at TEXT,
                last_draft_at TEXT,
                drafts_this_week INTEGER NOT NULL,
                next_scheduled_draft_at TEXT,
                locked_at TEXT,
                enabled INTEGER NOT NULL DEFAULT 1,
                interval_minutes INTEGER NOT NULL DEFAULT 15,
                last_run_result TEXT,
                autopilot_time_local TEXT,
                autopilot_platform TEXT,
                autopilot_draft_only INTEGER NOT NULL DEFAULT 1,
                autopilot_topics_json TEXT,
                autopilot_topic_index INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS content_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uuid TEXT NOT NULL,
                platform TEXT NOT NULL,
                kind TEXT NOT NULL,
                status TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS video_autopilot_state (
                platform TEXT PRIMARY KEY,
                enabled INTEGER NOT NULL DEFAULT 1,
                interval_minutes INTEGER NOT NULL DEFAULT 15,
                last_run_at TEXT,
                last_action TEXT,
                last_error TEXT,
                locked_at TEXT,
                last_script_id INTEGER,
                last_video_payload_json TEXT
            )
            """
        )
        columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(scheduler_state)").fetchall()
        }
        if "enabled" not in columns:
            conn.execute("ALTER TABLE scheduler_state ADD COLUMN enabled INTEGER NOT NULL DEFAULT 1")
        if "interval_minutes" not in columns:
            conn.execute(
                "ALTER TABLE scheduler_state ADD COLUMN interval_minutes INTEGER NOT NULL DEFAULT 15"
            )
        if "last_run_result" not in columns:
            conn.execute("ALTER TABLE scheduler_state ADD COLUMN last_run_result TEXT")
        if "autopilot_time_local" not in columns:
            conn.execute("ALTER TABLE scheduler_state ADD COLUMN autopilot_time_local TEXT")
        if "autopilot_platform" not in columns:
            conn.execute("ALTER TABLE scheduler_state ADD COLUMN autopilot_platform TEXT")
        if "autopilot_draft_only" not in columns:
            conn.execute(
                "ALTER TABLE scheduler_state ADD COLUMN autopilot_draft_only INTEGER NOT NULL DEFAULT 1"
            )
        if "autopilot_topics_json" not in columns:
            conn.execute("ALTER TABLE scheduler_state ADD COLUMN autopilot_topics_json TEXT")
        if "autopilot_topic_index" not in columns:
            conn.execute(
                "ALTER TABLE scheduler_state ADD COLUMN autopilot_topic_index INTEGER NOT NULL DEFAULT 0"
            )
        video_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(video_autopilot_state)").fetchall()
        }
        if "enabled" not in video_columns:
            conn.execute(
                "ALTER TABLE video_autopilot_state ADD COLUMN enabled INTEGER NOT NULL DEFAULT 1"
            )
        if "interval_minutes" not in video_columns:
            conn.execute(
                "ALTER TABLE video_autopilot_state ADD COLUMN interval_minutes INTEGER NOT NULL DEFAULT 15"
            )
        if "last_run_at" not in video_columns:
            conn.execute("ALTER TABLE video_autopilot_state ADD COLUMN last_run_at TEXT")
        if "last_action" not in video_columns:
            conn.execute("ALTER TABLE video_autopilot_state ADD COLUMN last_action TEXT")
        if "last_error" not in video_columns:
            conn.execute("ALTER TABLE video_autopilot_state ADD COLUMN last_error TEXT")
        if "locked_at" not in video_columns:
            conn.execute("ALTER TABLE video_autopilot_state ADD COLUMN locked_at TEXT")
        if "last_script_id" not in video_columns:
            conn.execute("ALTER TABLE video_autopilot_state ADD COLUMN last_script_id INTEGER")
        if "last_video_payload_json" not in video_columns:
            conn.execute("ALTER TABLE video_autopilot_state ADD COLUMN last_video_payload_json TEXT")

        _regenerate_draft_assets(conn)


def _regenerate_draft_assets(conn: sqlite3.Connection) -> None:
    from app.core import content_generator

    rows = conn.execute(
        "SELECT id, title, content_md, metadata_json FROM assets WHERE status = ?",
        ("DRAFT",),
    ).fetchall()
    if not rows:
        return
    now = datetime.utcnow().isoformat()
    for row in rows:
        metadata = json.loads(row["metadata_json"] or "{}")
        topic = metadata.get("topic") or row["title"]
        keywords = metadata.get("keywords") or content_generator.extract_keywords(topic)
        placeholders = metadata.get(
            "affiliate_placeholders",
            ["Primary offer – Official Site", "Secondary offer – Official Site"],
        )
        if "tone" in metadata:
            content = content_generator.generate_custom_medium_article(
                topic=topic,
                tone=metadata.get("tone", "friendly"),
                length=metadata.get("length", "medium"),
                audience=metadata.get("audience", "UK"),
                keywords=keywords,
                affiliate_placeholders=placeholders,
            )
        else:
            content = content_generator.generate_autopilot_draft(
                topic=topic,
                angle=metadata.get("angle", "buyer guide"),
                keywords=keywords,
                affiliate_placeholders=placeholders,
            )
        conn.execute(
            "UPDATE assets SET content_md = ?, updated_at = ? WHERE id = ?",
            (content, now, row["id"]),
        )
    conn.commit()


def seed_data() -> None:
    now = datetime.utcnow().isoformat()
    with get_connection() as conn:
        cur = conn.execute("SELECT COUNT(*) AS count FROM tasks")
        if cur.fetchone()["count"] == 0:
            tasks = [
                (
                    "Connect your funding source",
                    "WAITING_ON_YOU",
                    "Operations",
                    json.dumps(
                        {
                            "need": "Connect a dedicated bank account for reporting.",
                            "why": "We need clean inflow tracking and reconciliation.",
                            "risk": "Low",
                            "steps": [
                                "Open your online banking portal.",
                                "Create a new account named 'MoneyOS Ops'.",
                                "Copy the account number and sort code.",
                                "Paste them into the MoneyOS Settings page.",
                            ],
                            "paste_back": "Account name + account number + sort code.",
                            "next": "We will enable reconciliation and daily reporting.",
                        }
                    ),
                    now,
                    now,
                ),
                (
                    "Draft weekly revenue targets",
                    "NOT_STARTED",
                    "Planning",
                    json.dumps(
                        {
                            "need": "Propose weekly revenue targets for the next 4 weeks.",
                            "why": "Targets define pacing and experiment budgets.",
                            "risk": "Low",
                            "steps": [
                                "Open the Metrics page.",
                                "Review the default baseline metric.",
                                "Send your proposed targets back.",
                            ],
                            "paste_back": "Week-by-week targets in GBP.",
                            "next": "We will align experiments to targets.",
                        }
                    ),
                    now,
                    now,
                ),
                (
                    "Review experiment backlog",
                    "DONE",
                    "Experiments",
                    json.dumps(
                        {
                            "need": "Confirm the initial experiment backlog.",
                            "why": "Keeps learning cycles consistent.",
                            "risk": "Low",
                            "steps": ["Open Experiments page and confirm list."],
                            "paste_back": "Confirmed ✅",
                            "next": "We will schedule the first run.",
                        }
                    ),
                    now,
                    now,
                ),
            ]
            conn.executemany(
                """
                INSERT INTO tasks (title, status, category, details_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                tasks,
            )

        cur = conn.execute("SELECT COUNT(*) AS count FROM experiments")
        if cur.fetchone()["count"] == 0:
            conn.execute(
                """
                INSERT INTO experiments (
                    name, hypothesis, variants_json, status, started_at, ended_at, outcome_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "Landing page headline test",
                    "A clearer value prop increases signup rate.",
                    json.dumps(["Control", "Value-focused headline"]),
                    "RUNNING",
                    now,
                    None,
                    json.dumps({"Control": {"success": 3, "failure": 5}}),
                ),
            )

        cur = conn.execute("SELECT COUNT(*) AS count FROM metrics_daily")
        if cur.fetchone()["count"] == 0:
            conn.execute(
                """
                INSERT INTO metrics_daily (stream, metric_name, value, date)
                VALUES (?, ?, ?, ?)
                """,
                ("core", "baseline_revenue", 0.0, now.split("T")[0]),
            )

        cur = conn.execute("SELECT COUNT(*) AS count FROM assets")
        if cur.fetchone()["count"] == 0:
            conn.execute(
                """
                INSERT INTO assets (
                    uuid, type, platform, title, status, content_md, metadata_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    "blog_post",
                    "medium",
                    "NordVPN vs Surfshark: Which VPN Is Better in 2026?",
                    "DRAFT",
                    "# NordVPN vs Surfshark: Which VPN Is Better in 2026?\n\n_Draft placeholder generated by MoneyOS._\n",
                    json.dumps(
                        {
                            "topic": "VPN comparisons",
                            "keywords": ["NordVPN", "Surfshark", "VPN comparison"],
                            "angle": "buyer-focused comparison",
                            "intent": "comparison",
                            "monetization_type": "affiliate",
                            "affiliate_placeholders": [
                                "[NordVPN – Official Site]",
                                "[Surfshark – Official Site]",
                            ],
                        }
                    ),
                    now,
                    now,
                ),
            )

        cur = conn.execute("SELECT COUNT(*) AS count FROM scheduler_state")
        if cur.fetchone()["count"] == 0:
            conn.execute(
                """
                INSERT INTO scheduler_state (
                    id, last_run_at, last_draft_at, drafts_this_week, next_scheduled_draft_at, locked_at,
                    enabled, interval_minutes, last_run_result, autopilot_time_local, autopilot_platform,
                    autopilot_draft_only, autopilot_topics_json, autopilot_topic_index
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    1,
                    None,
                    None,
                    0,
                    None,
                    None,
                    1,
                    15,
                    None,
                    "09:00",
                    "medium",
                    1,
                    json.dumps(
                        [
                            "NordVPN vs Surfshark: Which VPN Is Better in 2026?",
                            "Budgeting tips for beginners",
                            "Personal finance apps that simplify tracking",
                            "Investing basics for cautious starters",
                        ]
                    ),
                    0,
                ),
            )

        asset_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(assets)").fetchall()
        }
        if "uuid" not in asset_columns:
            conn.execute("ALTER TABLE assets ADD COLUMN uuid TEXT")

        rows = conn.execute("SELECT id, uuid FROM assets").fetchall()
        for row in rows:
            if not row["uuid"]:
                conn.execute(
                    "UPDATE assets SET uuid = ? WHERE id = ?",
                    (str(uuid.uuid4()), row["id"]),
                )

        conn.commit()
