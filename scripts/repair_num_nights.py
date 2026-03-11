#!/usr/bin/env python3
"""Repair script: sync stored num_nights with date arithmetic.

The service layer (update_location_dates) already enforces this at mutation
time. This script fixes legacy data where num_nights drifted from dates.

Run: python scripts/repair_num_nights.py [--dry-run]

Idempotent — safe to run repeatedly.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def repair_num_nights(dry_run=False):
    from app import create_app
    app = create_app(run_data_migrations=False)

    with app.app_context():
        from models import db, AccommodationLocation

        fixed = 0
        for loc in AccommodationLocation.query.all():
            if loc.check_in_date and loc.check_out_date:
                expected = (loc.check_out_date - loc.check_in_date).days
                if loc.num_nights != expected:
                    print(f"  '{loc.location_name}': num_nights {loc.num_nights} → "
                          f"{expected} (from {loc.check_in_date} to {loc.check_out_date})")
                    if not dry_run:
                        loc.num_nights = expected
                    fixed += 1

        if fixed == 0:
            print("All num_nights values match date arithmetic. No fixes needed.")
            return False

        if dry_run:
            print(f"\n[DRY RUN] Would fix {fixed} location(s).")
        else:
            db.session.commit()
            print(f"\nFixed {fixed} location(s).")

        return True


if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv
    if dry_run:
        print("=== DRY RUN MODE (no changes will be written) ===\n")
    repair_num_nights(dry_run=dry_run)
