#!/usr/bin/env python3
"""
One-time script to update the local DB to match confirmed bookings.

The local DB is built from source_data/ markdown (original plan).
Production DB had 39 migrations applied to reach correct state.
This script applies the key data fixes for local development/testing.

Run: python scripts/fix_local_db.py
"""
import sqlite3
import os
import sys

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'japan_trip.db')
DB_PATH = os.path.abspath(DB_PATH)

if not os.path.exists(DB_PATH):
    print(f"DB not found at {DB_PATH}. Run import_markdown.py first.")
    sys.exit(1)

conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA foreign_keys = ON")
c = conn.cursor()


def log(msg):
    print(f"  ✓ {msg}")


print("\n=== Fixing local DB to match confirmed bookings ===\n")

# --- 1. Fix Tokyo accommodation ---
print("1. Tokyo accommodation")
# Select Sotetsu Fresa Inn, eliminate others
c.execute("UPDATE accommodation_option SET is_selected = 0 WHERE location_id = 1")
c.execute("""
    UPDATE accommodation_option SET
        is_selected = 1,
        booking_status = 'booked',
        confirmation_number = '976558450',
        booking_url = 'https://www.agoda.com/'
    WHERE location_id = 1 AND name LIKE '%Sotetsu Fresa%'
""")
if c.rowcount:
    log("Selected Sotetsu Fresa Inn (Agoda #976558450)")
else:
    log("Sotetsu Fresa Inn not found — check option name")
# Eliminate non-selected Tokyo options
c.execute("""
    UPDATE accommodation_option SET is_eliminated = 1, booking_status = 'not_booked'
    WHERE location_id = 1 AND is_selected = 0
""")
log(f"Eliminated {c.rowcount} other Tokyo options")

# --- 2. Fix Takayama accommodation ---
print("\n2. Takayama accommodation")
# Merge the two Takayama locations into one: Ryokan location gets full dates
c.execute("""
    UPDATE accommodation_location SET
        location_name = 'Takayama',
        check_in_date = '2026-04-09',
        check_out_date = '2026-04-12',
        num_nights = 3
    WHERE id = 2
""")
log("Updated Takayama Ryokan → Takayama (Apr 9-12, 3N)")

# Add TAKANOYU as new option in location 2
c.execute("SELECT MAX(rank) FROM accommodation_option WHERE location_id = 2")
max_rank = c.fetchone()[0] or 0
c.execute("""
    INSERT OR IGNORE INTO accommodation_option
        (location_id, name, rank, is_selected, booking_status, confirmation_number)
    VALUES (2, 'TAKANOYU', ?, 1, 'booked', 'HMDDRX4NFX')
""", (max_rank + 1,))
if c.rowcount:
    log("Added TAKANOYU (Airbnb #HMDDRX4NFX)")
else:
    # Maybe it already exists
    c.execute("UPDATE accommodation_option SET is_selected = 1, booking_status = 'booked', confirmation_number = 'HMDDRX4NFX' WHERE location_id = 2 AND name = 'TAKANOYU'")
    log("Updated existing TAKANOYU option")

# Eliminate other Takayama Ryokan options
c.execute("UPDATE accommodation_option SET is_eliminated = 1 WHERE location_id = 2 AND name != 'TAKANOYU'")
log(f"Eliminated {c.rowcount} other Takayama Ryokan options")

# Eliminate ALL Budget location options and mark location as unused
c.execute("UPDATE accommodation_option SET is_eliminated = 1 WHERE location_id = 3")
log(f"Eliminated {c.rowcount} Takayama Budget options")
c.execute("UPDATE accommodation_location SET check_in_date = '2026-04-09', check_out_date = '2026-04-12', num_nights = 3 WHERE id = 3")

# --- 3. Fix Kanazawa — eliminate all (day trip only) ---
print("\n3. Kanazawa (day trip only — no overnight)")
c.execute("UPDATE accommodation_option SET is_eliminated = 1, booking_status = 'cancelled' WHERE location_id = 4")
log(f"Eliminated {c.rowcount} Kanazawa options")

# --- 4. Fix Kyoto Stay 1 ---
print("\n4. Kyoto Stay 1")
c.execute("""
    UPDATE accommodation_location SET
        location_name = 'Kyoto (Stay 1)',
        check_in_date = '2026-04-12',
        check_out_date = '2026-04-14',
        num_nights = 2
    WHERE id = 5
""")
log("Updated Kyoto (3 nights) → Kyoto (Stay 1) Apr 12-14 (2N)")

# Add Tsukiya-Mikazuki
c.execute("SELECT MAX(rank) FROM accommodation_option WHERE location_id = 5")
max_rank = c.fetchone()[0] or 0
c.execute("""
    INSERT OR IGNORE INTO accommodation_option
        (location_id, name, rank, is_selected, booking_status, confirmation_number)
    VALUES (5, 'Tsukiya-Mikazuki', ?, 1, 'booked', 'HMXTP9H2Z9')
""", (max_rank + 1,))
if c.rowcount:
    log("Added Tsukiya-Mikazuki (Airbnb #HMXTP9H2Z9)")
