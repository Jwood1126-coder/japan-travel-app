from flask import Blueprint, render_template
from models import db, Activity, Day, Location

bookahead_bp = Blueprint('bookahead', __name__)


@bookahead_bp.route('/book-ahead')
def bookahead_view():
    """Activities that need advance tickets, reservations, or preparation."""
    days = Day.query.order_by(Day.day_number).all()
    locations = Location.query.order_by(Location.sort_order).all()

    # Build location lookup
    loc_by_id = {loc.id: loc for loc in locations}

    # Find all activities with book_ahead flag OR that have cost/url suggesting tickets
    items = []
    for d in days:
        loc = loc_by_id.get(d.location_id)
        for a in d.activities:
            if a.is_substitute or a.is_eliminated:
                continue
            if a.book_ahead:
                items.append({'activity': a, 'day': d, 'location': loc})

    return render_template('bookahead.html', items=items)
