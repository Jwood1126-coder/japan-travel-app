import os
import re
import uuid
from flask import (Blueprint, render_template, jsonify, request,
                   send_from_directory, current_app)
from werkzeug.utils import secure_filename
from models import db, Flight, AccommodationLocation, AccommodationOption, TransportRoute, Location, Day

documents_bp = Blueprint('documents', __name__)

VALID_BOOKING_STATUSES = {'not_booked', 'researching', 'booked', 'confirmed', 'cancelled'}
ALLOWED_DOC_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'webp'}


def _docs_folder():
    """Return path to documents storage folder, creating if needed."""
    folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'documents')
    os.makedirs(folder, exist_ok=True)
    return folder


def _get_saved_documents():
    """List all uploaded document files from the documents folder."""
    folder = _docs_folder()
    docs = []
    if os.path.isdir(folder):
        for fname in sorted(os.listdir(folder)):
            ext = fname.rsplit('.', 1)[-1].lower() if '.' in fname else ''
            if ext in ALLOWED_DOC_EXTENSIONS:
                # Extract display name: remove UUID prefix if present
                display = fname
                # Format: uuid__originalname.ext
                if '__' in fname:
                    display = fname.split('__', 1)[1]
                docs.append({
                    'filename': fname,
                    'display_name': display,
                    'ext': ext,
                    'is_pdf': ext == 'pdf',
                })
    return docs


def _match_docs_to_bookings(docs, accommodations, flights):
    """Match uploaded docs to bookings by confirmation number or name keywords."""
    links = {}  # key: 'accom_{loc_id}' or 'flight_{flight_id}', value: list of doc filenames

    for item in accommodations:
        opt = item['selected']
        loc = item['location']
        key = f'accom_{loc.id}'
        links[key] = []
        for doc in docs:
            fname_lower = doc['display_name'].lower()
            # Match by confirmation number
            if opt.confirmation_number and opt.confirmation_number.lower() in fname_lower:
                links[key].append(doc)
                continue
            # Match by accommodation name keywords
            name_words = opt.name.lower().split()
            if any(w in fname_lower for w in name_words if len(w) > 3):
                links[key].append(doc)
                continue
            # Match by location name (word boundary to avoid "kyoto" matching "kyotofish")
            loc_lower = loc.location_name.lower().replace('stay 1', '').replace('stay 2', '').strip()
            if loc_lower and re.search(r'\b' + re.escape(loc_lower) + r'\b', fname_lower):
                links[key].append(doc)
                continue
            # Match by date range (e.g. "Apr 12 – 14" or "Apr_12_14")
            if loc.check_in_date and loc.check_out_date:
                ci = loc.check_in_date
                co = loc.check_out_date
                month = ci.strftime('%b').lower()  # "apr"
                date_patterns = [
                    f'{month}_{ci.day}_{co.day}',
                    f'{month} {ci.day}',
                ]
                if any(p in fname_lower for p in date_patterns):
                    links[key].append(doc)

    for flight in flights:
        key = f'flight_{flight.id}'
        links[key] = []
        for doc in docs:
            fname_lower = doc['display_name'].lower()
            if flight.confirmation_number and flight.confirmation_number.lower() in fname_lower:
                links[key].append(doc)
                continue
            if flight.flight_number and flight.flight_number.lower() in fname_lower:
                links[key].append(doc)

    return links


@documents_bp.route('/documents')
def documents_view():
    flights = Flight.query.order_by(Flight.direction, Flight.leg_number).all()

    # Only show booked or confirmed accommodations
    accom_locations = AccommodationLocation.query.order_by(
        AccommodationLocation.check_in_date).all()
    accommodations = []
    for loc in accom_locations:
        selected = next((o for o in loc.options if o.is_selected), None)
        if selected and selected.booking_status in ('booked', 'confirmed'):
            accommodations.append({'location': loc, 'selected': selected})

    transport = TransportRoute.query.order_by(TransportRoute.sort_order).all()

    # Activities with tickets/bookings (have URL or cost)
    locations = Location.query.order_by(Location.sort_order).all()
    days = Day.query.order_by(Day.day_number).all()
    ticketed_activities = []
    for loc in locations:
        loc_days = [d for d in days if d.location_id == loc.id]
        for d in loc_days:
            for a in d.activities:
                if a.is_substitute or a.is_eliminated:
                    continue
                if a.url or a.cost_per_person:
                    ticketed_activities.append({
                        'activity': a, 'day': d, 'location': loc
                    })

    # Uploaded documents (PDFs, images)
    saved_docs = _get_saved_documents()

    # Link documents to accommodations and flights by matching keywords
    doc_links = _match_docs_to_bookings(saved_docs, accommodations, flights)

    return render_template('documents.html',
                           flights=flights,
                           accommodations=accommodations,
                           transport=transport,
                           ticketed_activities=ticketed_activities,
                           saved_docs=saved_docs,
                           doc_links=doc_links)


@documents_bp.route('/api/documents/flight/<int:flight_id>/confirmation',
                     methods=['PUT'])
def update_flight_confirmation(flight_id):
    flight = Flight.query.get_or_404(flight_id)
    data = request.get_json()
    new_status = data.get('booking_status')
    if new_status is not None:
        if new_status not in VALID_BOOKING_STATUSES:
            return jsonify({'ok': False, 'error': 'Invalid status'}), 400
        flight.booking_status = new_status
    flight.confirmation_number = data.get('confirmation_number',
                                          flight.confirmation_number)
    db.session.commit()

    from app import socketio
    socketio.emit('document_updated', {'type': 'flight', 'id': flight.id})

    return jsonify({'ok': True})


@documents_bp.route('/api/documents/upload', methods=['POST'])
def upload_document():
    """Upload a PDF or image document."""
    if 'file' not in request.files:
        return jsonify({'ok': False, 'error': 'No file provided'}), 400

    f = request.files['file']
    if not f.filename:
        return jsonify({'ok': False, 'error': 'No file selected'}), 400

    ext = f.filename.rsplit('.', 1)[-1].lower() if '.' in f.filename else ''
    if ext not in ALLOWED_DOC_EXTENSIONS:
        return jsonify({'ok': False, 'error': f'File type .{ext} not allowed'}), 400

    original_name = secure_filename(f.filename)
    unique_name = f"{uuid.uuid4().hex[:8]}__{original_name}"
    filepath = os.path.join(_docs_folder(), unique_name)
    f.save(filepath)

    return jsonify({
        'ok': True,
        'filename': unique_name,
        'display_name': original_name,
    })


@documents_bp.route('/api/documents/file/<path:filename>')
def serve_document(filename):
    """Serve an uploaded document file."""
    return send_from_directory(_docs_folder(), filename)


@documents_bp.route('/api/documents/file/<path:filename>', methods=['DELETE'])
def delete_document(filename):
    """Delete an uploaded document."""
    docs_dir = os.path.realpath(_docs_folder())
    filepath = os.path.realpath(os.path.join(docs_dir, os.path.basename(filename)))
    if not filepath.startswith(docs_dir + os.sep):
        return jsonify({'ok': False, 'error': 'Invalid filename'}), 400
    if os.path.exists(filepath):
        os.remove(filepath)
        return jsonify({'ok': True})
    return jsonify({'ok': False, 'error': 'File not found'}), 404
