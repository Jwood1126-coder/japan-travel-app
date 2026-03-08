"""Production startup script for Railway deployment."""
import os
import shutil
import subprocess
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
    db_src = os.path.join(basedir, 'data', 'japan_trip.db')

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
        # First deploy — need to bootstrap the database
        if os.path.exists(db_src):
            # Legacy path: copy bundled seed DB from repo
            print("[bootstrap] First deploy: copying seed DB from repo to volume...")
            shutil.copy2(db_src, db_dest)
        else:
            # New path: no seed DB in repo — build from markdown source
            print("[bootstrap] First deploy: no seed DB found, running import_markdown.py...")
            result = subprocess.run(
                [sys.executable, os.path.join(basedir, 'import_markdown.py')],
                cwd=basedir,
                env={**os.environ, 'RAILWAY_VOLUME_MOUNT_PATH': volume},
            )
            if result.returncode != 0:
                print("[bootstrap] FATAL: import_markdown.py failed", file=sys.stderr)
                sys.exit(1)
            print("[bootstrap] Database created from markdown source data")

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