else:
    c.execute("UPDATE accommodation_option SET is_selected = 1, booking_status = 'booked', confirmation_number = 'HMXTP9H2Z9' WHERE location_id = 5 AND name = 'Tsukiya-Mikazuki'")
    log("Updated existing Tsukiya-Mikazuki")

# Eliminate other Kyoto Stay 1 options
c.execute("UPDATE accommodation_option SET is_selected = 0, is_eliminated = 1 WHERE location_id = 5 AND name != 'Tsukiya-Mikazuki'")
log(f"Eliminated {c.rowcount} other Kyoto Stay 1 options")

# --- 5. Fix Kyoto Stay 2 ---
print("\n5. Kyoto Stay 2")
c.execute("""
    UPDATE accommodation_location SET
        location_name = 'Kyoto (Stay 2)',
        check_in_date = '2026-04-14',
        check_out_date = '2026-04-16',
        num_nights = 2
    WHERE id = 6
""")
log("Updated Kyoto Machiya → Kyoto (Stay 2) Apr 14-16 (2N)")

# Add Kyotofish Miyagawa
c.execute("SELECT MAX(rank) FROM accommodation_option WHERE location_id = 6")
max_rank = c.fetchone()[0] or 0
c.execute("""
    INSERT OR IGNORE INTO accommodation_option
        (location_id, name, rank, is_selected, booking_status, confirmation_number)
    VALUES (6, 'Kyotofish Miyagawa', ?, 1, 'booked', NULL)
""", (max_rank + 1,))
if c.rowcount:
    log("Added Kyotofish Miyagawa (host Karen)")
else:
    c.execute("UPDATE accommodation_option SET is_selected = 1, booking_status = 'booked' WHERE location_id = 6 AND name = 'Kyotofish Miyagawa'")
    log("Updated existing Kyotofish Miyagawa")

# Eliminate other Kyoto Stay 2 options
c.execute("UPDATE accommodation_option SET is_selected = 0, is_eliminated = 1 WHERE location_id = 6 AND name != 'Kyotofish Miyagawa'")
log(f"Eliminated {c.rowcount} other Kyoto Stay 2 options")

# --- 6. Add Osaka accommodation ---
print("\n6. Osaka accommodation")
c.execute("SELECT id FROM accommodation_location WHERE location_name LIKE '%Osaka%'")
osaka_loc = c.fetchone()
if not osaka_loc:
    c.execute("""
        INSERT INTO accommodation_location
            (location_name, check_in_date, check_out_date, num_nights, sort_order)
        VALUES ('Osaka', '2026-04-16', '2026-04-18', 2, 7)
    """)
    osaka_loc_id = c.lastrowid
    log(f"Created Osaka accommodation location (id={osaka_loc_id})")
    c.execute("""
        INSERT INTO accommodation_option
            (location_id, name, rank, is_selected, booking_status, confirmation_number, booking_url)
        VALUES (?, 'Hotel The Leben Osaka', 1, 1, 'booked', '976698966', 'https://www.agoda.com/')
    """, (osaka_loc_id,))
    log("Added Hotel The Leben Osaka (Agoda #976698966)")
else:
    log(f"Osaka location already exists (id={osaka_loc[0]})")

# --- 7. Fix stale hotel references in activities ---
print("\n7. Fixing stale hotel references in activities")

# Dormy Inn → Sotetsu Fresa Inn
for field in ['title', 'description', 'getting_there']:
    c.execute(f"""
        UPDATE activity SET {field} = REPLACE({field}, 'Dormy Inn Asakusa', 'Sotetsu Fresa Inn')
        WHERE {field} LIKE '%Dormy Inn Asakusa%'
    """)
    if c.rowcount:
        log(f"Replaced 'Dormy Inn Asakusa' → 'Sotetsu Fresa Inn' in {field} ({c.rowcount} rows)")

for field in ['title', 'description', 'getting_there']:
    c.execute(f"""
        UPDATE activity SET {field} = REPLACE({field}, 'Dormy Inn', 'Sotetsu Fresa Inn')
        WHERE {field} LIKE '%Dormy Inn%'
    """)
    if c.rowcount:
        log(f"Replaced 'Dormy Inn' → 'Sotetsu Fresa Inn' in {field} ({c.rowcount} rows)")

# Piece Hostel → Tsukiya-Mikazuki (Kyoto Stay 1 accommodation)
for field in ['title', 'description', 'getting_there']:
    c.execute(f"""
        UPDATE activity SET {field} = REPLACE({field}, 'Piece Hostel Sanjo', 'Tsukiya-Mikazuki')
        WHERE {field} LIKE '%Piece Hostel Sanjo%'
    """)
    if c.rowcount:
        log(f"Replaced 'Piece Hostel Sanjo' → 'Tsukiya-Mikazuki' in {field} ({c.rowcount} rows)")

for field in ['title', 'description', 'getting_there']:
    c.execute(f"""
        UPDATE activity SET {field} = REPLACE({field}, 'Piece Hostel', 'Tsukiya-Mikazuki')
        WHERE {field} LIKE '%Piece Hostel%'
    """)
    if c.rowcount:
        log(f"Replaced 'Piece Hostel' → 'Tsukiya-Mikazuki' in {field} ({c.rowcount} rows)")

