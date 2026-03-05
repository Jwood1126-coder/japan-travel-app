import re
from flask import Blueprint, render_template
from models import Location, Day

activities_bp = Blueprint('activities', __name__)

# Patterns that indicate logistics, not sightseeing/dining/experiences
_LOGISTICS_PATTERNS = re.compile(
    r'(?i)'
    r'^check\s*(in|out|into)\b'           # check-in/out
    r'|^activate\b'                        # activate passes/SIM
    r'|^pick\s+up\b'                       # pick up cards/WiFi
    r'|^arrange\b'                         # arrange luggage forwarding
    r'|^buy\s.*(pass|ticket)\b'            # buy passes
    r'|\bshinkansen\b'                     # bullet train transit
    r'|\bexpress\b.*→'                     # limited express transit
    r'|→'                                  # any A → B route
    r'|\bbus:'                             # bus routes
    r'|\bferry\b'                          # ferry transit
    r'|\bline\s+to\b'                      # train line to X
    r'|\blight\s+rail\b'                   # light rail
    r'|\bnarita\s+express\b'              # airport express
    r'|\bkeihan\s+line\b'                 # specific train line
    r'|^JR\s+(Special|Rapid|Limited|Hida)'  # JR transit routes
)

# Hotel-specific amenities tied to a particular accommodation
_HOTEL_AMENITY_PATTERNS = re.compile(
    r'(?i)'
    r'\bat\s+(dormy\s+inn|ryokan|hostel|toyoko|hotel)\b'
    r'|ryokan\s+breakfast'
    r'|kaiseki\s+dinner\s+at\s+ryokan'
)


def _is_browseable_activity(activity):
    """Return True if activity is a real experience, not logistics."""
    title = activity.title
    if _LOGISTICS_PATTERNS.search(title):
        return False
    if _HOTEL_AMENITY_PATTERNS.search(title):
        return False
    return True


@activities_bp.route('/activities')
def activities_view():
    locations = Location.query.order_by(Location.sort_order).all()
    days = Day.query.order_by(Day.day_number).all()

    location_activities = []
    for loc in locations:
        loc_days = [d for d in days if d.location_id == loc.id]
        activities = []
        for d in loc_days:
            for a in d.activities:
                if not a.is_substitute and _is_browseable_activity(a):
                    activities.append({'activity': a, 'day': d})
        if activities:
            location_activities.append({
                'location': loc,
                'activities': activities,
            })

    return render_template('activities.html',
                           location_activities=location_activities)
