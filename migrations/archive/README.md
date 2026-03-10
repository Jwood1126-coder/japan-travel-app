# Archived Migration Functions

These migration functions have ALL been applied to the production database.
They are preserved here as reference only. **DO NOT import or run them.**

Each function is idempotent (checks if already applied before making changes),
but they should never need to run again on an existing database.

If you need to make data changes, use API endpoints, the AI chat, or a
one-time script in scripts/.

## Migration History

### migrations_001_to_019.py (lines 81-1319 of original app.py)
Early migrations: Kanazawa removal, Osaka restructure, checklist seeding,
booking URLs, guide URLs, location coords, substitute activities, activity
URLs, checklist consistency, itinerary revisions.

### migrations_020_to_039.py (lines 1320-5582 of original app.py)
Later migrations: 14-day restructure, Kyoto consolidation, address cleanup,
data cleanup, activity enrichment, Shinjuku hotels, booking resources,
neighborhood descriptions, maps URLs, Sotetsu Fresa booking, TAKANOYU booking,
audit fixes, transport checklist, production data reapply, transit directions,
Hakone route, calendar warnings, transport hardening, accom-checklist sync,
schedule consistency, confirmed bookings, fix TAKANOYU.
