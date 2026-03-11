"""Boot-time schedule validation. Delegates to the trip audit service.

Prints warnings on boot so developers see issues immediately.
The same audit runs before export to gate rendering.
"""
from datetime import date as date_type
from models import AccommodationLocation, AccommodationOption, ChecklistItem, db
from services.trip_audit import audit_trip


def validate_schedule(app):
    """Post-migration schedule validation. Prints warnings for conflicts.
    Runs on every boot to catch data issues early."""

    # One-time fix: reconcile Kyoto accommodation overlap from legacy data
    _fix_kyoto_overlap()

    # Auto-fix: sync num_nights with date arithmetic (safety net)
    _autofix_num_nights()

    # Auto-fix: eliminated options should not claim confirmed/booked
    _autofix_eliminated_status()

    result = audit_trip()

    all_issues = result.blockers + result.warnings
    if all_issues:
        print(f"\n{'='*60}")
        print(f"SCHEDULE VALIDATION: {len(all_issues)} issue(s) "
              f"({len(result.blockers)} blockers, {len(result.warnings)} warnings)")
        print(f"{'='*60}")
        for b in result.blockers:
            print(f"  !! BLOCKER: {b}")
        for w in result.warnings:
            print(f"  !  {w}")
        if result.stale_refs:
            print(f"  (+ {len(result.stale_refs)} activities with stale hotel references)")
        print(f"{'='*60}\n")
    else:
        print("Schedule validation: all checks passed")


def _autofix_num_nights():
    """Safety net: sync stored num_nights with date arithmetic."""
    for loc in AccommodationLocation.query.all():
        if loc.check_in_date and loc.check_out_date:
            expected = (loc.check_out_date - loc.check_in_date).days
            if loc.num_nights != expected:
                old = loc.num_nights
                loc.num_nights = expected
                db.session.commit()
                print(f"  AUTO-FIX: '{loc.location_name}' num_nights {old} → {expected} "
                      f"(from dates {loc.check_in_date} to {loc.check_out_date})")