# Toyoko Inn Shinagawa → Hotel The Leben Osaka
for field in ['title', 'description', 'getting_there']:
    c.execute(f"""
        UPDATE activity SET {field} = REPLACE({field}, 'Toyoko Inn Shinagawa', 'Hotel The Leben Osaka')
        WHERE {field} LIKE '%Toyoko Inn Shinagawa%'
    """)
    if c.rowcount:
        log(f"Replaced 'Toyoko Inn Shinagawa' → 'Hotel The Leben Osaka' in {field} ({c.rowcount} rows)")

# Fix "rooftop onsen" and "free late-night ramen" references (Dormy Inn specific amenities)
c.execute("""
    UPDATE activity SET title = REPLACE(title, 'Rooftop onsen bath', 'Evening walk / explore neighborhood')
    WHERE title LIKE '%Rooftop onsen%'
""")
if c.rowcount:
    log("Replaced Dormy Inn 'Rooftop onsen' activity")

c.execute("""
    UPDATE activity SET description = REPLACE(description, 'at Sotetsu Fresa Inn — soak away the long journey', 'explore the Shinjuku neighborhood')
    WHERE description LIKE '%soak away%'
""")
if c.rowcount:
    log("Updated onsen description")

c.execute("""
    UPDATE activity SET title = REPLACE(title, 'Free late-night ramen', 'Late-night ramen')
    WHERE title LIKE '%Free late-night ramen%'
""")
if c.rowcount:
    log(f"Updated 'Free late-night ramen' references (no longer free at Sotetsu Fresa)")

c.execute("""
    UPDATE activity SET description = REPLACE(description, 'at Sotetsu Fresa Inn (~9:30 PM)', 'at a nearby ramen shop')
    WHERE description LIKE '%Sotetsu Fresa Inn (~9:30 PM)%'
""")
if c.rowcount:
    log("Updated late-night ramen description")

c.execute("""
    UPDATE activity SET title = REPLACE(title, 'Last free late-night ramen', 'Last late-night ramen')
    WHERE title LIKE '%Last free late-night ramen%'
""")
if c.rowcount:
    log("Updated 'Last free late-night ramen'")

c.execute("""
    UPDATE activity SET description = REPLACE(description, 'at Sotetsu Fresa Inn 😢', 'one more before leaving Tokyo')
    WHERE description LIKE '%Sotetsu Fresa Inn 😢%'
""")

# Fix takkyubin reference
c.execute("""
    UPDATE activity SET title = REPLACE(title,
        'Check out of Sotetsu Fresa Inn (bags already sent to Kyoto via takkyubin — travel with daypacks!)',
        'Check out of Sotetsu Fresa Inn')
    WHERE title LIKE '%takkyubin%'
""")
if c.rowcount:
    log("Simplified checkout activity text")

# --- 8. Fix Day 13 title (Kyoto → Osaka, not Tokyo) ---
print("\n8. Fixing day titles")
c.execute("""
    UPDATE day SET title = 'KYOTO → OSAKA'
    WHERE day_number = 13 AND title LIKE '%OSAKA%'
""")
if c.rowcount:
    log("Day 13 title already correct")
else:
    c.execute("UPDATE day SET title = 'KYOTO → OSAKA' WHERE day_number = 13")
    log("Updated Day 13 title → KYOTO → OSAKA")

# Fix "machiya / Tsukiya-Mikazuki" checkout reference on Day 13
c.execute("""
    UPDATE activity SET title = 'Check out of Kyotofish Miyagawa'
    WHERE title LIKE '%Check out of machiya%'
""")
if c.rowcount:
    log("Fixed Day 13 checkout reference → Kyotofish Miyagawa")

# --- 9. Add Kyoto → Osaka transport route if missing ---
print("\n9. Checking transport routes")
c.execute("SELECT id FROM transport_route WHERE route_from = 'Kyoto' AND route_to = 'Osaka'")
if not c.fetchone():
    c.execute("SELECT MAX(sort_order) FROM transport_route")
    max_sort = c.fetchone()[0] or 0
    c.execute("""
        INSERT INTO transport_route
            (route_from, route_to, transport_type, duration, jr_pass_covered, sort_order)
        VALUES ('Kyoto', 'Osaka', 'Shinkansen', '15 min', 1, ?)
    """, (max_sort + 1,))
    log("Added Kyoto → Osaka transport route")
else:
    log("Kyoto → Osaka route already exists")

# Check for Kyoto → Kyoto malformed route
c.execute("SELECT id, route_from, route_to FROM transport_route WHERE route_from = route_to")
dupes = c.fetchall()
if dupes:
    for d in dupes:
        log(f"WARNING: Found self-route id={d[0]}: {d[1]} → {d[2]}")
        c.execute("DELETE FROM transport_route WHERE id = ?", (d[0],))
        log(f"Deleted malformed route id={d[0]}")
else:
    log("No malformed self-routes found")

conn.commit()
conn.close()

print("\n=== Done! Run 'python app.py' and visit /export to verify. ===\n")
