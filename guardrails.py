"""Runtime data integrity guardrails.

These validate inputs at API boundaries before they reach the database.
Boot-time validation lives in migrations/validate.py (advisory warnings).
These guardrails are enforcement — they reject bad data with errors.
"""

VALID_TIME_SLOTS = {'morning', 'afternoon', 'evening', 'night'}
VALID_BOOKING_STATUSES = {'not_booked', 'booked', 'confirmed', 'researching', 'cancelled'}


def validate_time_slot(time_slot):
    """Return cleaned time_slot or None. Raises ValueError if invalid."""
    if not time_slot:
        return None
    ts = time_slot.strip().lower()
    if ts not in VALID_TIME_SLOTS:
        raise ValueError(f"Invalid time_slot '{time_slot}'. Must be one of: {', '.join(sorted(VALID_TIME_SLOTS))}")
    return ts


def validate_booking_status(status):
    """Return cleaned booking_status. Raises ValueError if invalid."""
    if not status:
        return None
    s = status.strip().lower()
    if s not in VALID_BOOKING_STATUSES:
        raise ValueError(f"Invalid booking_status '{status}'. Must be one of: {', '.join(sorted(VALID_BOOKING_STATUSES))}")
    return s


def validate_non_negative(value, field_name):
    """Validate that a numeric value is non-negative. Returns float or None."""
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"'{field_name}' must be a number, got '{value}'")
    if v < 0:
        raise ValueError(f"'{field_name}' cannot be negative (got {v})")
    return v


def check_accom_date_overlap(location, exclude_location_id=None):
    """Check if an accommodation location's dates overlap with others.

    Returns a warning string if overlap detected, None otherwise.
    Only checks active locations (not all-eliminated).
    """
    from models import AccommodationLocation

    if not location.check_in_date or not location.check_out_date:
        return None

    all_locs = AccommodationLocation.query.order_by(
        AccommodationLocation.check_in_date).all()
    active_locs = [loc for loc in all_locs
                   if loc.id != (exclude_location_id or location.id)
                   and loc.options
                   and not all(o.is_eliminated for o in loc.options)]

    for other in active_locs:
        if not other.check_in_date or not other.check_out_date:
            continue
        # Overlap if one starts before the other ends and vice versa
        if (location.check_in_date < other.check_out_date and
                location.check_out_date > other.check_in_date):
            # Same-day checkout/checkin is allowed (transition day)
            if location.check_in_date == other.check_out_date:
                continue
            if location.check_out_date == other.check_in_date:
                continue
            return (f"Date overlap with {other.location_name} "
                    f"({other.check_in_date} - {other.check_out_date})")
    return None
