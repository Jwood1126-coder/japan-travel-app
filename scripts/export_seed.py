#!/usr/bin/env python3
"""
Export current DB as a clean seed for local development.

Usage:
  python scripts/export_seed.py                    # from local DB
  python scripts/export_seed.py /path/to/backup.db # from a production backup

Strips chat history and photos, keeps all trip data.
Commit the result: git add data/seed.db && git commit
"""
import sqlite3
import shutil
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
SEED_PATH = os.path.join(PROJECT_DIR, 'data', 'seed.db')
LOCAL_DB = os.path.join(PROJECT_DIR, 'data', 'japan_trip.db')

# Accept an optional source path argument
source = sys.argv[1] if len(sys.argv) > 1 else LOCAL_DB

if not os.path.exists(source):
    print(f"Source DB not found: {source}")
    sys.exit(1)

# Validate it's a real SQLite DB with expected tables
try:
    conn = sqlite3.connect(source)
    conn.execute('SELECT count(*) FROM trip')
    conn.execute('SELECT count(*) FROM day')
    conn.execute('SELECT count(*) FROM accommodation_option')
    conn.close()
except Exception as e:
    print(f"Invalid database: {e}")
    sys.exit(1)

# Copy source → seed.db
shutil.copy2(source, SEED_PATH)

# Strip ephemeral data
conn = sqlite3.connect(SEED_PATH)
c = conn.cursor()
c.execute('DELETE FROM chat_message')
chat_count = c.rowcount
c.execute('DELETE FROM photo')
photo_count = c.rowcount
conn.commit()
conn.close()

# Compact
conn = sqlite3.connect(SEED_PATH)
conn.execute('VACUUM')
conn.close()

size_kb = os.path.getsize(SEED_PATH) / 1024
print(f"Exported seed.db ({size_kb:.0f} KB)")
print(f"  Stripped: {chat_count} chat messages, {photo_count} photos")
print(f"  Path: {SEED_PATH}")
print(f"\nCommit: git add data/seed.db")
