"""Production startup script for Railway deployment."""
import os
import shutil
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
        print(f"Pre-deploy backup: {backup_path}")
        # Keep only last 20 backups
        backup_dir = os.path.join(volume, 'backups')
        backups = sorted([f for f in os.listdir(backup_dir) if f.endswith('.db')])
        for old in backups[:-20]:
            os.remove(os.path.join(backup_dir, old))

    # Copy initial database to volume on FIRST deploy only
    if not os.path.exists(db_dest) and os.path.exists(db_src):
        print("First deploy: copying initial database to volume...")
        shutil.copy2(db_src, db_dest)

    # NOTE: Schema migrations are handled by _run_migrations() in app.py
    # using ALTER TABLE. NEVER replace the live DB with the repo DB.

from app import create_app, socketio

app = create_app()
port = int(os.environ.get('PORT', 5000))
debug = os.environ.get('FLASK_DEBUG', '0') == '1'

socketio.run(app, host='0.0.0.0', port=port, debug=debug)
