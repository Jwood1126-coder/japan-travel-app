"""Boot-time schedule validation — read-only.

Delegates to the trip audit service. Prints warnings on boot so developers
see issues immediately. The same audit runs before export to gate rendering.

This module performs NO data mutations. All data repair has been moved to
explicit scripts in scripts/ (repair_kyoto_overlap.py, etc.).
"""
from services.trip_audit import audit_trip


def validate_schedule(app):
    """Post-migration schedule validation. Prints warnings for conflicts.
    Runs on every boot to catch data issues early. Read-only — no mutations."""

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