def _fix_kyoto_overlap():
    """One-time fix: reconcile overlapping Kyoto accommodation locations.

    Production DB has legacy data where Kyoto stays overlap. The confirmed
    booking chain is:
        Kyoto Stay 1 (Tsukiya-Mikazuki): Apr 12–14 (2 nights)
        Kyoto Stay 2 (Kyotofish Miyagawa): Apr 14–16 (2 nights)

    This fix:
    1. Corrects dates on any Kyoto location that overlaps with these ranges
    2. Merges duplicate Kyoto locations (e.g. "Kyoto Stay 2 (2 nights)" + "Kyoto Stay 2")
    3. Normalizes location names to "Kyoto (Stay 1)" / "Kyoto (Stay 2)"
    4. Ensures only one option per slot is selected (the canonical hotel)
    """
    # Canonical Kyoto dates from booking confirmations
    KYOTO_CANONICAL = {
        1: {'name': 'Kyoto (Stay 1)', 'check_in': date_type(2026, 4, 12),
            'check_out': date_type(2026, 4, 14), 'sort_order': 5,
            'hotel_keyword': 'tsukiya'},
        2: {'name': 'Kyoto (Stay 2)', 'check_in': date_type(2026, 4, 14),
            'check_out': date_type(2026, 4, 16), 'sort_order': 6,
            'hotel_keyword': 'kyotofish'},
    }

    # Broad search: catch all Kyoto-related accommodation locations
    kyoto_locs = AccommodationLocation.query.filter(
        AccommodationLocation.location_name.ilike('%kyoto%')
    ).order_by(AccommodationLocation.check_in_date).all()

    if not kyoto_locs:
        return  # No Kyoto locations found (shouldn't happen)

    print(f"  FIX-KYOTO: found {len(kyoto_locs)} Kyoto location(s): "
          f"{[(loc.id, loc.location_name) for loc in kyoto_locs]}")

    # Identify which canonical slot each location belongs to, by checking
    # which confirmed hotel is among its options (use direct query, not relationship)
    slot_map = {}  # canonical_slot_num -> list of matching locations
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
            # No confirmed hotel found — try matching by date proximity
            for slot_num, canon in KYOTO_CANONICAL.items():
                if loc.check_in_date and abs((loc.check_in_date - canon['check_in']).days) <= 1:
                    slot_map.setdefault(slot_num, []).append(loc)
                    break

    slot_info = {k: [(l.id, l.location_name) for l in v] for k, v in slot_map.items()}
    print(f"  FIX-KYOTO: slot mapping: {slot_info}")

    changed = False
    for slot_num, canon in KYOTO_CANONICAL.items():
        locs_for_slot = slot_map.get(slot_num, [])
        if not locs_for_slot:
            continue

        # Pick the primary location (the one with the confirmed hotel selected)
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

        # If no selected match, pick the first one
        if primary is None:
            primary = locs_for_slot[0]
            duplicates = locs_for_slot[1:]

        # Fix dates on primary location
        if (primary.check_in_date != canon['check_in'] or
                primary.check_out_date != canon['check_out']):
            old_in, old_out = primary.check_in_date, primary.check_out_date
            primary.check_in_date = canon['check_in']
            primary.check_out_date = canon['check_out']
            primary.num_nights = (canon['check_out'] - canon['check_in']).days
            changed = True
            print(f"  FIX-KYOTO: '{primary.location_name}' dates "
                  f"{old_in}–{old_out} → {canon['check_in']}–{canon['check_out']}")

        # Fix name
        if primary.location_name != canon['name']:
            old_name = primary.location_name
            primary.location_name = canon['name']
            changed = True
            print(f"  FIX-KYOTO: renamed '{old_name}' → '{canon['name']}'")

        # Fix sort_order
        if primary.sort_order != canon['sort_order']:
            primary.sort_order = canon['sort_order']
            changed = True

        # Merge duplicates: move options + checklist refs to primary, then delete
        # Use direct queries instead of relationship to avoid stale cache issues
        for dup in duplicates:
            print(f"  FIX-KYOTO: merging duplicate '{dup.location_name}' (id={dup.id}) "
                  f"into '{primary.location_name}' (id={primary.id})")

            dup_opts = AccommodationOption.query.filter_by(location_id=dup.id).all()
            primary_opts = AccommodationOption.query.filter_by(location_id=primary.id).all()
            primary_names = {(o.name or '').lower() for o in primary_opts}
            max_rank = max((o.rank for o in primary_opts), default=0)

            for opt in dup_opts:
                opt_name_lower = (opt.name or '').lower()
                if opt_name_lower in primary_names:
                    # Duplicate option — delete it
                    print(f"    deleting duplicate option '{opt.name}' (id={opt.id})")
                    db.session.delete(opt)
                else:
                    # Move option to primary location
                    max_rank += 1
                    print(f"    moving option '{opt.name}' (id={opt.id}) → rank {max_rank}")
                    opt.location_id = primary.id
                    opt.rank = max_rank
                    primary_names.add(opt_name_lower)

            # Flush moves/deletes BEFORE deleting the location to avoid
            # SQLAlchemy relationship cascade nullifying moved options
            db.session.flush()

            # Reassign checklist items pointing to the duplicate
            for cl in ChecklistItem.query.filter_by(
                    accommodation_location_id=dup.id).all():
                cl.accommodation_location_id = primary.id

            db.session.delete(dup)
            db.session.flush()
            changed = True

        # After merge, ensure only the canonical hotel is selected at this location
        all_opts = AccommodationOption.query.filter_by(location_id=primary.id).all()
        canonical_opt = None
        for opt in all_opts:
            if canon['hotel_keyword'] in (opt.name or '').lower():
                if canonical_opt is None:
                    canonical_opt = opt
                else:
                    # Multiple options matching the keyword — keep the first selected
                    if opt.is_selected and not canonical_opt.is_selected:
                        canonical_opt = opt
        # Deselect all, then select only the canonical one
        for opt in all_opts:
            if opt.is_selected and opt != canonical_opt:
                print(f"  FIX-KYOTO: deselecting '{opt.name}' (not the canonical hotel)")
                opt.is_selected = False
                changed = True
        if canonical_opt and not canonical_opt.is_selected:
            print(f"  FIX-KYOTO: selecting canonical '{canonical_opt.name}'")
            canonical_opt.is_selected = True
            changed = True

    if changed:
        db.session.commit()
        print("  FIX-KYOTO: Kyoto accommodation overlap resolved")
    else:
        print("  FIX-KYOTO: no changes needed (data already clean)")


def _autofix_eliminated_status():
    """Downgrade eliminated options that still claim booked/confirmed."""
    for loc in AccommodationLocation.query.all():
        for opt in loc.options:
            if opt.is_eliminated and opt.booking_status in ('confirmed', 'booked'):
                old_status = opt.booking_status
                opt.booking_status = 'cancelled'
                db.session.commit()
                print(f"  AUTO-FIX: '{opt.name}' was eliminated but {old_status} "
                      f"— downgraded to cancelled")
