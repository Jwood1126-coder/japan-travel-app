import os
import shutil
from datetime import datetime
from flask import Blueprint, send_file, request, jsonify, current_app, session, redirect, url_for

backup_bp = Blueprint('backup', __name__)


def _db_path():
    uri = current_app.config['SQLALCHEMY_DATABASE_URI']
    return uri.replace('sqlite:///', '')


def _backup_dir():
    volume = os.environ.get('RAILWAY_VOLUME_MOUNT_PATH')
    if volume:
        d = os.path.join(volume, 'backups')
    else:
        d = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backups')
    os.makedirs(d, exist_ok=True)
    return d


@backup_bp.route('/api/backup/download')
def download_backup():
    if not session.get('authenticated'):
        return jsonify({'ok': False, 'error': 'Not authenticated'}), 401
    db = _db_path()
    if not os.path.exists(db):
        return jsonify({'ok': False, 'error': 'No database found'}), 404
    ts = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    return send_file(db, as_attachment=True,
                     download_name=f'japan_trip_backup_{ts}.db')


@backup_bp.route('/api/backup/restore', methods=['POST'])
def restore_backup():
    if not session.get('authenticated'):
        return jsonify({'ok': False, 'error': 'Not authenticated'}), 401
    file = request.files.get('backup')
    if not file or not file.filename:
        return jsonify({'ok': False, 'error': 'No file uploaded'}), 400
    if not file.filename.endswith('.db'):
        return jsonify({'ok': False, 'error': 'File must be a .db file'}), 400

    db = _db_path()

    # Backup current DB before overwriting
    if os.path.exists(db):
        ts = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        backup_path = os.path.join(_backup_dir(), f'pre_restore_{ts}.db')
        shutil.copy2(db, backup_path)

    file.save(db)
    return jsonify({'ok': True, 'message': 'Database restored. Reloading...'})


@backup_bp.route('/api/backup/list')
def list_backups():
    if not session.get('authenticated'):
        return jsonify({'ok': False, 'error': 'Not authenticated'}), 401
    d = _backup_dir()
    backups = []
    for f in sorted(os.listdir(d), reverse=True):
        if f.endswith('.db'):
            path = os.path.join(d, f)
            size = os.path.getsize(path)
            backups.append({'name': f, 'size_kb': round(size / 1024)})
    return jsonify({'ok': True, 'backups': backups[:20]})


@backup_bp.route('/api/backup/restore-server/<name>', methods=['POST'])
def restore_server_backup(name):
    """Restore from a server-side auto-backup."""
    if not session.get('authenticated'):
        return jsonify({'ok': False, 'error': 'Not authenticated'}), 401
    if '..' in name or '/' in name or '\\' in name:
        return jsonify({'ok': False, 'error': 'Invalid name'}), 400
    d = _backup_dir()
    backup_path = os.path.join(d, name)
    if not os.path.exists(backup_path):
        return jsonify({'ok': False, 'error': 'Backup not found'}), 404

    db = _db_path()
    # Save current before restoring
    if os.path.exists(db):
        ts = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        shutil.copy2(db, os.path.join(d, f'pre_restore_{ts}.db'))

    shutil.copy2(backup_path, db)
    return jsonify({'ok': True, 'message': f'Restored from {name}. Reloading...'})
