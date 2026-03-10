"""Verify that all legacy migrations have been applied to this database.

These migrations ran in app.py prior to the decomposition. They are archived
in migrations/archive/ for reference. This function does NOT re-run them --
it only checks that the database is in the expected state.
"""

from models import (db, Trip, Activity, AccommodationLocation,
                    AccommodationOption, ChecklistItem, Flight,
                    TransportRoute)


def verify_legacy_migrations(app):
    """Check that all legacy data migrations have been applied."""
    warnings = []

    trip = Trip.query.first()
    if not trip:
        print("Legacy migrations: no trip data found (fresh database?)")
        return

    notes = trip.notes or ''

    # --- ChecklistItem-based sentinel ---
    if not ChecklistItem.query.filter_by(title='__checklist_v2_fixed').first():
        warnings.append("Missing sentinel: __checklist_v2_fixed (checklist v2 fix)")

    # --- Trip.notes sentinel checks ---
    expected_sentinels = [
        ('__prod_reapply_v1', 'production data reapply'),
        ('__transit_dirs_v1', 'transit directions'),
        ('__cal_warnings_v2', 'calendar warnings v2'),
        ('__transport_hardening_v1', 'transport hardening v1'),
        ('__sync_accom_checklist_v1', 'sync accom checklist'),
        ('__schedule_consistency_v1', 'schedule consistency'),
        ('__confirmed_bookings_v1', 'confirmed bookings'),
        ('__fix_takanoyu_v1', 'fix takanoyu'),
    ]

    for sentinel, label in expected_sentinels:
        if sentinel not in notes:
            warnings.append(f"Missing sentinel: {sentinel} ({label})")

    # --- Data marker checks (evidence that key migrations ran) ---
    checks = [
        (Activity.query.filter(Activity.getting_there.isnot(None)).count() > 30,
         "Transit directions: expected 30+ activities with getting_there"),
        (AccommodationLocation.query.count() >= 5,
         "Expected at least 5 accommodation locations"),
        (ChecklistItem.query.filter(
            ChecklistItem.title.ilike('%Hakone Free Pass%')).first() is not None,
         "Transport checklist: Hakone Free Pass item missing"),
        (Flight.query.count() >= 4,
         "Expected at least 4 flight legs"),
        (TransportRoute.query.count() >= 5,
         "Expected at least 5 transport routes"),
        (AccommodationOption.query.filter_by(
            name='TAKANOYU, Traditional Style, Spa & Sauna',
            is_selected=True).first() is not None,
         "TAKANOYU should be selected for Takayama"),
    ]

    for check_result, message in checks:
        if not check_result:
            warnings.append(message)

    if warnings:
        print("=" * 60)
        print("LEGACY MIGRATION VERIFICATION WARNINGS:")
        for w in warnings:
            print(f"  - {w}")
        print("These migrations may not have been applied to this database.")
        print("See migrations/archive/ for the original functions.")
        print("=" * 60)
    else:
        print("Legacy migrations: all verified")
