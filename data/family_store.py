from __future__ import annotations

import json
import os
import sqlite3
from typing import Any

DB_PATH = os.path.join(os.path.dirname(__file__), "familysync.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_schema() -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS family_events (
                id TEXT PRIMARY KEY,
                title TEXT,
                member TEXT,
                start TEXT,
                end TEXT,
                category TEXT,
                location TEXT,
                notes TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS family_tasks (
                id TEXT PRIMARY KEY,
                title TEXT,
                owner TEXT,
                start TEXT,
                end TEXT,
                priority TEXT,
                completed INTEGER,
                category TEXT,
                description TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def save_events_and_tasks(events: list[dict[str, Any]], tasks: list[dict[str, Any]]) -> None:
    ensure_schema()
    conn = get_connection()
    try:
        conn.execute("DELETE FROM family_events")
        conn.execute("DELETE FROM family_tasks")
        conn.executemany(
            "INSERT OR REPLACE INTO family_events (id, title, member, start, end, category, location, notes) VALUES (:id, :title, :member, :start, :end, :category, :location, :notes)",
            events,
        )
        conn.executemany(
            "INSERT OR REPLACE INTO family_tasks (id, title, owner, start, end, priority, completed, category, description) VALUES (:id, :title, :owner, :start, :end, :priority, :completed, :category, :description)",
            [{**task, "completed": int(bool(task.get("completed", False)))} for task in tasks],
        )
        conn.commit()
    finally:
        conn.close()


def load_events_and_tasks() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    ensure_schema()
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM family_events ORDER BY start").fetchall()
        events = [dict(row) for row in rows]
        task_rows = conn.execute("SELECT * FROM family_tasks ORDER BY start").fetchall()
        tasks = [dict(row) for row in task_rows]
        for task in tasks:
            task["completed"] = bool(task["completed"])
        return events, tasks
    finally:
        conn.close()


def save_json_backup(payload: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(__file__), exist_ok=True)
    with open(os.path.join(os.path.dirname(__file__), "family_state.json"), "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
