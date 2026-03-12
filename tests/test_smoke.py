"""
Smoke tests for Japan Travel App.

Validates seed data integrity, route accessibility, and core invariants.
Run: python -m pytest tests/test_smoke.py -v
"""
import pytest
from datetime import date

from app import create_app
from models import (db, Trip, Day, Activity, Flight, AccommodationLocation,
                    AccommodationOption, TransportRoute, Location)

# -- Confirmed bookings (from Documentation/flights/ PDFs) --
# Kyoto Stay 2 (Apr 14-16) is open — Kyotofish Miyagawa cancelled
CONFIRMED_CHAIN = [
    ('Tokyo', 'Sotetsu Fresa Inn Higashi-Shinjuku', date(2026, 4, 6), date(2026, 4, 9), 3),
    ('Takayama', 'TAKANOYU', date(2026, 4, 9), date(2026, 4, 12), 3),
    ('Kyoto (Stay 1)', 'Tsukiya-Mikazuki', date(2026, 4, 12), date(2026, 4, 14), 2),
    ('Osaka', 'Hotel The Leben Osaka', date(2026, 4, 16), date(2026, 4, 18), 2),
]

STALE_HOTEL_NAMES = ['Dormy Inn', 'Piece Hostel', 'Toyoko Inn']


@pytest.fixture(scope='module')
def app():
    app = create_app(run_data_migrations=False)
    app.config['TESTING'] = True
    with app.app_context():
        yield app


@pytest.fixture(scope='module')
def client(app):
    return app.test_client()


# ---- Seed Data Integrity ----

class TestAccommodationChain:
    """Verify the confirmed accommodation chain matches PDF bookings."""

    def test_all_five_locations_have_selected_option(self, app):
        with app.app_context():
            for loc_name, hotel_name, *_ in CONFIRMED_CHAIN:
                locs = AccommodationLocation.query.filter(
                    AccommodationLocation.location_name.contains(loc_name.split('(')[0].strip())
                ).all()
                selected = []
                for loc in locs:
                    selected += [o for o in loc.options if o.is_selected]
                assert len(selected) >= 1, f"No selected option for {loc_name}"

    def test_selected_hotels_match_confirmed_names(self, app):
        with app.app_context():
            for loc_name, hotel_name, *_ in CONFIRMED_CHAIN:
                locs = AccommodationLocation.query.filter(
                    AccommodationLocation.location_name.contains(loc_name.split('(')[0].strip())
                ).all()
                selected_names = []
                for loc in locs:
                    selected_names += [o.name for o in loc.options if o.is_selected]
                assert any(hotel_name in n for n in selected_names), \
                    f"Expected '{hotel_name}' selected for {loc_name}, got {selected_names}"

    @pytest.mark.skip(reason="Kyoto Stay 2 open — gap in chain until replacement booked")
    def test_accommodation_dates_form_contiguous_chain(self, app):
        """Check-out of one stay == check-in of the next."""
        with app.app_context():
            booked = []
            for loc_name, hotel_name, check_in, check_out, nights in CONFIRMED_CHAIN:
                locs = AccommodationLocation.query.filter(
                    AccommodationLocation.location_name.contains(loc_name.split('(')[0].strip())
                ).all()
                for loc in locs:
                    for opt in loc.options:
                        if opt.is_selected and hotel_name in opt.name:
                            booked.append((loc_name, loc.check_in_date, loc.check_out_date))

            booked.sort(key=lambda x: x[1])
            for i in range(len(booked) - 1):
                curr_name, _, curr_out = booked[i]
                next_name, next_in, _ = booked[i + 1]
                assert str(curr_out) == str(next_in), \
                    f"Gap: {curr_name} checkout {curr_out} != {next_name} checkin {next_in}"

    def test_kanazawa_has_no_overnight(self, app):
        """Kanazawa is day-trip only — all options must be eliminated."""
        with app.app_context():
            locs = AccommodationLocation.query.filter(
                AccommodationLocation.location_name.contains('Kanazawa')
            ).all()
            for loc in locs:
                active = [o for o in loc.options if not o.is_eliminated]
                assert len(active) == 0, \
                    f"Kanazawa should have no active options, found: {[o.name for o in active]}"


