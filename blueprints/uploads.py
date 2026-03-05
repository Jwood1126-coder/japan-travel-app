from flask import Blueprint, current_app, send_from_directory
from models import db, Photo
from datetime import datetime
import os
import uuid

uploads_bp = Blueprint('uploads', __name__)


@uploads_bp.route('/photos/originals/<filename>')
def serve_original(filename):
    return send_from_directory(
        os.path.join(current_app.config['UPLOAD_FOLDER'], 'originals'),
        filename)


@uploads_bp.route('/photos/thumbnails/<filename>')
def serve_thumbnail(filename):
    return send_from_directory(
        os.path.join(current_app.config['UPLOAD_FOLDER'], 'thumbnails'),
        filename)


def save_photo(file_obj, day_id=None):
    """Save an uploaded photo, generate thumbnail, extract EXIF."""
    allowed = {'jpg', 'jpeg', 'png', 'gif', 'heic', 'heif', 'webp'}
    ext = file_obj.filename.rsplit('.', 1)[-1].lower()
    if ext not in allowed:
        return None

    filename = f"{uuid.uuid4().hex}.{ext}"
    upload_dir = current_app.config['UPLOAD_FOLDER']
    original_path = os.path.join(upload_dir, 'originals', filename)
    file_obj.save(original_path)

    exif_data = {}
    width, height, file_size = 0, 0, os.path.getsize(original_path)
    thumb_filename = f"thumb_{filename.rsplit('.', 1)[0]}.jpg"
    thumb_path = os.path.join(upload_dir, 'thumbnails', thumb_filename)

    try:
        from PIL import Image, ImageOps
        from PIL.ExifTags import TAGS, GPSTAGS

        with Image.open(original_path) as img:
            img = ImageOps.exif_transpose(img)
            width, height = img.size

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

            img.thumbnail(current_app.config['THUMBNAIL_SIZE'],
                          Image.Resampling.LANCZOS)
            img.save(thumb_path, 'JPEG', quality=85)
    except Exception:
        thumb_filename = filename

    photo = Photo(
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


def save_chat_image(file_obj):
    """Save an image uploaded via chat. Returns (filename, original_path)."""
    allowed = {'jpg', 'jpeg', 'png', 'gif', 'heic', 'heif', 'webp'}
    ext = file_obj.filename.rsplit('.', 1)[-1].lower()
    if ext not in allowed:
        return None, None

    filename = f"{uuid.uuid4().hex}.{ext}"
    upload_dir = current_app.config['UPLOAD_FOLDER']
    original_path = os.path.join(upload_dir, 'originals', filename)
    file_obj.save(original_path)

    # Generate thumbnail
    thumb_filename = f"thumb_{filename.rsplit('.', 1)[0]}.jpg"
    thumb_path = os.path.join(upload_dir, 'thumbnails', thumb_filename)
    try:
        from PIL import Image, ImageOps
        with Image.open(original_path) as img:
            img = ImageOps.exif_transpose(img)
            img.thumbnail(current_app.config['THUMBNAIL_SIZE'],
                          Image.Resampling.LANCZOS)
            img.save(thumb_path, 'JPEG', quality=85)
    except Exception:
        pass

    return filename, original_path


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
