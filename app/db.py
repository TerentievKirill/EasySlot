import os
import sqlite3
from contextlib import contextmanager

PATH = os.getenv("DATABASE_PATH", "/data/easyslot.db")

@contextmanager
def connect():
    os.makedirs(os.path.dirname(os.path.abspath(PATH)), exist_ok=True)
    conn = sqlite3.connect(PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def initialize():
    with connect() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS masters (
            id INTEGER PRIMARY KEY,
            hostname TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            calendar_id TEXT NOT NULL,
            telegram_chat_id TEXT,
            template TEXT NOT NULL DEFAULT 'default.html',
            slot_minutes INTEGER NOT NULL DEFAULT 60,
            timezone TEXT NOT NULL DEFAULT 'Asia/Almaty',
            active INTEGER NOT NULL DEFAULT 1
        )""")

def find_master(hostname):
    with connect() as db:
        row = db.execute("SELECT * FROM masters WHERE hostname=? AND active=1", (hostname,)).fetchone()
        return dict(row) if row else None
