"""One-time script: add missing recommended activities to production."""
import requests
import sqlite3
import tempfile

BASE = 'https://web-production-f84b27.up.railway.app'

# Get day IDs
resp = requests.get(f'{BASE}/api/backup/download')
tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
tmp.write(resp.content)
tmp.close()
conn = sqlite3.connect(tmp.name)
c = conn.cursor()
c.execute('SELECT id, day_number FROM day')
day_map = {r[1]: r[0] for r in c.fetchall()}
conn.close()

new_activities = [
    # TOKYO Day 2
    {
        'day_id': day_map[2],
        'title': 'Shinjuku Gyoen National Garden (cherry blossoms)',
        'description': "One of Tokyo's best cherry blossom spots with 1,000+ trees. Peaceful (alcohol banned). 10 min walk from hotel. Perfect jet-lag recovery.",
        'address': '11 Naitomachi, Shinjuku-ku, Tokyo',
        'url': 'https://fng.or.jp/shinjuku/en/',
        'time_slot': 'afternoon',
        'category': 'nature',
        'cost_note': '\u00a5500 entry',
        'is_optional': True,
    },
    {
        'day_id': day_map[2],
        'title': 'Chidorigafuchi cherry blossom boats (Imperial Palace moat)',
        'description': "Tokyo's #1 cherry blossom spot. Rent rowboats under a canopy of sakura along the palace moat. ~\u00a5800/30 min. Go weekday morning to avoid 60-90 min queue.",
        'address': 'Chidorigafuchi, Chiyoda-ku, Tokyo',
        'url': 'https://visit-chiyoda.tokyo/en/spots/4',
        'time_slot': 'morning',
        'category': 'nature',
        'cost_note': '~\u00a5800/30 min boat',
        'is_optional': True,
    },
    {
        'day_id': day_map[2],
        'title': 'Nakameguro cherry blossoms (evening illumination)',
        'description': 'Meguro River lined with cherry trees, illuminated with lanterns at night. Trendy cafes along the canal. Free. One of Tokyo\'s most photogenic evening spots.',
        'address': 'Nakameguro, Meguro-ku, Tokyo',
        'time_slot': 'evening',
        'category': 'nature',
        'is_optional': True,
    },
    # TOKYO Day 3
    {
        'day_id': day_map[3],
        'title': 'Shibuya Sky observation deck (230m)',
        'description': 'Stunning 360-degree rooftop views from Shibuya Scramble Square. Best at sunset. \u00a52,000. Book online in advance \u2014 sells out.',
        'address': '2-24-12 Shibuya, Shibuya-ku, Tokyo',
        'url': 'https://www.shibuya-scramble-square.com/sky/',
        'time_slot': 'afternoon',
        'category': 'entertainment',
        'cost_note': '\u00a52,000, book online',
        'is_optional': True,
    },
    {
        'day_id': day_map[3],
        'title': 'Akihabara (Electric Town)',
        'description': 'Anime, manga, retro game arcades, maid cafes, figurine stores. Multi-story arcades. Authentic otaku culture.',
        'address': 'Akihabara, Chiyoda-ku, Tokyo',
        'time_slot': 'afternoon',
        'category': 'shopping',
        'is_optional': True,
    },
    {
        'day_id': day_map[3],
        'title': 'Tsukiji Outer Market (breakfast crawl)',
        'description': 'Fresh tamago, tamagoyaki, tuna skewers, street food. Best 7:00-12:00. Many stalls close by early afternoon.',
        'address': 'Tsukiji 4-chome, Chuo-ku, Tokyo',
        'url': 'https://www.tsukiji.or.jp/english/',
        'time_slot': 'morning',
        'category': 'food',
        'cost_note': '\u00a51,000-3,000 food crawl',
        'is_optional': True,
    },
    # HAKONE Day 4
    {
        'day_id': day_map[4],
        'title': 'Hakone Shrine (lakeside torii gate)',
        'description': "Iconic red torii gate standing in Lake Ashi. Shrine set in cedar forest. Free. Go early to avoid 30+ min photo queue.",
        'address': '80-1 Motohakone, Hakone-machi',
        'url': 'https://hakonejinja.or.jp/',
        'time_slot': 'afternoon',
        'category': 'temple',
        'is_optional': True,
    },
    # TAKAYAMA Day 7
    {
        'day_id': day_map[7],
        'title': 'Higashiyama Walking Course (13 temples trail)',
        'description': 'Peaceful 3.5km trail through eastern temple district connecting 13 temples and 5 shrines. Lovely with cherry blossoms. Allow 1.5-2 hours.',
        'address': 'Higashiyama, Takayama-shi, Gifu',
        'time_slot': 'morning',
        'category': 'nature',
        'is_optional': True,
    },
    # KYOTO Day 9
    {
        'day_id': day_map[9],
        'title': 'Keage Incline (cherry blossom rail tracks)',
        'description': "Abandoned railway incline lined with cherry trees. Walk along the tracks under a canopy of sakura. Near Nanzen-ji. Free, open 24/7. Most photogenic spot in Kyoto.",
        'address': 'Keage, Sakyo-ku, Kyoto',
        'time_slot': 'morning',
        'category': 'nature',
        'is_optional': True,
    },
    # KYOTO Day 10
    {
        'day_id': day_map[10],
        'title': 'Nijo Castle + nightingale floors',
        'description': "Shogun's castle with floors that chirp when walked on. Beautiful cherry blossom gardens. Night illumination during blossom season. \u00a5800 daytime.",
        'address': '541 Nijojocho, Nakagyo-ku, Kyoto',
        'url': 'https://nijo-jocastle.city.kyoto.lg.jp/?lang=en',
        'time_slot': 'afternoon',
        'category': 'culture',
        'cost_note': '\u00a5800 daytime',
        'is_optional': True,
    },
    # OSAKA Day 12
    {
        'day_id': day_map[12],
        'title': 'Osaka-style okonomiyaki (Mizuno or Kiji)',
        'description': 'Mixed-style okonomiyaki. Mizuno (Dotonbori, expect queue) or Kiji (Umeda, local favorite). \u00a5900-1,500.',
        'address': 'Dotonbori area, Chuo-ku, Osaka',
        'time_slot': 'evening',
        'category': 'food',
        'cost_note': '\u00a5900-1,500',
        'is_optional': True,
    },
    # NARA Day 13
    {
        'day_id': day_map[13],
        'title': 'Kasuga Taisha Shrine (3,000 lanterns)',
        'description': 'Ancient shrine (768 AD) famous for thousands of stone and bronze lanterns. Atmospheric approach through primeval forest. Main area free, inner sanctuary \u00a5500.',
        'address': '160 Kasuganocho, Nara',
        'url': 'https://www.kasugataisha.or.jp/en/',
        'time_slot': 'morning',
        'category': 'temple',
        'cost_note': 'Free (inner \u00a5500)',
        'is_optional': True,
    },
    {
        'day_id': day_map[13],
        'title': 'Nigatsu-do Hall (best free view in Nara)',
        'description': 'Part of Todai-ji complex, often overlooked. Wooden balcony with sweeping panorama over Nara. Free. Walk up the atmospheric stone lantern stairway.',
        'address': 'Todai-ji complex, Zoshicho, Nara',
        'time_slot': 'afternoon',
        'category': 'temple',
        'is_optional': True,
    },
    {
        'day_id': day_map[13],
        'title': 'Naramachi old town + mochi pounding show',
        'description': 'Traditional merchant district with machiya cafes. Nakatanidou does entertaining high-speed mochi-pounding performances. Mochi \u00a5150-300.',
        'address': 'Naramachi, Nara',
        'time_slot': 'afternoon',
        'category': 'food',
        'cost_note': 'Mochi \u00a5150-300',
        'is_optional': True,
    },
]

ok = 0
for item in new_activities:
    resp = requests.post(f'{BASE}/api/activities/add', json=item)
    name = item['title'][:50]
    if resp.ok:
        ok += 1
    else:
        print(f'  FAIL "{name}": {resp.status_code} {resp.text[:80]}')

print(f'Added {ok}/{len(new_activities)} new optional activities')

# Fix Osaka Castle description
resp = requests.put(f'{BASE}/api/activities/155/update', json={
    'description': 'The exterior and park are stunning. Castle tower is a modern concrete museum (\u00a51,200 entry). Cherry blossoms around the moat are the real draw. Park is free.',
})
print(f'Fix Osaka Castle desc: {resp.status_code}')

# Fix Takayama Jinya price
resp = requests.put(f'{BASE}/api/activities/200/update', json={
    'cost_note': '\u00a5440 entry',
    'url': 'https://jinya.gifu.jp/en/',
})
print(f'Fix Jinya price: {resp.status_code}')

print('\nDone')
