"""Production startup script for Railway deployment."""
import os
import shutil
import sys
from datetime import datetime

basedir = os.path.dirname(__file__)
volume = os.environ.get('RAILWAY_VOLUME_MOUNT_PATH')

if volume:
    # Ensure persistent directories exist on Railway volume
    os.makedirs(os.path.join(volume, 'data'), exist_ok=True)
    os.makedirs(os.path.join(volume, 'uploads', 'originals'), exist_ok=True)
    os.makedirs(os.path.join(volume, 'uploads', 'thumbnails'), exist_ok=True)
    os.makedirs(os.path.join(volume, 'backups'), exist_ok=True)

    db_dest = os.path.join(volume, 'data', 'japan_trip.db')

    # Auto-backup before every deploy (if DB exists)
    if os.path.exists(db_dest):
        ts = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        backup_path = os.path.join(volume, 'backups', f'japan_trip_{ts}.db')
        shutil.copy2(db_dest, backup_path)
        print(f"[bootstrap] Pre-deploy backup: {backup_path}")
        # Keep only last 20 backups
        backup_dir = os.path.join(volume, 'backups')
        backups = sorted([f for f in os.listdir(backup_dir) if f.endswith('.db')])
        for old in backups[:-20]:
            os.remove(os.path.join(backup_dir, old))
        print("[bootstrap] Using existing volume DB (normal path)")
    else:
        # First deploy — bootstrap from seed.db
        seed_db = os.path.join(basedir, 'data', 'seed.db')
        if os.path.exists(seed_db):
            print("[bootstrap] First deploy: copying seed.db to volume...")
            shutil.copy2(seed_db, db_dest)
        else:
            print("[bootstrap] FATAL: data/seed.db not found in repo", file=sys.stderr)
            sys.exit(1)

    # NOTE: Schema migrations are handled by _run_migrations() in app.py
    # using ALTER TABLE. NEVER replace the live DB with the repo DB.

port = int(os.environ.get('PORT', 5000))

# Hand off to Gunicorn with gevent workers for WebSocket support and resilience.
# os.execv replaces this process with gunicorn — wsgi.py imports create_app() on startup.
os.execv(sys.executable, [
    sys.executable,
    '-m',
    'gunicorn',
    '--worker-class', 'geventwebsocket.gunicorn.workers.GeventWebSocketWorker',
    '--workers', '1',
    '--bind', f'0.0.0.0:{port}',
    '--timeout', '120',
    '--access-logfile', '-',
    'wsgi:app',
])
