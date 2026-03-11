#!/usr/bin/env python3
"""Repair script: downgrade eliminated options that still claim booked/confirmed.

The service layer prevents this state from being created (eliminate() rejects
booked/confirmed options). This script fixes legacy data where the invariant
was not enforced.

Run: python scripts/repair_eliminated_status.py [--dry-run]

Idempotent — safe to run repeatedly.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def repair_eliminated_status(dry_run=False):
    from app import create_app
    app = create_app(run_data_migrations=False)

    with app.app_context():
        from models import db, AccommodationOption, AccommodationLocation

        bad_opts = AccommodationOption.query.filter(
            AccommodationOption.is_eliminated == True,
            AccommodationOption.booking_status.in_(['booked', 'confirmed'])
        ).all()

        if not bad_opts:
            print("No eliminated options with booked/confirmed status found.")
            return False

        print(f"Found {len(bad_opts)} eliminated option(s) with active booking status:\n")
        for opt in bad_opts:
            loc = AccommodationLocation.query.get(opt.location_id)
            loc_name = loc.location_name if loc else '(unknown)'
            print(f"  '{opt.name}' at {loc_name}: "
                  f"{opt.booking_status} → cancelled")
            if not dry_run:
                opt.booking_status = 'cancelled'

        if dry_run:
            print(f"\n[DRY RUN] Would downgrade {len(bad_opts)} option(s) to 'cancelled'.")
        else:
            db.session.commit()
            print(f"\nDowngraded {len(bad_opts)} option(s) to 'cancelled'.")

        return True


if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv
    if dry_run:
        print("=== DRY RUN MODE (no changes will be written) ===\n")
    repair_eliminated_status(dry_run=dry_run)
