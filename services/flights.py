"""Flight mutation service — single canonical write path.

Every mutation follows: validate → normalize → write → cascade → emit.
Both UI routes and AI chat tools call these functions.
"""
from models import db, Flight
from guardrails import validate_booking_status, validate_document_status
from extensions import socketio


def _strip_or_none(value):
    """Strip whitespace from string, return None if empty."""
    if value is None:
        return None
    if isinstance(value, str):
        v = value.strip()
        return v if v else None
    return value


def _emit_flight_updated(flight_id=None):
    """Emit Socket.IO event for any flight change."""
    socketio.emit('flight_updated', {'flight_id': flight_id})


def update(flight_id, fields):
    """Update an existing flight's fields.

    Args:
        flight_id: Flight record ID
        fields: dict with optional keys: booking_status, confirmation_number,
                depart_time, arrive_time, notes

    Returns:
        Updated Flight object

    Raises:
        ValueError: if booking_status is invalid or document-first rule violated
    """
    flight = Flight.query.get_or_404(flight_id)

    # Validate and set booking_status if provided
    if 'booking_status' in fields and fields['booking_status'] is not None:
        new_status = validate_booking_status(fields['booking_status'])
        validate_document_status(new_status, flight.document_id,
                                 f'flight {flight.flight_number}')
        flight.booking_status = new_status

    # String fields — normalize whitespace
    for field in ('confirmation_number', 'depart_time', 'arrive_time', 'notes'):
        if field in fields:
            setattr(flight, field, _strip_or_none(fields[field]))

    db.session.commit()
    _emit_flight_updated(flight.id)
    return flight
