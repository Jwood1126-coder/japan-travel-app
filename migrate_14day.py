"""One-time migration script: restructure trip from 16 days to 14 days.
Removes Minneapolis, updates flights to confirmed bookings, removes Tokyo Final Night.
Run against seed DB, then add as live migration in app.py."""

import sqlite3
import sys
import os

def migrate(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Idempotent check: if Day 1 is already CLE travel day, skip
    c.execute("SELECT title FROM day WHERE day_number=1")
    row = c.fetchone()
    if row and 'CLEVELAND' in row[0] and 'TOKYO' in row[0] and 'TRAVEL' in row[0]:
        print("Migration already applied.")
        conn.close()
        return

    print("Migrating trip to 14 days...")

    # === 1. DELETE Day 1 (Minneapolis) activities and day ===
    c.execute("SELECT id FROM day WHERE day_number=1")
    day1 = c.fetchone()
    if day1:
        c.execute("DELETE FROM activity WHERE day_id=?", (day1[0],))
        c.execute("DELETE FROM day WHERE id=?", (day1[0],))

    # === 2. REPURPOSE Day 2 as new Day 1 (CLE→DTW→HND travel) ===
    c.execute("SELECT id FROM day WHERE day_number=2")
    day2 = c.fetchone()
    if day2:
        day2_id = day2[0]
        # Delete old Day 2 activities
        c.execute("DELETE FROM activity WHERE day_id=?", (day2_id,))
        # Update day metadata
        c.execute("""UPDATE day SET day_number=1, date='2026-04-05',
                     title='TRAVEL DAY -- CLEVELAND -> TOKYO'
                     WHERE id=?""", (day2_id,))
        # Insert new travel activities
        activities = [
            ('Depart CLE 10:30 AM -- Delta DL5392 to Detroit', 'morning', 1,
             'Endeavor Air regional jet. ~56 min flight. Confirmation: HBPF75'),
            ('Arrive DTW 11:26 AM -- layover', 'morning', 2,
             '2h 39min layover at Detroit Metropolitan. Grab lunch.'),
            ('Depart DTW 2:05 PM -- Delta DL275 to Tokyo Haneda', 'afternoon', 3,
             'Boeing 767-400ER. ~13h 10min flight. Main Basic (E class). Seats assigned at gate.'),
        ]
        for title, slot, order, desc in activities:
            c.execute("""INSERT INTO activity (day_id, title, time_slot, sort_order, description,
                         is_optional, is_substitute, jr_pass_covered)
                         VALUES (?, ?, ?, ?, ?, 0, 0, 0)""",
                      (day2_id, title, slot, order, desc))

    # === 3. Shift Days 3-14 down by 1 (become Days 2-13) ===
    # Must do in order to avoid unique constraint conflicts
    for old_num in range(3, 15):
        new_num = old_num - 1
        c.execute("UPDATE day SET day_number=? WHERE day_number=?", (new_num, old_num))

    # === 4. REPURPOSE Day 15 (Osaka→Tokyo) as Day 14 (Departure from Osaka) ===
    c.execute("SELECT id FROM day WHERE day_number=15")
    day15 = c.fetchone()
    if day15:
        day15_id = day15[0]
        # Delete old activities
        c.execute("DELETE FROM activity WHERE day_id=?", (day15_id,))
        # Update day
        c.execute("""UPDATE day SET day_number=14, date='2026-04-18',
                     title='DEPARTURE DAY -- OSAKA -> HOME'
                     WHERE id=?""", (day15_id,))
        # Insert departure activities
        dep_activities = [
            ('Early checkout from Osaka hotel', 'morning', 1,
             'Pack up. Check out by 8 AM for the journey home.'),
            ('Shinkansen Osaka -> Shinagawa (~2h 30min)', 'morning', 2,
             'Hikari shinkansen. JR Pass covered. Last ekiben lunch on the train!'),
            ('Transfer to Haneda Airport', 'afternoon', 3,
             'Keikyu Line from Shinagawa to Haneda Terminal 3 (~15 min, ~500 yen).'),
            ('Haneda Airport -- last shopping & check-in', 'afternoon', 4,
             'Arrive by 1:30 PM for 3:50 PM departure. Tax-free omiyage shops in terminal.'),
            ('United UA876 HND 3:50 PM -> SFO 9:35 AM', 'afternoon', 5,
             'Boeing 777-200. Seats: Jacob 52B, Jessica 52A (window pair, no third seat). Confirmation: I91ZHJ'),
            ('SFO layover (4h 45min)', 'evening', 6,
             'Arrive 9:35 AM same day (cross dateline). Long layover -- grab food, stretch legs.'),
            ('United UA1470 SFO 2:20 PM -> CLE 10:13 PM', 'evening', 7,
             'Seats: Jacob 37C, Jessica 37B. Confirmation: I91ZHJ. Welcome home!'),
        ]
        for title, slot, order, desc in dep_activities:
            c.execute("""INSERT INTO activity (day_id, title, time_slot, sort_order, description,
                         is_optional, is_substitute, jr_pass_covered)
                         VALUES (?, ?, ?, ?, ?, 0, 0, ?)""",
                      (day15_id, title, slot, order, desc,
                       1 if 'Shinkansen' in title else 0))

    # === 5. DELETE Day 16 (old departure day) ===
    c.execute("SELECT id FROM day WHERE day_number=16")
    day16 = c.fetchone()
    if day16:
        c.execute("DELETE FROM activity WHERE day_id=?", (day16[0],))
        c.execute("DELETE FROM day WHERE id=?", (day16[0],))

    # === 6. UPDATE FLIGHTS ===
    # Delete all existing flights
    c.execute("DELETE FROM flight")

    # Outbound: Delta CLE→DTW→HND (confirmed, HBPF75)
    c.execute("""INSERT INTO flight (direction, leg_number, flight_number, airline,
                 route_from, route_to, depart_date, depart_time, arrive_date, arrive_time,
                 duration, aircraft, cost_type, cost_amount, booking_status, confirmation_number, notes)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
              ('outbound', 1, 'DL5392', 'Delta (Endeavor Air)',
               'CLE', 'DTW', '2026-04-05', '10:30 AM', '2026-04-05', '11:26 AM',
               '56 min', 'CRJ-900', 'cash', '$775.00/person',
               'booked', 'HBPF75', 'Main Basic (E class). Seats assigned at gate. Operated by Endeavor Air.'))

    c.execute("""INSERT INTO flight (direction, leg_number, flight_number, airline,
                 route_from, route_to, depart_date, depart_time, arrive_date, arrive_time,
                 duration, aircraft, cost_type, cost_amount, booking_status, confirmation_number, notes)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
              ('outbound', 2, 'DL275', 'Delta',
               'DTW', 'HND', '2026-04-05', '2:05 PM', '2026-04-06', '4:15 PM',
               '13h 10min', 'Boeing 767-400ER', 'cash', '$775.00/person',
               'booked', 'HBPF75', 'Main Basic (E class). Seats assigned at gate.'))

    # Return: United HND→SFO→CLE (confirmed, I91ZHJ, miles)
    c.execute("""INSERT INTO flight (direction, leg_number, flight_number, airline,
                 route_from, route_to, depart_date, depart_time, arrive_date, arrive_time,
                 duration, aircraft, cost_type, cost_amount, booking_status, confirmation_number, notes)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
              ('return', 1, 'UA876', 'United',
               'HND', 'SFO', '2026-04-18', '3:50 PM', '2026-04-18', '9:35 AM',
               '9h 45min', 'Boeing 777-200', 'miles', '61,800 miles + $49.03/person',
               'booked', 'I91ZHJ', 'Jessica: seat 52A / Jacob: seat 52B (window pair, 2-seat section)'))

    c.execute("""INSERT INTO flight (direction, leg_number, flight_number, airline,
                 route_from, route_to, depart_date, depart_time, arrive_date, arrive_time,
                 duration, aircraft, cost_type, cost_amount, booking_status, confirmation_number, notes)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
              ('return', 2, 'UA1470', 'United',
               'SFO', 'CLE', '2026-04-18', '2:20 PM', '2026-04-18', '10:13 PM',
               '4h 53min', None, 'miles', '61,800 miles + $49.03/person',
               'booked', 'I91ZHJ', 'Jessica: seat 37B / Jacob: seat 37C'))

    # === 7. REMOVE Minneapolis location, accommodation, checklist items ===
    c.execute("SELECT id FROM accommodation_location WHERE location_name='Minneapolis'")
    mpls_accom = c.fetchone()
    if mpls_accom:
        c.execute("DELETE FROM accommodation_option WHERE location_id=?", (mpls_accom[0],))
        # Delete checklist options linked to checklist items linked to this accom
        c.execute("SELECT id FROM checklist_item WHERE accommodation_location_id=?", (mpls_accom[0],))
        for ci in c.fetchall():
            c.execute("DELETE FROM checklist_option WHERE checklist_item_id=?", (ci[0],))
            c.execute("DELETE FROM checklist_item WHERE id=?", (ci[0],))
        c.execute("DELETE FROM accommodation_location WHERE id=?", (mpls_accom[0],))

    # Delete Minneapolis-related checklist items (by title)
    c.execute("SELECT id FROM checklist_item WHERE title LIKE '%Minneapolis%' OR title LIKE '%MSP%'")
    for ci in c.fetchall():
        c.execute("DELETE FROM checklist_option WHERE checklist_item_id=?", (ci[0],))
        c.execute("DELETE FROM checklist_item WHERE id=?", (ci[0],))

    # Update outbound flight checklist item
    c.execute("""UPDATE checklist_item SET title='Book Delta outbound CLE -> DTW -> HND',
                 is_completed=1, status='completed'
                 WHERE title LIKE '%Delta outbound%'""")

    # Update return flight checklist item
    c.execute("""UPDATE checklist_item SET title='Book United return HND -> SFO -> CLE',
                 is_completed=1, status='completed'
                 WHERE title LIKE '%United%return%' OR title LIKE '%United award return%'""")

    # Delete Minneapolis location
    c.execute("DELETE FROM location WHERE name='Minneapolis'")

    # === 8. REMOVE Tokyo Final Night accommodation ===
    c.execute("SELECT id FROM accommodation_location WHERE location_name='Tokyo Final Night'")
    tfn_accom = c.fetchone()
    if tfn_accom:
        c.execute("DELETE FROM accommodation_option WHERE location_id=?", (tfn_accom[0],))
        # Unlink checklist items
        c.execute("""UPDATE checklist_item SET accommodation_location_id=NULL
                     WHERE accommodation_location_id=?""", (tfn_accom[0],))
        c.execute("DELETE FROM accommodation_location WHERE id=?", (tfn_accom[0],))

    # Delete Tokyo Final Night checklist items
    c.execute("SELECT id FROM checklist_item WHERE title LIKE '%Tokyo final night%'")
    for ci in c.fetchall():
        c.execute("DELETE FROM checklist_option WHERE checklist_item_id=?", (ci[0],))
        c.execute("DELETE FROM checklist_item WHERE id=?", (ci[0],))

    # === 9. UPDATE Osaka accommodation checkout ===
    c.execute("""UPDATE accommodation_location SET check_out_date='2026-04-18'
                 WHERE location_name='Osaka' AND check_out_date='2026-04-18'""")
    # Already correct from previous migration

    # === 10. UPDATE Tokyo location dates ===
    c.execute("""UPDATE location SET departure_date='2026-04-18'
                 WHERE name='Tokyo'""")

    # === 11. UPDATE Osaka location dates ===
    c.execute("""UPDATE location SET departure_date='2026-04-18'
                 WHERE name='Osaka'""")

    # === 12. UPDATE trip dates and description ===
    c.execute("""UPDATE trip SET
                 start_date='2026-04-05',
                 end_date='2026-04-18',
                 notes='14-day cherry blossom trip. Cleveland -> Tokyo -> Alps -> Kyoto -> Osaka -> Home'
                 WHERE id=1""")

    conn.commit()
    conn.close()
    print("Migration complete: trip restructured to 14 days (Apr 5-18).")
    print("Flights updated with confirmed Delta outbound and United return bookings.")


if __name__ == '__main__':
    db_path = os.path.join(os.path.dirname(__file__), 'data', 'japan_trip.db')
    migrate(db_path)
