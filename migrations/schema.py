"""Schema migrations — adds missing columns/tables to the database.

Idempotent and safe to run on every boot. Uses raw SQLite DDL
so it works even if models have changed.
"""

import os
import sqlite3


def run_schema_migrations(app):
    """Add new columns/tables if they don't exist."""
    db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
    if not os.path.exists(db_path):
        return
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # --- Create Document table (Phase 6: document-first architecture) ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS document (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            original_name TEXT,
            file_type TEXT,
            file_size INTEGER,
            doc_type TEXT NOT NULL,
            extracted_data TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT
        )
    """)

    # --- Column additions (idempotent via try/except) ---
    migrations = [
        ('activity', 'address', 'TEXT'),
        ('accommodation_option', 'address', 'TEXT'),
        ('accommodation_option', 'is_eliminated', 'BOOLEAN DEFAULT 0'),
        ('location', 'address', 'TEXT'),
        ('flight', 'confirmation_number', 'TEXT'),
        ('chat_message', 'image_filename', 'TEXT'),
        ('checklist_item', 'url', 'TEXT'),
        ('location', 'guide_url', 'TEXT'),
        ('checklist_item', 'item_type', "TEXT DEFAULT 'task'"),
        ('checklist_item', 'status', "TEXT DEFAULT 'pending'"),
        ('checklist_item', 'accommodation_location_id', 'INTEGER'),
        ('activity', 'url', 'TEXT'),
        ('location', 'latitude', 'REAL'),
        ('location', 'longitude', 'REAL'),
        ('accommodation_option', 'booking_image', 'TEXT'),
        ('accommodation_option', 'maps_url', 'TEXT'),
        ('activity', 'maps_url', 'TEXT'),
        ('accommodation_option', 'check_in_info', 'TEXT'),
        ('accommodation_option', 'check_out_info', 'TEXT'),
        ('activity', 'is_eliminated', 'BOOLEAN DEFAULT 0'),
        ('chat_message', 'context_summary', 'TEXT'),
        ('activity', 'category', 'TEXT'),
        ('activity', 'why', 'TEXT'),
        ('activity', 'book_ahead', 'BOOLEAN DEFAULT 0'),
        ('activity', 'book_ahead_note', 'TEXT'),
        ('activity', 'getting_there', 'TEXT'),
        ('activity', 'is_confirmed', 'BOOLEAN DEFAULT 0'),
        ('accommodation_option', 'phone', 'TEXT'),
        # Phase 6: document-first FK columns
        ('accommodation_option', 'document_id', 'INTEGER REFERENCES document(id)'),
        ('flight', 'document_id', 'INTEGER REFERENCES document(id)'),
        # Transport route enrichment
        ('transport_route', 'maps_url', 'TEXT'),
        ('transport_route', 'url', 'TEXT'),
        # Checklist option location link
        ('checklist_option', 'maps_url', 'TEXT'),
    ]
    for table, column, col_type in migrations:
        try:
            cursor.execute(f'ALTER TABLE {table} ADD COLUMN {column} {col_type}')
        except sqlite3.OperationalError:
            pass  # Column already exists
    conn.commit()

    # --- One-shot data migrations (idempotent, safe to re-run) ---
    _migrate_transport_data(cursor, conn)

    conn.commit()
    conn.close()


def _migrate_transport_data(cursor, conn):
    """Split Haneda combined route into two cards + enrich all routes with maps_url.

    Idempotent: checks current state before each change.
    """
    # Check if route 13 still has the old combined transport_type
    cursor.execute("SELECT id, transport_type FROM transport_route WHERE id = 13")
    row = cursor.fetchone()
    if row and 'OR' in (row[1] or ''):
        # Still the old combined "Keikyu Line + subway OR Limousine Bus" — split it
        cursor.execute("""
            UPDATE transport_route SET
                transport_type = 'Keikyu Line + subway',
                train_name = 'Keikyu Airport Express → Toei Oedo Line',
                duration = '~75 min',
                cost_if_not_covered = '~¥800',
                notes = 'Keikyu Line to Shinagawa, transfer to Toei Oedo Line to Higashi-Shinjuku. Use IC card (Suica/Pasmo).',
                maps_url = 'https://www.google.com/maps/dir/Haneda+Airport+Terminal+3,+Tokyo/Higashi-Shinjuku+Station',
                url = 'https://www.keikyu.co.jp/en/',
                sort_order = 1
            WHERE id = 13
        """)

    # Insert Limousine Bus route if it doesn't exist yet
    cursor.execute("SELECT id FROM transport_route WHERE transport_type = 'Limousine Bus'")
    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO transport_route (route_from, route_to, transport_type, train_name,
                duration, jr_pass_covered, cost_if_not_covered, notes, day_id, sort_order, maps_url, url)
            VALUES (
                'Haneda Airport', 'Shinjuku', 'Limousine Bus', 'Airport Limousine Bus',
                '~60-85 min', 0, '~¥1,300',
                'Direct bus from Haneda to Shinjuku Bus Terminal. No transfers. Runs every 20-30 min. Then 10 min walk to hotel.',
                (SELECT id FROM day WHERE day_number = 2), 2,
                'https://www.google.com/maps/dir/Haneda+Airport+Terminal+3,+Tokyo/Shinjuku+Expressway+Bus+Terminal',
                'https://www.limousinebus.co.jp/en/'
            )
        """)

    # Enrich all routes with maps_url where missing
    _route_data = {
        1: ('https://www.google.com/maps/dir/Tokyo+Station/Odawara+Station', 'https://www.jreast.co.jp/multi/en/'),
        2: ('https://www.google.com/maps/dir/Tokyo+Station/Nagoya+Station', 'https://www.jreast.co.jp/multi/en/'),
        3: ('https://www.google.com/maps/dir/Nagoya+Station/Takayama+Station', 'https://touristpass.jp/en/'),
        4: ('https://www.google.com/maps/dir/Takayama+Nohi+Bus+Center/Shirakawa-go+Bus+Terminal', None),
        5: ('https://www.google.com/maps/dir/Shirakawa-go+Bus+Terminal/Kanazawa+Station', None),
        6: ('https://www.google.com/maps/dir/Kanazawa+Station/Tsuruga+Station', None),
        7: ('https://www.google.com/maps/dir/Tsuruga+Station/Kyoto+Station', None),
        8: ('https://www.google.com/maps/dir/Kyoto+Station/Hiroshima+Station', None),
        9: ('https://www.google.com/maps/dir/Miyajimaguchi+Station/Miyajima+Ferry+Terminal', 'https://www.jr-miyajimaferry.co.jp/en/'),
        10: ('https://www.google.com/maps/dir/Kyoto+Station/Tokyo+Station', None),
        12: ('https://www.google.com/maps/dir/Kyoto+Station/Shin-Osaka+Station', None),
    }
    for route_id, (maps, url) in _route_data.items():
        cursor.execute("SELECT maps_url FROM transport_route WHERE id = ?", (route_id,))
        row = cursor.fetchone()
        if row and not row[0]:
            if url:
                cursor.execute("UPDATE transport_route SET maps_url = ?, url = ? WHERE id = ?",
                               (maps, url, route_id))
            else:
                cursor.execute("UPDATE transport_route SET maps_url = ? WHERE id = ?",
                               (maps, route_id))
