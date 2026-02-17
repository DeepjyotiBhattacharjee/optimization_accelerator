import sqlite3
import json
from datetime import datetime

DB_NAME = "models.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS models (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            model_json TEXT,
            created_at TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_id INTEGER,
            objective REAL,
            solution_json TEXT,
            created_at TEXT
        )
    """)

    conn.commit()
    conn.close()


def save_model(name, model_json):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
        INSERT INTO models (name, model_json, created_at)
        VALUES (?, ?, ?)
    """, (name, json.dumps(model_json), datetime.now().isoformat()))

    conn.commit()
    model_id = c.lastrowid
    conn.close()

    return model_id


def save_result(model_id, objective, solution):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
        INSERT INTO results (model_id, objective, solution_json, created_at)
        VALUES (?, ?, ?, ?)
    """, (
        model_id,
        objective,
        json.dumps(solution),
        datetime.now().isoformat()
    ))

    conn.commit()
    conn.close()
