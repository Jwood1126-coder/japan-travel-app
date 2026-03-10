# Archive of migration functions 32-39 (from original app.py lines 4228-5582)
def _migrate_transport_hardening_v1(app):
    """Comprehensive transport hardening: add missing routes, fix route assignments,
    fix activity titles, add getting_there/URLs/addresses. See docs/transport-audit.md."""
    from models import Activity, Day, Trip, TransportRoute

    trip = Trip.query.first()
    if trip and trip.notes and '__transport_hardening_v1' in (trip.notes or ''):
        return

    print("Running migration: transport hardening v1...")
    changed = False

    # ---- HELPERS ----
    def find_day(day_number):
        return Day.query.filter_by(day_number=day_number).first()

    def find_activity(title_pattern, day_number=None):
        q = Activity.query.filter(Activity.title.ilike(title_pattern))
        if day_number:
            day = find_day(day_number)
            if day:
                q = q.filter_by(day_id=day.id)
        return q.first()

    def find_route(from_pattern, to_pattern, day_number=None):
        q = TransportRoute.query.filter(
            TransportRoute.route_from.ilike(from_pattern),
            TransportRoute.route_to.ilike(to_pattern))
        if day_number:
            day = find_day(day_number)
            if day:
                q = q.filter_by(day_id=day.id)
        return q.first()

    def add_route(day_number, route_from, route_to, transport_type, duration,
                  jr_pass, notes=None, sort_order=None):
        nonlocal changed
        day = find_day(day_number)
        if not day:
            return
        existing = find_route(f'%{route_from}%', f'%{route_to}%', day_number)
        if existing:
            return
        max_sort = db.session.query(db.func.max(TransportRoute.sort_order)).filter_by(
            day_id=day.id).scalar() or 0
        r = TransportRoute(
            route_from=route_from, route_to=route_to,
            transport_type=transport_type, duration=duration,
            jr_pass_covered=jr_pass, notes=notes,
            day_id=day.id, sort_order=sort_order or (max_sort + 1))
        db.session.add(r)
        changed = True
        print(f"  + Route: {route_from} → {route_to} (Day {day_number})")

    def set_activity_field(title_pattern, day_number, field, value, overwrite=False):
        nonlocal changed
        act = find_activity(title_pattern, day_number)
        if not act:
            return
        current = getattr(act, field, None)
        if current and not overwrite:
            return
        setattr(act, field, value)
        changed = True
        print(f"  ~ Activity '{act.title}' Day {day_number}: {field} set")

    def rename_activity(title_pattern, new_title, day_number=None):
        nonlocal changed
        act = find_activity(title_pattern, day_number)
        if not act:
            return
        if act.title == new_title:
            return
        old = act.title
        act.title = new_title
        changed = True
        print(f"  ~ Renamed: '{old}' → '{new_title}'")

    # ================================================================
    # PART 1: Add Missing Transport Routes (6 new routes)
    # ================================================================

    # Day 3 — Tokyo internal transit (sumo morning)
    add_route(3, 'Higashi-Shinjuku', 'Hamacho (Arashio Stable)',
              'Toei Oedo Line', '~20 min', False,
              'Leave by 6:15 AM for 6:45 AM sumo practice. Oedo Line from '
              'Higashi-Shinjuku Station direct to Hamacho. ¥220.')

    # Day 5 — First mile to station
    add_route(5, 'Higashi-Shinjuku', 'Tokyo Station',
              'Subway (Fukutoshin → Marunouchi)', '~20 min', False,
              'Transfer at Ikebukuro or take Oedo to Tochomae then walk to '
              'Shinjuku JR. Alternative: taxi ~¥2,000.')

    # Day 6 — Takayama internal (Hida Folk Village)
    add_route(6, 'Takayama Station', 'Hida Folk Village (Hida no Sato)',
              'Sarubobo Bus', '~10 min', False,
              'Runs every 20-30 min from platform #3 at Takayama Bus Center '
              '(next to JR station). ¥210. Or 30 min walk uphill.')

    # Day 12 — Hiroshima day trip (4 routes)
    add_route(12, 'Kyoto Station', 'Hiroshima Station',
              'Shinkansen Sakura/Hikari', '~1h 45min', True,
              'Board by 7:30 AM to maximize time. Nozomi is faster but NOT '
              'covered by JR Pass — take Sakura or Hikari.', sort_order=1)

    add_route(12, 'Hiroshima Station', 'Peace Park (Genbaku-Dome mae)',
              'Hiroshima streetcar (tram)', '~15 min', False,
              'Line 2 or 6 to Genbaku-Dome mae stop. ¥220 flat fare. IC card accepted.',
              sort_order=2)

    add_route(12, 'Hiroshima Station', 'Miyajimaguchi',
              'JR Sanyo Line', '~30 min', True,
              'Walk to JR Ferry terminal (2 min). Ferry ~10 min, JR Pass covered.',
              sort_order=3)

    add_route(12, 'Hiroshima Station', 'Kyoto Station',
              'Shinkansen Sakura/Hikari (return)', '~1h 45min', True,
              'DEADLINE: Last useful Shinkansen ~9 PM. Aim for 6:30-7 PM departure.',
              sort_order=4)

    # Day 14 — First mile to station
    add_route(14, 'Hotel Leben (Shinsaibashi)', 'Shin-Osaka Station',
              'Osaka Metro Midosuji Line', '~15 min', False,
              'Shinsaibashi → Shin-Osaka direct (7 stops). ¥280. Leave hotel by '
              '9:15 AM for recommended buffer.', sort_order=1)

    # ================================================================
    # PART 2: Fix Existing Route Assignments
    # ================================================================

    # Move Kanazawa→Kyoto route from Day 8 to Day 9
    route_kz_ky = find_route('%Kanazawa%', '%Kyoto%', 8)
    day9 = find_day(9)
    if route_kz_ky and day9:
        route_kz_ky.day_id = day9.id
        changed = True
        print("  ~ Moved Kanazawa→Kyoto route from Day 8 to Day 9")

    # Delete old generic Hiroshima routes from Day 11 (replaced by detailed Day 12 routes above)
    day11 = find_day(11)
    if day11:
        hiro_routes = TransportRoute.query.filter_by(day_id=day11.id).all()
        for r in hiro_routes:
            if 'hiroshima' in (r.route_from or '').lower() or \
               'hiroshima' in (r.route_to or '').lower() or \
               'miyajima' in (r.route_to or '').lower():
                db.session.delete(r)
                changed = True
                print(f"  - Deleted old route {r.route_from}→{r.route_to} from Day 11 (replaced by detailed Day 12 routes)")

    # Delete Osaka→Nara route from Day 13
    nara_route = find_route('%Osaka%', '%Nara%', 13)
    if nara_route:
        db.session.delete(nara_route)
        changed = True
        print("  - Deleted Osaka→Nara route from Day 13")

    # Fix Day 4 return JR flag and notes
    hakone_return = find_route('%Hakone%', '%Tokyo%', 4)
    if not hakone_return:
        hakone_return = find_route('%Hakone-Yumoto%', '%Tokyo%', 4)
    if hakone_return:
        hakone_return.notes = ('Hakone Tozan to Odawara (NOT JR, Hakone Free Pass), '
                               'then Shinkansen Odawara→Tokyo (JR Pass covered)')
        changed = True
        print("  ~ Updated Day 4 return route notes (JR clarification)")

    # ================================================================
    # PART 3: Fix Activity Titles (6 renames)
    # ================================================================

    rename_activity('%Nohi Bus%Shirakawa-go%Kyoto%',
                    'Nohi Bus: Shirakawa-go → Kanazawa')

    rename_activity('%Shinkansen Kyoto%Tokyo%',
                    'Shinkansen Shin-Osaka → Shinagawa', day_number=14)

    rename_activity('%Check out of Kyoto%',
                    'Early checkout from Hotel Leben Osaka', day_number=14)

    rename_activity('%Last Kyoto exploration%',
                    'Last Osaka morning — konbini breakfast & walk', day_number=14)

    rename_activity('%Kyoto Castle Park%',
                    'Kanazawa Castle Park', day_number=8)

    rename_activity('%Hokuriku Shinkansen%Kyoto%Tsuruga%',
                    'Hokuriku Shinkansen: Kanazawa → Tsuruga', day_number=9)

    # ================================================================
    # PART 4: Add Missing getting_there (14 activities)
    # ================================================================

    getting_there_updates = [
        ('%Explore Sanmachi Suji%', 6,
         'Walk from K\'s House — 10 min south along the river to the old town.'),
        ('%Takayama Jinya%', 6,
         '5 min walk south from Sanmachi Suji, across the Miyagawa River.'),
        ('%Miyagawa Morning Market%', 7,
         '5 min walk east from K\'s House along the river. Open 6 AM–noon.'),
        ('%Hida Folk Village%', 7,
         'Sarubobo Bus from Takayama Bus Center (~10 min, ¥210). Or 30 min walk uphill from station.'),
        ('%Kenrokuen%', 8,
         '15 min walk or bus from Kanazawa Station (east exit). Bus #6 to Kenrokuen-shita.'),
        ('%Higashi Chaya%', 8,
         '10 min walk east from Kenrokuen across Asanogawa bridge.'),
        ('%21st Century Museum%', 9,
         '15 min walk south from Kanazawa Station. Or bus from east exit, Hirosaka stop.'),
        ('%Hiroshima Peace%Park%', 12,
         'Streetcar from Hiroshima Station, Line 2 or 6 to Genbaku-Dome mae (15 min, ¥220).'),
        ('%A-Bomb Dome%', 12,
         'Across the river from Peace Park, 3 min walk.'),
        ('%JR train to Miyajimaguchi%', 12,
         'JR Sanyo Line from Hiroshima Station (~30 min). Walk to JR Ferry terminal (2 min).'),
        ('%Osaka Castle Park%', 13,
         'JR Loop Line from Osaka Station to Osakajo-Koen (2 stops, ~10 min). Walk through park to castle ~15 min.'),
        ('%Kuromon Market%', 13,
         'Subway from Tanimachi-Yonchome to Nipponbashi (~10 min). Or 20 min walk south from Osaka Castle.'),
        ('%Shinsekai%Tsutenkaku%', 13,
         'Walk south from Kuromon (~10 min) or subway to Ebisucho Station (1 stop).'),
        ('%TeamLab Planets%', 14,
         'Yurikamome Line from Shinbashi to Shin-Toyosu (~15 min). Or walk 10 min from Toyosu Station (Yurakucho Line).'),
    ]

    for pattern, day_num, gt_text in getting_there_updates:
        set_activity_field(pattern, day_num, 'getting_there', gt_text)

    # ================================================================
    # PART 5: Add Missing URLs, Addresses, Fix Broken URLs
    # ================================================================

    # --- URLs ---
    url_updates = [
        ('%Welcome Suica%', None, 'https://www.japan-guide.com/e/e2359_003.html'),
        ('%Nohi Bus%Shirakawa-go%Kanazawa%', None, 'https://www.nouhibus.co.jp/english/'),
        ('%Miyagawa Morning Market%', 7, 'https://www.japan-guide.com/e/e5907.html'),
        ('%Takayama Festival Floats%', 7, 'https://www.japan-guide.com/e/e5905.html'),
        ('%Wada House%', 8, 'https://www.japan-guide.com/e/e5951.html'),
        ('%Higashi Chaya%', 8, 'https://visitkanazawa.jp/en/attractions/detail_10212.html'),
        ('%D.T. Suzuki%', 9, 'https://www.japan-guide.com/e/e4211.html'),
        ('%Nagamachi Samurai%', 9, 'https://www.japan-guide.com/e/e4204.html'),
        ('%Gold leaf ice cream%Hakuichi%', 9, 'https://www.hakuichi.co.jp/'),
        ('%Itsukushima Torii%', 11, 'https://www.itsukushimajinja.jp/en/'),
        ('%A-Bomb Dome%', 12, 'https://hpmmuseum.jp/?lang=eng'),
        ('%Itsukushima Shrine%shopping%', 12, 'https://www.itsukushimajinja.jp/en/'),
        ('%Dotonbori Night Walk%', 13, 'https://www.japan-guide.com/e/e4001.html'),
        ('%Hozenji Yokocho%', 13, 'https://www.osaka-info.jp/en/spot/hozenji-yokocho/'),
    ]

    for pattern, day_num, url in url_updates:
        set_activity_field(pattern, day_num, 'url', url)

    # Fix broken URL on Nohi Bus Shirakawa→Kyoto (now renamed to →Kanazawa)
    nohi_act = find_activity('%Nohi Bus%Shirakawa-go%')
    if nohi_act and nohi_act.url and 'shirakawa-go.org' in nohi_act.url:
        nohi_act.url = 'https://www.nouhibus.co.jp/english/'
        changed = True
        print("  ~ Fixed broken URL on Nohi Bus activity")

    # --- Addresses ---
    address_updates = [
        ('%Tenzan Tohji-kyo%', 4, '208 Yumoto-chaya, Hakone-machi, Kanagawa'),
        ('%Cable Car%Owakudani%', 5, 'Gora, Hakone-machi, Ashigarashimo-gun, Kanagawa'),
        ('%Ropeway%', 5, 'Sounzan, Hakone-machi, Kanagawa'),
        ('%Lake Ashi Pirate Ship%', 5, 'Togendai Port, Hakone-machi, Kanagawa'),
        ('%Sake brewery%', 6, 'Sanmachi, Takayama-shi, Gifu'),
        ('%observation deck%', 8, 'Shiroyama Observation Deck, Ogimachi, Shirakawa-mura, Gifu'),
        ('%Higashi Chaya%', 8, 'Higashiyama, Kanazawa, Ishikawa'),
        ('%Kanazawa Castle Park%', 8, '1-1 Marunouchi, Kanazawa, Ishikawa'),
        ('%21st Century Museum%', 9, '1-2-1 Hirosaka, Kanazawa, Ishikawa'),
        ('%D.T. Suzuki%', 9, '3-4-20 Honda-machi, Kanazawa, Ishikawa'),
        ('%Nagamachi Samurai%', 9, 'Nagamachi, Kanazawa, Ishikawa'),
        ('%Gold leaf ice cream%Hakuichi%', 9, 'Higashiyama 1-15-4, Kanazawa, Ishikawa'),
        ('%Itsukushima Torii%', 11, 'Miyajima-cho, Hatsukaichi, Hiroshima'),
        ('%Itsukushima Shrine%', 12, '1-1 Miyajima-cho, Hatsukaichi, Hiroshima'),
        ('%Takoyaki crawl%', 13, 'Dotonbori, Chuo-ku, Osaka'),
        ('%TeamLab Planets%', 14, '6-1-16 Toyosu, Koto-ku, Tokyo'),
    ]

    for pattern, day_num, address in address_updates:
        set_activity_field(pattern, day_num, 'address', address)

    # --- Transport Route Notes (booking URLs) ---
    nohi_tk = find_route('%Takayama%', '%Shirakawa%')
    if nohi_tk and nohi_tk.notes and 'nouhibus' not in (nohi_tk.notes or ''):
        nohi_tk.notes = (nohi_tk.notes or '') + ' Book: https://www.nouhibus.co.jp/english/'
        changed = True

    nohi_sk = find_route('%Shirakawa%', '%Kanazawa%')
    if nohi_sk and nohi_sk.notes and 'nouhibus' not in (nohi_sk.notes or ''):
        nohi_sk.notes = (nohi_sk.notes or '') + ' Book: https://www.nouhibus.co.jp/english/'
        changed = True

    osaka_shinkansen = find_route('%Osaka%', '%Shinagawa%', 14)
    if osaka_shinkansen and 'Hikari' not in (osaka_shinkansen.notes or ''):
        osaka_shinkansen.notes = ('Use Hikari (not Nozomi). Reserve seat at JR ticket office. '
                                  + (osaka_shinkansen.notes or ''))
        changed = True

    # ================================================================
    # VALIDATION: Double-check transport consistency
    # ================================================================
    warnings = []

    # Check 1: Every day with non-optional activities should have routes or walkable note
    # Day 13 excluded: Osaka-internal (walking/subway), Kyoto→Osaka route is on Day 12
    days_needing_routes = {2, 3, 4, 5, 6, 8, 9, 12, 14}  # transit/multi-location days
    for dn in days_needing_routes:
        day = find_day(dn)
        if day:
            route_count = TransportRoute.query.filter_by(day_id=day.id).count()
            if route_count == 0:
                warnings.append(f"Day {dn} has no transport routes")

    # Check 2: No duplicate routes on same day (same from+to)
    all_days = Day.query.all()
    for day in all_days:
        routes = TransportRoute.query.filter_by(day_id=day.id).all()
        seen = set()
        for r in routes:
            key = (r.route_from.lower().strip(), r.route_to.lower().strip())
            if key in seen:
                warnings.append(f"Day {day.day_number}: duplicate route {r.route_from} → {r.route_to}")
            seen.add(key)

    # Check 3: Activity titles shouldn't reference wrong city for their day
    city_day_map = {
        'Tokyo': {2, 3, 4, 5}, 'Takayama': {6, 7}, 'Kanazawa': {8, 9},
        'Kyoto': {9, 10, 11, 12}, 'Osaka': {13, 14}, 'Hiroshima': {11, 12},
    }
    title_mismatches = [
        (8, '%Kyoto Castle%'),   # Day 8 is Kanazawa, not Kyoto
        (14, '%Kyoto%checkout%'),  # Day 14 is Osaka, not Kyoto
        (14, '%Kyoto%exploration%'),
    ]
    for dn, pattern in title_mismatches:
        bad = find_activity(pattern, dn)
        if bad:
            warnings.append(f"Day {dn}: activity '{bad.title}' references wrong city")

    # Check 4: Renamed activities should exist
    expected_titles = [
        (None, '%Nohi Bus%Kanazawa%'),
        (14, '%Shin-Osaka%Shinagawa%'),
        (8, '%Kanazawa Castle Park%'),
        (9, '%Kanazawa%Tsuruga%'),
    ]
    for dn, pattern in expected_titles:
        if not find_activity(pattern, dn):
            warnings.append(f"Expected activity '{pattern}' on Day {dn or 'any'} not found after rename")

    # Check 5: Key routes should be on correct days
    route_checks = [
        (9, '%Kanazawa%', '%Kyoto%', 'Kanazawa→Kyoto should be on Day 9'),
        (12, '%Kyoto%Station%', '%Hiroshima%Station%', 'Kyoto→Hiroshima should be on Day 12'),
        (12, '%Hiroshima%Station%', '%Kyoto%Station%', 'Hiroshima→Kyoto return should be on Day 12'),
        (3, '%Shinjuku%', '%Hamacho%', 'Sumo transit should be on Day 3'),
        (5, '%Shinjuku%', '%Tokyo Station%', 'First mile should be on Day 5'),
        (14, '%Leben%', '%Shin-Osaka%', 'Hotel→station should be on Day 14'),
    ]
    for dn, from_pat, to_pat, msg in route_checks:
        if not find_route(from_pat, to_pat, dn):
            warnings.append(f"MISSING: {msg}")

    if warnings:
        print(f"  ⚠ TRANSPORT VALIDATION WARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"    - {w}")
    else:
        print("  ✓ All transport validation checks passed")

    # ================================================================
    # Mark sentinel
    # ================================================================
    if trip:
        trip.notes = (trip.notes or '') + '\n__transport_hardening_v1'
        db.session.commit()
        print(f"Migration transport_hardening_v1 complete (changed={changed})")


def _migrate_sync_accom_checklist_v1(app):
    """Ensure every AccommodationLocation has a linked ChecklistItem,
    and sync booking statuses bidirectionally so documents page shows all reservations."""
    from models import (AccommodationLocation, AccommodationOption,
                        ChecklistItem, Trip, db)
    from datetime import datetime

    trip = Trip.query.first()
    if not trip:
        return
    if '__sync_accom_checklist_v1' in (trip.notes or ''):
        print("sync_accom_checklist_v1: already applied, skipping")
        return

    print("Running sync_accom_checklist_v1 migration...")
    changed = False

    # ================================================================
    # Part A: Create missing ChecklistItems for unlinked AccommodationLocations
    # ================================================================
    max_sort = db.session.query(db.func.max(ChecklistItem.sort_order)).scalar() or 0

    for loc in AccommodationLocation.query.order_by(
            AccommodationLocation.sort_order).all():
        existing = ChecklistItem.query.filter_by(
            accommodation_location_id=loc.id).first()
        if existing:
            continue

        # Build title like "Book Tokyo (3 nights, Apr 6-9)"
        date_range = ''
        if loc.check_in_date and loc.check_out_date:
            cin = loc.check_in_date.strftime('%b %-d')
            cout = loc.check_out_date.strftime('%-d')
            date_range = f', {cin}-{cout}'
        nights = loc.num_nights or 0
        night_str = f"{nights} night{'s' if nights != 1 else ''}"
        title = f"Book {loc.location_name} ({night_str}{date_range})"

        max_sort += 1
        item = ChecklistItem(
            title=title,
            item_type='decision',
            category='pre_departure_today',
            status='pending',
            accommodation_location_id=loc.id,
            sort_order=max_sort,
        )
        db.session.add(item)
        changed = True
        print(f"  + Created checklist item: {title}")

    if changed:
        db.session.flush()

    # ================================================================
    # Part B: Sync booking statuses bidirectionally
    # ================================================================

    # Pass 1: Checklist 'booked'/'completed' → AccommodationOption.booking_status
    for item in ChecklistItem.query.filter(
            ChecklistItem.accommodation_location_id.isnot(None),
            ChecklistItem.status.in_(['booked', 'completed'])).all():
        opt = AccommodationOption.query.filter_by(
            location_id=item.accommodation_location_id,
            is_selected=True).first()
        if opt and opt.booking_status not in ('booked', 'confirmed'):
            opt.booking_status = 'booked'
            changed = True
            print(f"  ~ Synced option '{opt.name}' booking_status → booked "
                  f"(from checklist '{item.title}')")

    # Pass 2: AccommodationOption booked/confirmed → ChecklistItem status
    for opt in AccommodationOption.query.filter(
            AccommodationOption.is_selected == True,
            AccommodationOption.booking_status.in_(['booked', 'confirmed'])).all():
        item = ChecklistItem.query.filter_by(
            accommodation_location_id=opt.location_id).first()
        if item and item.status not in ('booked', 'completed'):
            item.status = 'booked'
            item.is_completed = True
            item.completed_at = datetime.utcnow()
            changed = True
            print(f"  ~ Synced checklist '{item.title}' → booked "
                  f"(from option '{opt.name}')")

    # ================================================================
    # Mark sentinel
    # ================================================================
    trip.notes = (trip.notes or '') + '\n__sync_accom_checklist_v1'
    db.session.commit()
    print(f"Migration sync_accom_checklist_v1 complete (changed={changed})")


def _migrate_schedule_consistency_v1(app):
    """Fix all schedule audit findings. Each fix has its own idempotency check."""
    from models import (Activity, Day, Trip, AccommodationLocation, db)
    from datetime import date

    trip = Trip.query.first()
    if not trip:
        return
    sentinel = '__schedule_consistency_v1'
    if sentinel in (trip.notes or ''):
        print("schedule_consistency_v1: already applied, skipping")
        return

    print("Running schedule_consistency_v1 migration...")
    days = {d.day_number: d for d in Day.query.all()}

    # ================================================================
    # Fix 1: Day 14 — Eliminate impossible post-departure activities
    # Flight UA876 departs HND at 3:50 PM. No time for hotel check-in,
    # TeamLab, or dinner in Tokyo.
    # ================================================================
    day14 = days.get(14)
    if day14:
        impossible_titles = [
            'Check into Toyoko Inn Shinagawa',
            'TeamLab Planets',
            'Final dinner — make it special',
            'Final dinner',
        ]
        for a in Activity.query.filter_by(day_id=day14.id).all():
            if a.title in impossible_titles and not a.is_eliminated:
                a.is_eliminated = True
                print(f"  Fix1: Eliminated '{a.title}' on Day 14 (impossible with 3:50 PM flight)")

    # ================================================================
    # Fix 2: Day 5 — Eliminate misplaced Hakone Loop activities
    # Day 5 is "TOKYO → TAKAYAMA" transit day. The Hakone activities
    # belong on Day 4 (which already has its own Hakone Loop).
    # ================================================================
    day5 = days.get(5)
    if day5:
        hakone_titles = [
            'Shinkansen Tokyo → Odawara',
            'Shinkansen Tokyo \u2192 Odawara',
            'Buy Hakone Free Pass at Odawara Station',
            'Hakone Loop: Switchback Train to Gora',
            'Hakone Loop: Cable Car to Owakudani',
            'Hakone Loop: Ropeway over mountains',
            'Hakone Loop: Lake Ashi Pirate Ship',
            'Hakone Open-Air Museum',
            'Day-use onsen: Tenzan Tohji-kyo',
            'Shinkansen Odawara → Tokyo',
            'Shinkansen Odawara \u2192 Tokyo',
            'Last night in Shinjuku',
        ]
        for a in Activity.query.filter_by(day_id=day5.id).all():
            if a.title in hakone_titles and not a.is_eliminated:
                a.is_eliminated = True
                print(f"  Fix2: Eliminated '{a.title}' on Day 5 (belongs on Day 4)")

    # ================================================================
    # Fix 3: Day 6 → Day 5 — Move transit activities to the actual
    # transit day. Day 5 = "TOKYO → TAKAYAMA", Day 6 = "FULL DAY TAKAYAMA"
    # ================================================================
    day6 = days.get(6)
    if day5 and day6:
        transit_titles_to_move = [
            'Check out of Sotetsu Fresa Inn',
            'Shinkansen Tokyo → Nagoya',
            'Shinkansen Tokyo \u2192 Nagoya',
            'JR Hida Limited Express: Nagoya → Takayama',
            'JR Hida Limited Express: Nagoya \u2192 Takayama',
            'Check into ryokan',
            'Check into TAKANOYU',  # production variant
        ]
        max_sort_d5 = max(
            [a.sort_order for a in Activity.query.filter_by(day_id=day5.id).all()] or [0]
        )
        for a in Activity.query.filter_by(day_id=day6.id).all():
            if a.title in transit_titles_to_move:
                a.day_id = day5.id
                max_sort_d5 += 1
                a.sort_order = max_sort_d5
                # Fix time slots for transit day
                if 'Check out' in a.title or 'Shinkansen' in a.title:
                    a.time_slot = 'morning'
                elif 'JR Hida' in a.title:
                    a.time_slot = 'morning'
                elif 'Check into' in a.title:
                    a.time_slot = 'afternoon'
                print(f"  Fix3: Moved '{a.title}' from Day 6 → Day 5")

    # ================================================================
    # Fix 4: Day 3 — Eliminate stale arrival activities
    # These are duplicates of Day 2 arrival tasks, or reference the
    # wrong hotel (Dormy Inn instead of Sotetsu Fresa).
    # ================================================================
    day3 = days.get(3)
    if day3:
        stale_titles = [
            'Pick up Welcome Suica IC card',
            'Activate eSIM or pick up pocket WiFi',
            'Train to Higashi-Shinjuku',
            'Check into Dormy Inn Asakusa',
        ]
        for a in Activity.query.filter_by(day_id=day3.id).all():
            if a.title in stale_titles and not a.is_eliminated:
                a.is_eliminated = True
                print(f"  Fix4: Eliminated '{a.title}' on Day 3 (stale/duplicate)")

    # ================================================================
    # Fix 5: Fix accommodation dates
    # Correct chain: Tokyo Apr 6-9, Takayama Apr 9-12,
    # Kanazawa Apr 12-13, Kyoto Apr 13-16, Osaka Apr 16-18
    # ================================================================

    # 5a: K's House / Takayama Budget → Apr 10-12 (2 nights)
    for loc in AccommodationLocation.query.filter(
            AccommodationLocation.location_name.contains('Budget')).all():
        if loc.check_out_date != date(2026, 4, 12):
            loc.check_out_date = date(2026, 4, 12)
            loc.num_nights = 2
            print(f"  Fix5a: Updated '{loc.location_name}' checkout to Apr 12 (2 nights)")

    # 5b: Kanazawa → Apr 12-13 (1 night)
    for loc in AccommodationLocation.query.filter(
            AccommodationLocation.location_name.contains('Kanazawa')).all():
        if loc.check_in_date != date(2026, 4, 12):
            loc.check_in_date = date(2026, 4, 12)
            loc.check_out_date = date(2026, 4, 13)
            loc.num_nights = 1
            print(f"  Fix5b: Updated '{loc.location_name}' to Apr 12-13 (1 night)")

    # 5c: Kyoto → Apr 13-16 (3 nights)
    for loc in AccommodationLocation.query.filter(
            AccommodationLocation.location_name.contains('Kyoto')).all():
        if loc.check_in_date != date(2026, 4, 13):
            loc.check_in_date = date(2026, 4, 13)
            loc.check_out_date = date(2026, 4, 16)
            loc.num_nights = 3
            if '4 nights' in loc.location_name:
                loc.location_name = loc.location_name.replace('4 nights', '3 nights')
            print(f"  Fix5c: Updated '{loc.location_name}' to Apr 13-16 (3 nights)")

    # ================================================================
    # Fix 6: Day 7 title — It's a full Takayama day, not a transit day
    # Transit to Shirakawa-go/Kanazawa happens on Day 8
    # ================================================================
    day7 = days.get(7)
    if day7 and 'SHIRAKAWA' in (day7.title or '').upper():
        day7.title = 'FULL DAY TAKAYAMA — Old Town & Markets'
        print(f"  Fix6: Updated Day 7 title to '{day7.title}'")

    # ================================================================
    # Fix 7: Day 11 — Fix time slots (all marked morning)
    # Hiroshima Peace Park is morning, okonomiyaki is lunch,
    # Miyajima activities are afternoon
    # ================================================================
    day11 = days.get(11)
    if day11:
        afternoon_keywords = [
            'Itsukushima', 'high tide', 'low tide', 'deer roam',
            'momiji manju', 'shopping street', 'Itsukushima Shrine',
        ]
        lunch_keywords = ['okonomiyaki', 'Okonomimura']
        for a in Activity.query.filter_by(day_id=day11.id).all():
            if a.time_slot == 'morning':
                if any(kw in (a.title or '') for kw in afternoon_keywords):
                    a.time_slot = 'afternoon'
                    print(f"  Fix7: Changed '{a.title[:40]}' to afternoon")
                elif any(kw in (a.title or '') for kw in lunch_keywords):
                    a.time_slot = 'afternoon'
                    print(f"  Fix7: Changed '{a.title[:40]}' to afternoon (lunch)")

    # ================================================================
    # Fix 8: Day 12 — Add luggage logistics note
    # Checking out of Kyoto then doing Hiroshima day trip requires
    # coin locker or luggage forwarding
    # ================================================================
    day12 = days.get(12)
    if day12:
        existing = Activity.query.filter_by(day_id=day12.id).filter(
            Activity.title.contains('luggage') | Activity.title.contains('locker')
            | Activity.title.contains('Luggage') | Activity.title.contains('Locker')
        ).first()
        if not existing:
            max_sort = max(
                [a.sort_order for a in Activity.query.filter_by(day_id=day12.id).all()] or [0]
            )
            luggage_note = Activity(
                day_id=day12.id,
                title='Store luggage in Kyoto Station coin lockers before Hiroshima',
                time_slot='morning',
                sort_order=1,  # First thing in the morning
                is_optional=False,
                getting_there='Kyoto Station has large coin lockers (¥700-1000/day) near the Shinkansen gates. '
                              'Store bags before boarding Shinkansen to Hiroshima. Pick up on return.',
            )
            db.session.add(luggage_note)
            print("  Fix8: Added luggage logistics note to Day 12")

    # ================================================================
    # Mark sentinel
    # ================================================================
    trip.notes = (trip.notes or '') + '\n' + sentinel
    db.session.commit()
    print("Migration schedule_consistency_v1 complete")


def _validate_schedule(app):
    """Post-migration schedule validation. Prints warnings for conflicts.
    Runs on every boot to catch data issues early."""
    from models import (Activity, Day, Trip, AccommodationLocation,
                        Flight, TransportRoute, Location, db)
    from datetime import date, timedelta

    trip = Trip.query.first()
    if not trip:
        return

    warnings = []
    days = Day.query.order_by(Day.day_number).all()
    day_map = {d.day_number: d for d in days}

    # --- Check 1: Accommodation date chain gaps/overlaps ---
    # Skip locations where ALL options are eliminated (e.g. Kanazawa, merged Budget)
    all_locs = AccommodationLocation.query.order_by(
        AccommodationLocation.check_in_date).all()
    locs = [l for l in all_locs
            if l.options and not all(o.is_eliminated for o in l.options)]
    for i in range(len(locs) - 1):
        curr = locs[i]
        nxt = locs[i + 1]
        if curr.check_out_date and nxt.check_in_date:
            gap = (nxt.check_in_date - curr.check_out_date).days
            if gap > 0:
                warnings.append(
                    f"ACCOM GAP: {gap} night(s) gap between "
                    f"{curr.location_name} checkout ({curr.check_out_date}) and "
                    f"{nxt.location_name} checkin ({nxt.check_in_date})")
            elif gap < 0:
                warnings.append(
                    f"ACCOM OVERLAP: {abs(gap)} night(s) overlap between "
                    f"{curr.location_name} and {nxt.location_name}")

    # --- Check 2: Accommodation num_nights consistency ---
    for loc in locs:
        if loc.check_in_date and loc.check_out_date:
            expected = (loc.check_out_date - loc.check_in_date).days
            if loc.num_nights and loc.num_nights != expected:
                warnings.append(
                    f"ACCOM NIGHTS: {loc.location_name} says {loc.num_nights} nights "
                    f"but dates span {expected} nights "
                    f"({loc.check_in_date} → {loc.check_out_date})")

    # --- Check 3: Departure day activities after flight ---
    flights = Flight.query.all()
    for f in flights:
        if f.direction == 'return' and f.depart_date:
            dep_day = next(
                (d for d in days if d.date == f.depart_date), None)
            if dep_day:
                late_activities = Activity.query.filter_by(
                    day_id=dep_day.id, is_eliminated=False
                ).filter(
                    Activity.time_slot.in_(['evening', 'night'])
                ).all()
                for a in late_activities:
                    if not a.is_substitute:
                        warnings.append(
                            f"DEPARTURE CONFLICT: '{a.title}' ({a.time_slot}) on "
                            f"departure day {dep_day.day_number} — flight {f.flight_number} "
                            f"departs at {f.depart_time}")

    # --- Check 4: Overpacked days (>10 non-eliminated activities) ---
    for d in days:
        active = Activity.query.filter_by(
            day_id=d.id, is_eliminated=False, is_substitute=False
        ).count()
        if active > 10:
            warnings.append(
                f"OVERPACKED: Day {d.day_number} ({d.title}) has {active} active activities")

    # --- Check 5: Day has city location but activities reference wrong city ---
    # (lightweight check: look for activities mentioning specific city keywords
    # on days assigned to different locations)
    location_map = {}
    locations = Location.query.all() if hasattr(app, 'extensions') else []
    try:
        locations = Location.query.all()
        for loc in locations:
            for d in Day.query.filter_by(location_id=loc.id).all():
                location_map[d.day_number] = loc.name
    except Exception:
        pass

    if warnings:
        print(f"\n{'='*60}")
        print(f"SCHEDULE VALIDATION: {len(warnings)} warning(s)")
        print(f"{'='*60}")
        for w in warnings:
            print(f"  ⚠ {w}")
        print(f"{'='*60}\n")
    else:
        print("Schedule validation: all checks passed ✓")


def _migrate_confirmed_bookings_v1(app):
    """Authoritative migration based on confirmed PDF booking documents.
    Source of truth: extracted data from uploaded booking confirmations.

    Confirmed accommodation chain:
    1. Sotetsu Fresa Inn Higashi-Shinjuku — Apr 6-9 (3n) — Agoda 976558450
    2. Takayama — Apr 9-12 (3n) — NOT YET BOOKED
    3. Tsukiya-Mikazuki (Airbnb machiya) — Apr 12-14 (2n) — HMXTP9H2Z9
    4. Kyotofish Miyagawa Geisha Ochaya (Airbnb) — Apr 14-16 (2n) — confirmed
    5. Hotel The Leben Osaka — Apr 16-18 (2n) — Agoda 976698966

    NO KANAZAWA OVERNIGHT.
    """
    from models import (Trip, AccommodationLocation, AccommodationOption,
                        Activity, Day, Location, db)
    from datetime import date

    with app.app_context():
        trip = Trip.query.first()
        if not trip:
            return
        sentinel = '__confirmed_bookings_v1'
        if trip.notes and sentinel in trip.notes:
            print("confirmed_bookings_v1: already applied, skipping")
            return

        print("Running migration: confirmed_bookings_v1 (from PDF booking data)...")

        # ============================================================
        # 1. TOKYO — Sotetsu Fresa Inn (LOC 1, OPT 11)
        # ============================================================
        tokyo_loc = AccommodationLocation.query.filter_by(location_name='Tokyo').first()
        if tokyo_loc:
            tokyo_loc.check_in_date = date(2026, 4, 6)
            tokyo_loc.check_out_date = date(2026, 4, 9)
            tokyo_loc.num_nights = 3

            fresa = AccommodationOption.query.filter(
                AccommodationOption.location_id == tokyo_loc.id,
                AccommodationOption.name.like('%Sotetsu Fresa%')
            ).first()
            if fresa:
                fresa.is_selected = True
                fresa.booking_status = 'confirmed'
                fresa.confirmation_number = '976558450'
                fresa.address = '7-27-9 Shinjuku, Shinjuku-ku, Tokyo 160-0022'
                fresa.check_in_info = 'after 3:00 PM'
                fresa.check_out_info = 'before 11:00 AM'
                fresa.phone = '+81-3-6892-2032'
                fresa.property_type = 'Hotel'
                # Deselect all other Tokyo options
                for opt in tokyo_loc.options:
                    if opt.id != fresa.id:
                        opt.is_selected = False

        # ============================================================
        # 2. TAKAYAMA — NOT YET BOOKED (LOC 2 + LOC 3)
        #    Ryokan: Apr 9-10 (1n), Budget: Apr 10-12 (2n) = 3n total
        # ============================================================
        tak_ryokan = AccommodationLocation.query.filter_by(
            location_name='Takayama Ryokan').first()
        if tak_ryokan:
            tak_ryokan.check_in_date = date(2026, 4, 9)
            tak_ryokan.check_out_date = date(2026, 4, 10)
            tak_ryokan.num_nights = 1

        tak_budget = AccommodationLocation.query.filter_by(
            location_name='Takayama Budget').first()
        if tak_budget:
            tak_budget.check_in_date = date(2026, 4, 10)
            tak_budget.check_out_date = date(2026, 4, 12)
            tak_budget.num_nights = 2

        # ============================================================
        # 3. KANAZAWA — ELIMINATE (NO OVERNIGHT STAY)
        # ============================================================
        kanazawa_loc = AccommodationLocation.query.filter_by(
            location_name='Kanazawa').first()
        if kanazawa_loc:
            for opt in kanazawa_loc.options:
                opt.is_eliminated = True
                opt.is_selected = False

        # ============================================================
        # 4. KYOTO — Split into two stays matching confirmed bookings
        #    LOC 5 → Kyoto Stay 1 (Tsukiya-Mikazuki, Apr 12-14)
        #    NEW LOC → Kyoto Stay 2 (Kyotofish, Apr 14-16)
        # ============================================================
        kyoto_loc = AccommodationLocation.query.filter(
            AccommodationLocation.location_name.like('%Kyoto%'),
            AccommodationLocation.location_name.notlike('%Stay 2%')
        ).first()

        if kyoto_loc:
            kyoto_loc.location_name = 'Kyoto Stay 1'
            kyoto_loc.check_in_date = date(2026, 4, 12)
            kyoto_loc.check_out_date = date(2026, 4, 14)
            kyoto_loc.num_nights = 2

            # Deselect all existing options
            for opt in kyoto_loc.options:
                opt.is_selected = False

            # Add Tsukiya-Mikazuki option
            tsukiya = AccommodationOption.query.filter(
                AccommodationOption.location_id == kyoto_loc.id,
                AccommodationOption.name.like('%Tsukiya%')
            ).first()
            if not tsukiya:
                tsukiya = AccommodationOption(
                    location_id=kyoto_loc.id,
                    name='Tsukiya-Mikazuki',
                    rank=1,
                    property_type='Machiya B&B',
                    price_low=138, price_high=138,
                    total_low=276, total_high=276,
                )
                db.session.add(tsukiya)
                db.session.flush()

            tsukiya.is_selected = True
            tsukiya.is_eliminated = False
            tsukiya.booking_status = 'confirmed'
            tsukiya.confirmation_number = 'HMXTP9H2Z9'
            tsukiya.address = '600-8302, Kyoto-fu, Shimogyo-ku, Kyoto-shi, 139 Ebisuchō'
            tsukiya.check_in_info = 'after 4:00 PM'
            tsukiya.check_out_info = 'by 11:00 AM'
            tsukiya.phone = '+81-75-353-7920'

        # Create Kyoto Stay 2 location
        kyoto2 = AccommodationLocation.query.filter_by(
            location_name='Kyoto Stay 2').first()
        if not kyoto2:
            kyoto2 = AccommodationLocation(
                location_name='Kyoto Stay 2',
                check_in_date=date(2026, 4, 14),
                check_out_date=date(2026, 4, 16),
                num_nights=2,
                sort_order=6,
            )
            db.session.add(kyoto2)
            db.session.flush()

        # Add Kyotofish option
        kyotofish = AccommodationOption.query.filter(
            AccommodationOption.location_id == kyoto2.id,
            AccommodationOption.name.like('%Kyotofish%')
        ).first()
        if not kyotofish:
            kyotofish = AccommodationOption(
                location_id=kyoto2.id,
                name='Kyotofish Miyagawa Geisha Ochaya',
                rank=1,
                property_type='Airbnb Townhouse',
            )
            db.session.add(kyotofish)
            db.session.flush()

        kyotofish.is_selected = True
        kyotofish.is_eliminated = False
        kyotofish.booking_status = 'confirmed'
        kyotofish.check_in_info = '4:00 PM'
        kyotofish.check_out_info = '10:00 AM'
        kyotofish.notes = 'Host: Karen. UPDATE GUEST COUNT TO 2 ADULTS (host flagged this).'

        # ============================================================
        # 5. OSAKA — Hotel The Leben (LOC 7)
        # ============================================================
        osaka_loc = AccommodationLocation.query.filter_by(
            location_name='Osaka').first()
        if osaka_loc:
            osaka_loc.check_in_date = date(2026, 4, 16)
            osaka_loc.check_out_date = date(2026, 4, 18)
            osaka_loc.num_nights = 2

            # Deselect all existing
            for opt in osaka_loc.options:
                opt.is_selected = False

            leben = AccommodationOption.query.filter(
                AccommodationOption.location_id == osaka_loc.id,
                AccommodationOption.name.like('%Leben%')
            ).first()
            if not leben:
                leben = AccommodationOption(
                    location_id=osaka_loc.id,
                    name='Hotel The Leben Osaka',
                    rank=1,
                    property_type='Hotel',
                    price_low=230, price_high=230,
                    total_low=460, total_high=460,
                )
                db.session.add(leben)
                db.session.flush()

            leben.is_selected = True
            leben.is_eliminated = False
            leben.booking_status = 'confirmed'
            leben.confirmation_number = '976698966'
            leben.address = '2-2-15 Minamisenba, Chuo-ku, Osaka 542-0081'
            leben.check_in_info = 'after 3:00 PM'
            leben.check_out_info = 'before 11:00 AM'
            leben.notes = 'Free cancellation before Apr 7, non-refundable after. $459.42 total.'

        # ============================================================
        # 6. ACTIVITY FIXES
        # ============================================================

        # --- Day 2: Eliminate Dormy Inn amenities (user is at Sotetsu Fresa) ---
        day2 = Day.query.filter_by(day_number=2).first()
        if day2:
            for title_frag in ['Rooftop onsen bath', 'Free late-night ramen']:
                act = Activity.query.filter(
                    Activity.day_id == day2.id,
                    Activity.title.like(f'%{title_frag}%'),
                    Activity.is_eliminated == False
                ).first()
                if act:
                    act.is_eliminated = True
                    print(f"  Eliminated Day 2: '{act.title}' (Dormy Inn amenity)")

        # --- Day 7: Fix location from Kanazawa to Takayama ---
        day7 = Day.query.filter_by(day_number=7).first()
        takayama_loc = Location.query.filter_by(name='Takayama').first()
        if day7 and takayama_loc:
            if day7.location_id != takayama_loc.id:
                day7.location_id = takayama_loc.id
                print(f"  Fixed Day 7 location: Kanazawa → Takayama")

        # --- Day 8: Transit day Takayama → Shirakawa-go → Kyoto ---
        day8 = Day.query.filter_by(day_number=8).first()
        if day8:
            day8.title = 'TAKAYAMA → SHIRAKAWA-GO → KYOTO'
            # Eliminate Kanazawa-specific activities
            kanazawa_activities = [
                'Check into Kaname Inn', 'Kenrokuen Garden',
                'Castle Park', 'Higashi Chaya',
                'Fresh seafood dinner at Omicho', 'Sai River',
            ]
            for frag in kanazawa_activities:
                act = Activity.query.filter(
                    Activity.day_id == day8.id,
                    Activity.title.like(f'%{frag}%'),
                    Activity.is_eliminated == False
                ).first()
                if act:
                    act.is_eliminated = True
                    print(f"  Eliminated Day 8: '{act.title}' (Kanazawa activity)")

            # Fix bus route title
            bus_to_kyoto = Activity.query.filter(
                Activity.day_id == day8.id,
                Activity.title.like('%Shirakawa-go%Kyoto%')
            ).first()
            if bus_to_kyoto:
                bus_to_kyoto.title = 'Nohi Bus: Shirakawa-go → Kanazawa'
                bus_to_kyoto.getting_there = 'Nohi Bus from Shirakawa-go to Kanazawa (~1h15m). Then Hokuriku Shinkansen/Thunderbird to Kyoto.'

            # Add check-in to Tsukiya-Mikazuki on Day 8 evening
            existing_checkin = Activity.query.filter(
                Activity.day_id == day8.id,
                Activity.title.like('%Tsukiya%')
            ).first()
            if not existing_checkin:
                checkin_act = Activity(
                    day_id=day8.id,
                    title='Check into Tsukiya-Mikazuki (Kyoto machiya)',
                    time_slot='evening',
                    sort_order=900,
                    getting_there='From Kyoto Station: Karasuma Line to Gojo Station (1 stop, 3 min). 5 min walk.',
                    is_optional=False,
                )
                db.session.add(checkin_act)
                print("  Added Day 8: Check into Tsukiya-Mikazuki")

            # Add train from Kanazawa to Kyoto
            existing_train = Activity.query.filter(
                Activity.day_id == day8.id,
                Activity.title.like('%Kanazawa%Kyoto%')
            ).first()
            if not existing_train:
                # Check for Hokuriku shinkansen
                existing_hoku = Activity.query.filter(
                    Activity.day_id == day8.id,
                    Activity.title.like('%Hokuriku%')
                ).first()
                if not existing_hoku:
                    train_act = Activity(
                        day_id=day8.id,
                        title='Hokuriku Shinkansen + Thunderbird: Kanazawa → Kyoto',
                        time_slot='afternoon',
                        sort_order=800,
                        jr_pass_covered=True,
                        getting_there='Hokuriku Shinkansen Kanazawa → Tsuruga, then Thunderbird Express Tsuruga → Kyoto. ~2h15m total.',
                    )
                    db.session.add(train_act)
                    print("  Added Day 8: Kanazawa → Kyoto train")

        # --- Day 9: Eliminate Kanazawa activities, make it a Kyoto day ---
        day9 = Day.query.filter_by(day_number=9).first()
        if day9:
            day9.title = 'KYOTO DAY 1 — Eastern Temples & Gion'
            kanazawa_day9 = [
                '21st Century Museum', 'D.T. Suzuki Museum',
                'Nagamachi Samurai', 'Gold leaf ice cream',
                'Last Omicho Market', 'Hokuriku Shinkansen',
                'Thunderbird Express',
            ]
            for frag in kanazawa_day9:
                act = Activity.query.filter(
                    Activity.day_id == day9.id,
                    Activity.title.like(f'%{frag}%'),
                    Activity.is_eliminated == False
                ).first()
                if act:
                    act.is_eliminated = True
                    print(f"  Eliminated Day 9: '{act.title}' (Kanazawa activity)")

            # Check-into Tsukiya should be Day 8, not Day 9 — move if on Day 9
            tsukiya_checkin_d9 = Activity.query.filter(
                Activity.day_id == day9.id,
                Activity.title.like('%Tsukiya%')
            ).first()
            if tsukiya_checkin_d9:
                tsukiya_checkin_d9.is_eliminated = True
                print("  Eliminated Day 9: Tsukiya check-in (moved to Day 8)")

            # Add Kyoto sightseeing activities for Day 9 if now mostly empty
            active_d9 = Activity.query.filter_by(
                day_id=day9.id, is_eliminated=False, is_substitute=False
            ).count()
            if active_d9 < 3:
                kyoto_d9_activities = [
                    ('Fushimi Inari Shrine — walk the thousand torii gates', 'morning', 100,
                     'JR Nara Line from Kyoto Station to Inari Station (5 min). Shrine is right at the station exit.'),
                    ('Kiyomizu-dera Temple', 'morning', 200,
                     'Bus #207 from Gojo to Kiyomizu-michi (15 min) then 10 min uphill walk.'),
                    ('Higashiyama historic walking streets', 'afternoon', 300,
                     'Walk downhill from Kiyomizu-dera through Ninenzaka and Sannenzaka lanes.'),
                    ('Gion district walk — spot geiko and maiko', 'afternoon', 400,
                     'Walk north from Higashiyama through Yasaka Shrine to Gion (~15 min).'),
                    ('Stroll along Kamo River', 'evening', 500,
                     'Walk west from Gion to the river (5 min). Beautiful lit-up bridges at night.'),
                    ('Pontocho Alley dinner', 'evening', 600,
                     'Narrow alley parallel to Kamo River between Shijo and Sanjo bridges.'),
                ]
                for title, slot, order, gt in kyoto_d9_activities:
                    exists = Activity.query.filter(
                        Activity.day_id == day9.id,
                        Activity.title.like(f'%{title[:20]}%')
                    ).first()
                    if not exists:
                        db.session.add(Activity(
                            day_id=day9.id, title=title, time_slot=slot,
                            sort_order=order, getting_there=gt,
                        ))
                print("  Added Kyoto sightseeing activities to Day 9")

        # --- Day 10: Fix Kiyomizu-dera (if also on Day 9 now, eliminate on Day 10) ---
        day10 = Day.query.filter_by(day_number=10).first()
        if day10:
            kiyomizu_d10 = Activity.query.filter(
                Activity.day_id == day10.id,
                Activity.title.like('%Kiyomizu%'),
                Activity.is_eliminated == False
            ).first()
            kiyomizu_d9 = Activity.query.filter(
                Activity.day_id == (day9.id if day9 else -1),
                Activity.title.like('%Kiyomizu%'),
                Activity.is_eliminated == False
            ).first()
            if kiyomizu_d10 and kiyomizu_d9:
                kiyomizu_d10.is_eliminated = True
                print("  Eliminated Day 10 Kiyomizu-dera (now on Day 9)")

        # --- Day 11: Hiroshima day trip from Kyoto (this is correct) ---
        # Already has Hiroshima content — just verify title
        day11 = Day.query.filter_by(day_number=11).first()
        if day11:
            day11.title = 'DAY TRIP — HIROSHIMA & MIYAJIMA ISLAND'

        # --- Day 12: Eliminate duplicate Hiroshima, make it Kyoto→Osaka transit ---
        day12 = Day.query.filter_by(day_number=12).first()
        if day12:
            # Check if Day 12 has Hiroshima activities — if Day 11 also does, eliminate Day 12's
            day11_hiroshima = Activity.query.filter(
                Activity.day_id == (day11.id if day11 else -1),
                Activity.title.like('%Hiroshima%'),
                Activity.is_eliminated == False
            ).count()

            if day11_hiroshima > 0:
                # Day 11 already covers Hiroshima — eliminate Day 12 Hiroshima dupes
                for act in Activity.query.filter(
                    Activity.day_id == day12.id,
                    Activity.is_eliminated == False
                ).all():
                    if any(kw in act.title for kw in [
                        'Hiroshima', 'A-Bomb', 'okonomiyaki', 'Miyajima',
                        'Itsukushima', 'JR train to', 'JR Ferry',
                        'Shinkansen Kyoto', 'Shinkansen Hiroshima',
                        'coin locker', 'Store luggage',
                    ]):
                        act.is_eliminated = True
                        print(f"  Eliminated Day 12: '{act.title}' (Hiroshima dupe)")

                day12.title = 'KYOTO → OSAKA'
                # Change Day 12 location to Osaka
                osaka_location = Location.query.filter_by(name='Osaka').first()
                if osaka_location:
                    day12.location_id = osaka_location.id

                # Add Kyoto→Osaka transit activities
                transit_acts = [
                    ('Check out of Kyotofish Miyagawa Ochaya', 'morning', 100,
                     'Checkout by 10:00 AM.'),
                    ('Last Kyoto exploration & omiyage shopping', 'morning', 200,
                     'Nishiki Market or Kyoto Station shopping area.'),
                    ('JR Special Rapid: Kyoto → Osaka', 'afternoon', 300,
                     'JR Special Rapid from Kyoto Station to Osaka Station (~30 min). JR Pass covered.'),
                    ('Check into Hotel The Leben Osaka', 'afternoon', 400,
                     'From Osaka Station: Midosuji Line to Shinsaibashi Station (3 stops). 5 min walk to hotel.'),
                    ('Explore Shinsaibashi & Amerikamura', 'afternoon', 500,
                     'Walk from hotel — Shinsaibashi shopping arcade is right outside.'),
                    ('Dotonbori Night Walk', 'evening', 600,
                     '~10 min walk south from Shinsaibashi to the canal.'),
                ]
                for title, slot, order, gt in transit_acts:
                    exists = Activity.query.filter(
                        Activity.day_id == day12.id,
                        Activity.title.like(f'%{title[:20]}%')
                    ).first()
                    if not exists:
                        db.session.add(Activity(
                            day_id=day12.id, title=title, time_slot=slot,
                            sort_order=order, getting_there=gt,
                        ))
                print("  Restructured Day 12 as Kyoto → Osaka transit day")

        # --- Day 13: Now a FULL Osaka day (no morning transit needed) ---
        day13 = Day.query.filter_by(day_number=13).first()
        if day13:
            day13.title = 'FULL DAY OSAKA — Street Food & Neon'
            # Eliminate transit activities that are now on Day 12
            for frag in ['Check out of Kyoto', 'JR Special Rapid to Osaka']:
                act = Activity.query.filter(
                    Activity.day_id == day13.id,
                    Activity.title.like(f'%{frag}%'),
                    Activity.is_eliminated == False
                ).first()
                if act:
                    act.is_eliminated = True
                    print(f"  Eliminated Day 13: '{act.title}' (now on Day 12)")

            # "Check into Osaka hotel" should also be eliminated (now Day 12)
            checkin_osaka = Activity.query.filter(
                Activity.day_id == day13.id,
                Activity.title.like('%Check into Osaka%'),
                Activity.is_eliminated == False
            ).first()
            if checkin_osaka:
                checkin_osaka.is_eliminated = True
                print("  Eliminated Day 13: 'Check into Osaka hotel' (now on Day 12)")

        # --- Day 14: Update departure activities ---
        day14 = Day.query.filter_by(day_number=14).first()
        if day14:
            # Update checkout reference
            checkout_act = Activity.query.filter(
                Activity.day_id == day14.id,
                Activity.title.like('%checkout%Hotel Leben%')
            ).first()
            if not checkout_act:
                checkout_act = Activity.query.filter(
                    Activity.day_id == day14.id,
                    Activity.title.like('%Early checkout%')
                ).first()
            if checkout_act:
                checkout_act.title = 'Check out of Hotel The Leben Osaka'
                checkout_act.getting_there = 'Checkout before 11:00 AM. Flight UA876 departs HND 3:50 PM.'

        # ============================================================
        # 7. FLIGHT UPDATES — add confirmation details from PDFs
        # ============================================================
        from models import Flight
        # Outbound: DL5392 + DL275
        dl_flights = Flight.query.filter(Flight.direction == 'outbound').all()
        for f in dl_flights:
            if 'DL' in (f.flight_number or '') or 'Delta' in (f.airline or ''):
                if not f.confirmation_number:
                    f.confirmation_number = 'HBPF75'
                f.booking_status = 'confirmed'

        # Return: UA876 + UA1470
        ua_flights = Flight.query.filter(Flight.direction == 'return').all()
        for f in ua_flights:
            if 'UA' in (f.flight_number or '') or 'United' in (f.airline or ''):
                if not f.confirmation_number:
                    f.confirmation_number = 'I91ZHJ'
                f.booking_status = 'confirmed'

        # Mark sentinel and commit
        trip.notes = (trip.notes or '') + '\n' + sentinel
        db.session.commit()
        print("Migration complete: confirmed_bookings_v1 applied successfully.")


def _migrate_fix_takanoyu_v1(app):
    """Fix TAKANOYU as the correct selected Takayama accommodation.

    The confirmed_bookings_v1 migration created a duplicate 'Traditional Room
    above Sento' option at the same address as TAKANOYU. They are the same
    property. TAKANOYU was booked first and is the user-recognized name.

    Also removes the erroneous 'Book Kanazawa' checklist item.
    """
    from models import (Trip, AccommodationOption, ChecklistItem, db)

    with app.app_context():
        trip = Trip.query.first()
        if not trip:
            return
        sentinel = '__fix_takanoyu_v1'
        if trip.notes and sentinel in trip.notes:
            print("fix_takanoyu_v1: already applied, skipping")
            return

        print("Running migration: fix_takanoyu_v1...")

        # --- 1. Find both options (same property at souyuji-machi 107) ---
        takanoyu = AccommodationOption.query.filter(
            AccommodationOption.name.ilike('%TAKANOYU%')).first()
        sento_dup = AccommodationOption.query.filter(
            AccommodationOption.name.ilike('%Traditional Room above Sento%')).first()

        if takanoyu and sento_dup:
            # Copy PDF-verified data from duplicate into TAKANOYU
            takanoyu.confirmation_number = sento_dup.confirmation_number or takanoyu.confirmation_number
            takanoyu.booking_status = 'confirmed'
            takanoyu.is_selected = True
            takanoyu.is_eliminated = False
            takanoyu.address = sento_dup.address or takanoyu.address
            takanoyu.phone = sento_dup.phone or takanoyu.phone
            takanoyu.check_in_info = sento_dup.check_in_info or takanoyu.check_in_info
            takanoyu.check_out_info = sento_dup.check_out_info or takanoyu.check_out_info
            if sento_dup.user_notes:
                takanoyu.user_notes = sento_dup.user_notes

            # Eliminate the duplicate
            sento_dup.is_selected = False
            sento_dup.is_eliminated = True
            print("  TAKANOYU: selected + confirmed (merged PDF data from duplicate)")
            print("  Traditional Room above Sento: eliminated (duplicate)")
        elif takanoyu:
            # Just fix TAKANOYU directly
            takanoyu.booking_status = 'confirmed'
            takanoyu.is_selected = True
            takanoyu.is_eliminated = False
            takanoyu.confirmation_number = takanoyu.confirmation_number or 'HMDDRX4NFX'
            print("  TAKANOYU: selected + confirmed")

        # --- 2. Remove 'Book Kanazawa' checklist item ---
        kanazawa_book = ChecklistItem.query.filter(
            ChecklistItem.title.ilike('%Book Kanazawa%')).first()
        if kanazawa_book:
            db.session.delete(kanazawa_book)
            print(f"  Deleted checklist: '{kanazawa_book.title}'")

        # Mark sentinel and commit
        trip.notes = (trip.notes or '') + '\n' + sentinel
        db.session.commit()
        print("Migration complete: fix_takanoyu_v1 applied.")

