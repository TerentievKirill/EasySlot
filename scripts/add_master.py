import argparse
import os
import sqlite3

p = argparse.ArgumentParser()
p.add_argument("--hostname", required=True)
p.add_argument("--name", required=True)
p.add_argument("--calendar-id", required=True)
p.add_argument("--telegram-chat-id", default="")
p.add_argument("--template", default="default.html")
p.add_argument("--timezone", default="Asia/Almaty")
p.add_argument("--slot-minutes", type=int, default=60)
args = p.parse_args()
path = os.getenv("DATABASE_PATH", "./data/easyslot.db")
os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
db = sqlite3.connect(path)
db.execute("""CREATE TABLE IF NOT EXISTS masters (
id INTEGER PRIMARY KEY, hostname TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
calendar_id TEXT NOT NULL, telegram_chat_id TEXT, template TEXT NOT NULL DEFAULT 'default.html',
slot_minutes INTEGER NOT NULL DEFAULT 60, timezone TEXT NOT NULL DEFAULT 'Asia/Almaty',
active INTEGER NOT NULL DEFAULT 1)""")
db.execute("""INSERT INTO masters(hostname,name,calendar_id,telegram_chat_id,template,slot_minutes,timezone)
VALUES (?,?,?,?,?,?,?) ON CONFLICT(hostname) DO UPDATE SET
name=excluded.name, calendar_id=excluded.calendar_id, telegram_chat_id=excluded.telegram_chat_id,
template=excluded.template, slot_minutes=excluded.slot_minutes, timezone=excluded.timezone""",
(args.hostname,args.name,args.calendar_id,args.telegram_chat_id,args.template,args.slot_minutes,args.timezone))
db.commit()
print("Saved:", args.hostname)
