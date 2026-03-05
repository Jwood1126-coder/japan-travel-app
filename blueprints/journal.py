from flask import Blueprint, render_template, jsonify, request, current_app
from models import db, JournalEntry, Photo, Day
from datetime import datetime
import os
import uuid

journal_bp = Blueprint('journal', __name__)


@journal_bp.route('/journal')
def journal_view():
    entries = JournalEntry.query.order_by(
        JournalEntry.created_at.desc()).all()
    photos = Photo.query.order_by(Photo.taken_at.desc()).all()
    days = Day.query.order_by(Day.day_number).all()
    return render_template('journal.html', entries=entries, photos=photos,
                           days=days)


@journal_bp.route('/journal/new', methods=['GET', 'POST'])
def new_entry():
    days = Day.query.order_by(Day.day_number).all()
    if request.method == 'POST':
        entry = JournalEntry(
            day_id=request.form.get('day_id') or None,
            title=request.form.get('title', ''),
            content=request.form.get('content', ''),
            mood=request.form.get('mood', ''),
        )
        db.session.add(entry)
        db.session.commit()

        # Handle photo uploads
        photos = request.files.getlist('photos')
        for f in photos:
            if f and f.filename:
                _save_photo(f, entry.id, entry.day_id)

        db.session.commit()

        from app import socketio
        socketio.emit('journal_updated', {'action': 'new_entry',
                                           'id': entry.id})

        return jsonify({'ok': True, 'id': entry.id})

    return render_template('journal_entry.html', entry=None, days=days)


@journal_bp.route('/journal/<int:entry_id>')
def view_entry(entry_id):
    entry = JournalEntry.query.get_or_404(entry_id)
    days = Day.query.order_by(Day.day_number).all()
    return render_template('journal_entry.html', entry=entry, days=days)


@journal_bp.route('/api/photos/upload', methods=['POST'])
def upload_photos():
    day_id = request.form.get('day_id') or None
    journal_entry_id = request.form.get('journal_entry_id') or None
    results = []

    for f in request.files.getlist('photos'):
        if f and f.filename:
            photo = _save_photo(f, journal_entry_id, day_id)
            if photo:
                results.append(photo.to_dict())

    db.session.commit()

    from app import socketio
    socketio.emit('journal_updated', {'action': 'photos_added',
                                       'count': len(results)})

    return jsonify(results)


@journal_bp.route('/photos/originals/<filename>')
def serve_original(filename):
    from flask import send_from_directory
    return send_from_directory(
        os.path.join(current_app.config['UPLOAD_FOLDER'], 'originals'),
        filename)


@journal_bp.route('/photos/thumbnails/<filename>')
def serve_thumbnail(filename):
    from flask import send_from_directory
    return send_from_directory(
        os.path.join(current_app.config['UPLOAD_FOLDER'], 'thumbnails'),
        filename)


def _save_photo(file_obj, journal_entry_id, day_id):
    """Save an uploaded photo, generate thumbnail, extract EXIF."""
    allowed = {'jpg', 'jpeg', 'png', 'gif', 'heic', 'heif', 'webp'}
    ext = file_obj.filename.rsplit('.', 1)[-1].lower()
    if ext not in allowed:
        return None

    filename = f"{uuid.uuid4().hex}.{ext}"
    upload_dir = current_app.config['UPLOAD_FOLDER']
    original_path = os.path.join(upload_dir, 'originals', filename)
    file_obj.save(original_path)

    # Extract EXIF and generate thumbnail
    exif_data = {}
    width, height, file_size = 0, 0, os.path.getsize(original_path)
    thumb_filename = f"thumb_{filename.rsplit('.', 1)[0]}.jpg"
    thumb_path = os.path.join(upload_dir, 'thumbnails', thumb_filename)

    try:
        from PIL import Image, ImageOps
        from PIL.ExifTags import TAGS, GPSTAGS

        with Image.open(original_path) as img:
            # Fix orientation
            img = ImageOps.exif_transpose(img)
            width, height = img.size

            # EXIF extraction
            raw_exif = img.getexif()
            if raw_exif:
                for tag_id, value in raw_exif.items():
                    tag = TAGS.get(tag_id, tag_id)
                    if tag == 'DateTimeOriginal':
                        try:
                            exif_data['datetime'] = datetime.strptime(
                                str(value), '%Y:%m:%d %H:%M:%S')
                        except (ValueError, TypeError):
                            pass
                    elif tag == 'GPSInfo':
                        gps = {}
                        for gps_tag_id, gps_value in value.items():
                            gps_tag = GPSTAGS.get(gps_tag_id, gps_tag_id)
                            gps[gps_tag] = gps_value
                        exif_data['latitude'] = _gps_to_decimal(
                            gps.get('GPSLatitude'), gps.get('GPSLatitudeRef'))
                        exif_data['longitude'] = _gps_to_decimal(
                            gps.get('GPSLongitude'),
                            gps.get('GPSLongitudeRef'))

            # Generate thumbnail
            img.thumbnail(current_app.config['THUMBNAIL_SIZE'],
                          Image.Resampling.LANCZOS)
            img.save(thumb_path, 'JPEG', quality=85)
    except Exception:
        # If thumbnail generation fails, copy original as thumb
        thumb_filename = filename

    photo = Photo(
        journal_entry_id=journal_entry_id,
        day_id=day_id,
        filename=filename,
        original_filename=file_obj.filename,
        thumbnail_filename=thumb_filename,
        taken_at=exif_data.get('datetime'),
        latitude=exif_data.get('latitude'),
        longitude=exif_data.get('longitude'),
        width=width,
        height=height,
        file_size=file_size,
    )
    db.session.add(photo)
    return photo


def _gps_to_decimal(coords, ref):
    """Convert GPS coordinates from EXIF format to decimal degrees."""
    if not coords or not ref:
        return None
    try:
        d, m, s = [float(x) for x in coords]
        decimal = d + m / 60 + s / 3600
        if ref in ('S', 'W'):
            decimal = -decimal
        return decimal
    except (TypeError, ValueError):
        return None
