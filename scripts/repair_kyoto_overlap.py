#!/usr/bin/env python3
"""Repair script: reconcile overlapping Kyoto accommodation locations.

This handles legacy production data where Kyoto stays were duplicated
or had incorrect date ranges. It:
1. Corrects dates on Kyoto locations to match booking confirmations
2. Merges duplicate locations (moves options, reassigns checklist FKs)
3. Normalizes names to "Kyoto (Stay 1)" / "Kyoto (Stay 2)"
4. Ensures only the canonical hotel is selected per slot

Run: python scripts/repair_kyoto_overlap.py [--dry-run]

This script is idempotent — safe to run repeatedly. When data is already
clean it reports "no changes needed" and exits.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import date as date_type


def repair_kyoto_overlap(dry_run=False):
    from app import create_app
    app = create_app(run_data_migrations=False)

    with app.app_context():
        from models import (db, AccommodationLocation, AccommodationOption,
                            ChecklistItem)

        # Canonical Kyoto dates from booking confirmations
        KYOTO_CANONICAL = {
            1: {'name': 'Kyoto (Stay 1)', 'check_in': date_type(2026, 4, 12),
                'check_out': date_type(2026, 4, 14), 'sort_order': 5,
                'hotel_keyword': 'tsukiya'},
            2: {'name': 'Kyoto (Stay 2)', 'check_in': date_type(2026, 4, 14),
                'check_out': date_type(2026, 4, 16), 'sort_order': 6,
                'hotel_keyword': 'kyotofish'},
        }

        kyoto_locs = AccommodationLocation.query.filter(
            AccommodationLocation.location_name.ilike('%kyoto%')
        ).order_by(AccommodationLocation.check_in_date).all()

        if not kyoto_locs:
            print("No Kyoto locations found — nothing to repair.")
            return False

        print(f"Found {len(kyoto_locs)} Kyoto location(s):")
        for loc in kyoto_locs:
            opts = AccommodationOption.query.filter_by(location_id=loc.id).all()
            print(f"  id={loc.id} '{loc.location_name}' "
                  f"{loc.check_in_date}–{loc.check_out_date} "
                  f"({len(opts)} options)")

        # Map locations to canonical slots
        slot_map = {}
        for loc in kyoto_locs:
            opts = AccommodationOption.query.filter_by(location_id=loc.id).all()
            matched = False
            for slot_num, canon in KYOTO_CANONICAL.items():
                keyword = canon['hotel_keyword']
                if any(keyword in (opt.name or '').lower() for opt in opts):
                    slot_map.setdefault(slot_num, []).append(loc)
                    matched = True
                    break
            if not matched:
                for slot_num, canon in KYOTO_CANONICAL.items():
                    if loc.check_in_date and abs((loc.check_in_date - canon['check_in']).days) <= 1:
                        slot_map.setdefault(slot_num, []).append(loc)
                        break

        print(f"\nSlot mapping:")
        for k, v in slot_map.items():
            print(f"  Slot {k}: {[(l.id, l.location_name) for l in v]}")

        changed = False
        for slot_num, canon in KYOTO_CANONICAL.items():
            locs_for_slot = slot_map.get(slot_num, [])
            if not locs_for_slot:
                continue

            # Pick primary (the one with confirmed hotel selected)
            primary = None
            duplicates = []
            for loc in locs_for_slot:
                opts = AccommodationOption.query.filter_by(location_id=loc.id).all()
                has_confirmed = any(
                    canon['hotel_keyword'] in (opt.name or '').lower()
                    and opt.is_selected
                    for opt in opts
                )
                if has_confirmed and primary is None:
                    primary = loc
                else:
                    duplicates.append(loc)

            if primary is None:
                primary = locs_for_slot[0]
                duplicates = locs_for_slot[1:]

            # Fix dates
            if (primary.check_in_date != canon['check_in'] or
                    primary.check_out_date != canon['check_out']):
                print(f"\n  FIX dates: '{primary.location_name}' "
                      f"{primary.check_in_date}–{primary.check_out_date} → "
                      f"{canon['check_in']}–{canon['check_out']}")
                if not dry_run:
                    primary.check_in_date = canon['check_in']
                    primary.check_out_date = canon['check_out']
                    primary.num_nights = (canon['check_out'] - canon['check_in']).days
                changed = True

            # Fix name
            if primary.location_name != canon['name']:
                print(f"  FIX name: '{primary.location_name}' → '{canon['name']}'")
                if not dry_run:
                    primary.location_name = canon['name']
                changed = True

            # Fix sort_order
            if primary.sort_order != canon['sort_order']:
                if not dry_run:
                    primary.sort_order = canon['sort_order']
                changed = True

            # Merge duplicates
            for dup in duplicates:
                print(f"\n  MERGE: '{dup.location_name}' (id={dup.id}) "
                      f"into '{primary.location_name}' (id={primary.id})")

                dup_opts = AccommodationOption.query.filter_by(location_id=dup.id).all()
                primary_opts = AccommodationOption.query.filter_by(location_id=primary.id).all()
                primary_names = {(o.name or '').lower() for o in primary_opts}
                max_rank = max((o.rank for o in primary_opts), default=0)

                for opt in dup_opts:
                    opt_name_lower = (opt.name or '').lower()
                    if opt_name_lower in primary_names:
                        print(f"    DELETE duplicate option '{opt.name}' (id={opt.id})")
                        if not dry_run:
                            db.session.delete(opt)
                    else:
                        max_rank += 1
                        print(f"    MOVE option '{opt.name}' (id={opt.id}) → rank {max_rank}")
                        if not dry_run:
                            opt.location_id = primary.id
                            opt.rank = max_rank
                        primary_names.add(opt_name_lower)

                if not dry_run:
                    db.session.flush()

                # Reassign checklist items
                cls = ChecklistItem.query.filter_by(
                    accommodation_location_id=dup.id).all()
                for cl in cls:
                    print(f"    REASSIGN checklist '{cl.title}' → location {primary.id}")
                    if not dry_run:
                        cl.accommodation_location_id = primary.id

                print(f"    DELETE location '{dup.location_name}' (id={dup.id})")
                if not dry_run:
                    db.session.delete(dup)
                    db.session.flush()
                changed = True

            # Ensure only canonical hotel is selected
            all_opts = AccommodationOption.query.filter_by(location_id=primary.id).all()
            canonical_opt = None
            for opt in all_opts:
                if canon['hotel_keyword'] in (opt.name or '').lower():
                    if canonical_opt is None:
                        canonical_opt = opt
                    elif opt.is_selected and not canonical_opt.is_selected:
                        canonical_opt = opt

            for opt in all_opts:
                if opt.is_selected and opt != canonical_opt:
                    print(f"  DESELECT '{opt.name}' (not the canonical hotel)")
                    if not dry_run:
                        opt.is_selected = False
                    changed = True
            if canonical_opt and not canonical_opt.is_selected:
                print(f"  SELECT canonical '{canonical_opt.name}'")
                if not dry_run:
                    canonical_opt.is_selected = True
                changed = True

        if changed:
            if dry_run:
                print("\n[DRY RUN] Would commit the above changes.")
            else:
                db.session.commit()
                print("\nKyoto overlap repair committed successfully.")
        else:
            print("\nNo changes needed — data is already clean.")

        return changed


if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv
    if dry_run:
        print("=== DRY RUN MODE (no changes will be written) ===\n")
    repair_kyoto_overlap(dry_run=dry_run)
