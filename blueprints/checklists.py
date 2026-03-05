from flask import Blueprint, render_template, jsonify, request
from models import db, ChecklistItem, Flight, AccommodationLocation, \
    AccommodationOption, TransportRoute, Day, Activity, Trip
from datetime import datetime, date

checklists_bp = Blueprint('checklists', __name__)

# Map old categories to new groupings
CATEGORY_MAP = {
    'pre_departure_today': 'preparation',
    'pre_departure_week': 'preparation',
    'pre_departure_miles': 'booking',
    'pre_departure_month': 'booking',
    'packing_essential': 'packing',
    'packing_helpful': 'packing',
}

GROUP_LABELS = {
    'booking': 'Bookings & Tickets',
    'preparation': 'Preparation',
    'packing': 'Packing',
}

GROUP_ORDER = ['booking', 'preparation', 'packing']


@checklists_bp.route('/checklists')
def checklists_view():
    tab = request.args.get('tab', '')

    # Auto-select tab based on trip dates
    if not tab:
        trip = Trip.query.first()
        today = date.today()
        if trip and today >= trip.start_date:
            tab = 'on_trip'
        else:
            tab = 'pre_trip'

    if tab == 'on_trip':
        upcoming = _build_upcoming_events()
        return render_template('checklists.html', tab=tab, upcoming=upcoming,
                               categories=None, group_labels=None, group_order=None)

    # Pre-trip: group items
    items = ChecklistItem.query.order_by(ChecklistItem.sort_order).all()
    categories = {}
    for item in items:
        group = CATEGORY_MAP.get(item.category, 'preparation')
        categories.setdefault(group, []).append(item)

    return render_template('checklists.html', tab=tab, categories=categories,
                           group_labels=GROUP_LABELS, group_order=GROUP_ORDER,
                           upcoming=None)


def _build_upcoming_events():
    """Build dynamic list of upcoming logistics from itinerary data."""
    today = date.today()
    events = []

    # Upcoming flights
    flights = Flight.query.filter(
        Flight.depart_date >= today
    ).order_by(Flight.depart_date, Flight.depart_time).all()
    for f in flights:
        events.append({
            'type': 'flight',
            'date': f.depart_date,
            'time': f.depart_time,
            'title': f'{f.airline} {f.flight_number}',
            'subtitle': f'{f.route_from} \u2192 {f.route_to}',
            'status': f.booking_status or 'not_booked',
            'icon': '&#x2708;',
            'address': None,
        })

    # Accommodation check-ins
    checkins = AccommodationLocation.query.filter(
        AccommodationLocation.check_in_date >= today
    ).order_by(AccommodationLocation.check_in_date).all()
    for a in checkins:
        selected = AccommodationOption.query.filter_by(
            location_id=a.id, is_selected=True).first()
        name = selected.name if selected else a.location_name
        status = selected.booking_status if selected else 'not_booked'
        address = selected.address if selected else None
        events.append({
            'type': 'checkin',
            'date': a.check_in_date,
            'time': None,
            'title': f'Check in: {name}',
            'subtitle': a.location_name,
            'status': status,
            'icon': '&#x1f3e8;',
            'address': address,
        })

    # Accommodation check-outs
    checkouts = AccommodationLocation.query.filter(
        AccommodationLocation.check_out_date >= today
    ).order_by(AccommodationLocation.check_out_date).all()
    for a in checkouts:
        selected = AccommodationOption.query.filter_by(
            location_id=a.id, is_selected=True).first()
        if selected:
            events.append({
                'type': 'checkout',
                'date': a.check_out_date,
                'time': None,
                'title': f'Check out: {selected.name}',
                'subtitle': a.location_name,
                'status': 'info',
                'icon': '&#x1f6ce;',
                'address': selected.address,
            })

    # Transport routes
    days = Day.query.filter(Day.date >= today).order_by(Day.date).all()
    day_ids = [d.id for d in days]
    day_map = {d.id: d for d in days}

    routes = TransportRoute.query.filter(
        TransportRoute.day_id.in_(day_ids)
    ).order_by(TransportRoute.sort_order).all()
    for r in routes:
        day = day_map.get(r.day_id)
        events.append({
            'type': 'transport',
            'date': day.date if day else today,
            'time': None,
            'title': f'{r.route_from} \u2192 {r.route_to}',
            'subtitle': f'{r.transport_type} {r.train_name or ""}',
            'status': 'jr_covered' if r.jr_pass_covered else ('ticket_needed' if r.cost_if_not_covered else 'info'),
            'icon': '&#x1f686;',
            'address': None,
        })

    # Also find transport routes without day_id (matched by location)
    if not routes:
        for day in days:
            if day.day_number <= 1:
                continue
            prev = Day.query.filter_by(day_number=day.day_number - 1).first()
            if prev and prev.location and day.location and prev.location.name != day.location.name:
                found = TransportRoute.query.filter_by(
                    route_from=prev.location.name, route_to=day.location.name
                ).all()
                for r in found:
                    events.append({
                        'type': 'transport',
                        'date': day.date,
                        'time': None,
                        'title': f'{r.route_from} \u2192 {r.route_to}',
                        'subtitle': f'{r.transport_type} {r.train_name or ""}',
                        'status': 'jr_covered' if r.jr_pass_covered else ('ticket_needed' if r.cost_if_not_covered else 'info'),
                        'icon': '&#x1f686;',
                        'address': None,
                    })

    # Ticketed activities (cost > 0)
    for day in days:
        for a in day.activities:
            if a.cost_per_person and a.cost_per_person > 0 and not a.is_substitute and not a.is_completed:
                events.append({
                    'type': 'ticketed',
                    'date': day.date,
                    'time': a.start_time,
                    'title': a.title,
                    'subtitle': f'Day {day.day_number} \u2022 \u00a5{int(a.cost_per_person)}/person',
                    'status': 'upcoming',
                    'icon': '&#x1f3ab;',
                    'address': a.address,
                })

    # Sort by date, then time
    events.sort(key=lambda e: (e['date'], e['time'] or ''))
    return events


@checklists_bp.route('/api/checklists/<int:item_id>/toggle', methods=['POST'])
def toggle_checklist(item_id):
    item = ChecklistItem.query.get_or_404(item_id)
    item.is_completed = not item.is_completed
    item.completed_at = datetime.utcnow() if item.is_completed else None
    db.session.commit()

    from app import socketio
    socketio.emit('checklist_toggled', {
        'id': item.id,
        'is_completed': item.is_completed,
    })

    return jsonify({'ok': True, 'is_completed': item.is_completed})