class TestNoStaleReferences:
    """Ensure old hotel names don't leak into activity text."""

    def test_no_stale_hotel_names_in_activities(self, app):
        with app.app_context():
            activities = Activity.query.all()
            for act in activities:
                for stale in STALE_HOTEL_NAMES:
                    for field in [act.title, act.description, act.getting_there]:
                        if field:
                            assert stale not in field, \
                                f"Stale reference '{stale}' in Day activity '{act.title}': {field[:80]}"


class TestTransportRoutes:
    """Validate transport route integrity."""

    def test_no_self_referencing_routes(self, app):
        with app.app_context():
            routes = TransportRoute.query.all()
            for r in routes:
                assert r.route_from != r.route_to, \
                    f"Self-route: {r.route_from} → {r.route_to}"

    def test_kyoto_osaka_route_exists(self, app):
        with app.app_context():
            route = TransportRoute.query.filter_by(
                route_from='Kyoto', route_to='Osaka'
            ).first()
            assert route is not None, "Missing Kyoto → Osaka transport route"


class TestDayStructure:
    """Validate trip day structure."""

    def test_14_days_exist(self, app):
        with app.app_context():
            days = Day.query.all()
            assert len(days) == 14

    def test_days_cover_apr_5_to_18(self, app):
        with app.app_context():
            days = Day.query.order_by(Day.day_number).all()
            assert str(days[0].date) == '2026-04-05'
            assert str(days[-1].date) == '2026-04-18'

    def test_every_day_has_at_least_one_activity(self, app):
        with app.app_context():
            days = Day.query.all()
            for day in days:
                acts = Activity.query.filter_by(
                    day_id=day.id, is_substitute=False, is_eliminated=False
                ).all()
                assert len(acts) > 0, f"Day {day.day_number} ({day.title}) has no activities"


class TestFlights:
    """Validate flight records."""

    def test_four_flight_legs_exist(self, app):
        with app.app_context():
            flights = Flight.query.all()
            assert len(flights) == 4

    def test_outbound_flights(self, app):
        with app.app_context():
            outbound = Flight.query.filter_by(direction='outbound').order_by(Flight.leg_number).all()
            assert len(outbound) == 2
            assert 'DL' in outbound[0].flight_number or 'DL' in outbound[1].flight_number

    def test_return_flights(self, app):
        with app.app_context():
            ret = Flight.query.filter_by(direction='return').order_by(Flight.leg_number).all()
            assert len(ret) == 2
            assert 'UA' in ret[0].flight_number or 'UA' in ret[1].flight_number


# ---- Route Accessibility ----

class TestRoutes:
    """Every page should return 200."""

    @pytest.mark.parametrize('path', [
        '/',
        '/export',
        '/accommodations',
        '/calendar',
        '/checklists',
        '/activities',
        '/documents',
        '/chat',
        '/reference',
        '/book-ahead',
    ])
    def test_page_returns_200(self, client, path):
        resp = client.get(path)
        assert resp.status_code == 200, f"{path} returned {resp.status_code}"

    def test_day_view_returns_200(self, client):
        resp = client.get('/day/1')
        assert resp.status_code == 200

    def test_backup_download_returns_200(self, client):
        resp = client.get('/api/backup/download')
        assert resp.status_code == 200

    def test_backup_list_returns_200(self, client):
        resp = client.get('/api/backup/list')
        assert resp.status_code == 200


# ---- Export Quality ----

class TestExport:
    """Verify the export PDF contains correct data."""

    def test_export_contains_confirmed_hotels(self, client):
        resp = client.get('/export?force=1')
        html = resp.data.decode()
        for _, hotel_name, *_ in CONFIRMED_CHAIN:
            assert hotel_name in html, f"Export missing confirmed hotel: {hotel_name}"

    def test_export_has_no_stale_references(self, client):
        resp = client.get('/export?force=1')
        html = resp.data.decode()
        for stale in STALE_HOTEL_NAMES:
            assert stale not in html, f"Export contains stale reference: {stale}"

    def test_export_excludes_kanazawa(self, client):
        resp = client.get('/export?force=1')
        html = resp.data.decode()
        # Kanazawa should appear in transport but NOT in accommodation table
        accom_section = html.split('Accommodations')[1].split('Day-by-Day')[0]
        assert 'Kanazawa' not in accom_section
