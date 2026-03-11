"""
Initialize local development database from seed.

Copies data/seed.db → data/japan_trip.db to provide a correct baseline
that matches the confirmed booking state. The seed is updated by running
scripts/export_seed.py after production changes.

Usage:
    python import_markdown.py          # local dev
    python import_markdown.py --force  # overwrite existing DB

Previously this file was 1,091 lines of regex parsing that built the DB
from source_data/*.md files. Those markdown files reflected the original
brainstorm, not the confirmed bookings, causing stale data in local dev.
The seed.db approach ensures local always matches production state.
"""
import os
import shutil
import sys

basedir = os.path.dirname(os.path.abspath(__file__))
seed = os.path.join(basedir, 'data', 'seed.db')
volume = os.environ.get('RAILWAY_VOLUME_MOUNT_PATH')

if volume:
    dest = os.path.join(volume, 'data', 'japan_trip.db')
    os.makedirs(os.path.dirname(dest), exist_ok=True)
else:
    dest = os.path.join(basedir, 'data', 'japan_trip.db')
    os.makedirs(os.path.dirname(dest), exist_ok=True)

if not os.path.exists(seed):
    print(f"FATAL: seed database not found: {seed}", file=sys.stderr)
    print("Run 'python scripts/export_seed.py' to create it.", file=sys.stderr)
    sys.exit(1)

if os.path.exists(dest) and '--force' not in sys.argv:
    print(f"Database already exists: {dest}")
    print("Use --force to overwrite, or delete it first.")
    sys.exit(0)

shutil.copy2(seed, dest)
size_kb = os.path.getsize(dest) / 1024
print(f"Initialized database from seed ({size_kb:.0f} KB)")
print(f"  {seed} → {dest}")
print(f"\nRun 'python app.py' to start the app.")
