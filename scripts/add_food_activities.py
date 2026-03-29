"""One-time script: add food, bar, and dining recommendations to production."""
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

activities = [
    # === TOKYO DAY 2 ===
    {
        'day_id': day_map[2],
        'title': 'Gyukatsu Motomura (rare beef cutlet you sear yourself)',
        'description': 'THE gyukatsu spot. Beef served very rare, cook it on a hot stone at your seat. Get the 130g barley rice set. Expect 30-60 min queue at peak.',
        'address': 'Near Shinjuku-sanchome Station',
        'time_slot': 'afternoon',
        'category': 'food',
        'cost_note': '\u00a51,500-1,800',
        'is_optional': True,
    },
    # === TOKYO DAY 3 ===
    {
        'day_id': day_map[3],
        'title': 'TeamLab Borderless at Azabudai Hills',
        'description': 'Immersive digital art museum. Sells out weeks ahead \u2014 book NOW. 2-3 hours to explore. Stunning photo ops. \u00a53,800-4,800 depending on date.',
        'address': 'Azabudai Hills, Minato-ku, Tokyo',
        'url': 'https://www.teamlab.art/e/borderless-azabudai/',
        'time_slot': 'afternoon',
        'category': 'entertainment',
        'cost_note': '\u00a53,800-4,800, book online',
        'is_optional': True,
    },
    {
        'day_id': day_map[3],
        'title': 'Fuunji tsukemen (legendary dipping ramen)',
        'description': 'Widely considered Tokyo\'s best tsukemen. Thick broth simmered 38 hours. Get the large (free upgrade). 5 min walk south of Shinjuku Station. Arrive before 11 AM opening.',
        'address': '2-14-3 Yoyogi, Shibuya-ku',
        'time_slot': 'afternoon',
        'category': 'food',
        'cost_note': '\u00a51,000-1,200',
        'is_optional': True,
    },
    {
        'day_id': day_map[3],
        'title': 'Golden Gai: Albatross G, La Jetee, Open Book',
        'description': 'Albatross G: eclectic vintage decor, tiny balcony. La Jetee: film-themed, Japanese whiskey. Open Book: literary bar with curry toast. Cover charge 500-1,000\u00a5 each. Budget 3-4 bars in a night.',
        'address': 'Golden Gai, Kabukicho, Shinjuku',
        'time_slot': 'night',
        'category': 'nightlife',
        'cost_note': 'Drinks \u00a5800-1,500 + cover per bar',
        'is_optional': True,
    },
    {
        'day_id': day_map[3],
        'title': 'Ramen Nagi (Golden Gai, open 24h)',
        'description': 'Dried sardine (niboshi) ramen in a tiny 2nd-floor Golden Gai shop. Customize salt, richness, garlic, noodle firmness. Perfect 2 AM post-bar-hop meal.',
        'address': 'Golden Gai 2F, Kabukicho',
        'time_slot': 'night',
        'category': 'food',
        'cost_note': '\u00a51,000-1,200',
        'is_optional': True,
    },

    # === TAKAYAMA DAY 5 ===
    {
        'day_id': day_map[5],
        'title': 'Hidagyu Maruaki (best-value Hida beef yakiniku)',
        'description': 'Butcher shop + restaurant. A5 Hida beef cut and grilled in front of you. Arrive at 11 AM or 5 PM opening \u2014 no reservations, lines form fast. Cash recommended.',
        'address': 'Central Takayama, near old town',
        'time_slot': 'evening',
        'category': 'food',
        'cost_note': 'Lunch \u00a52,500-4,000, dinner \u00a55,000-8,000',
        'is_optional': True,
    },

    # === TAKAYAMA DAY 6 ===
    {
        'day_id': day_map[6],
        'title': 'Hida Kotte Ushi (seared A5 beef sushi on rice cracker)',
        'description': 'Street stall on Sanmachi Suji. Seared A5 Hida beef sushi on a crispy rice cracker \u2014 get the version with quail egg yolk on top. Always a line but moves fast.',
        'address': 'Sanmachi Suji, Takayama',
        'time_slot': 'afternoon',
        'category': 'food',
        'cost_note': '\u00a5600-800 for 2 pieces',
        'is_optional': True,
    },
    {
        'day_id': day_map[6],
        'title': 'Harada Sake Brewery (500\u00a5 tasting + keep the cup)',
        'description': 'Pay \u00a5500, get a ceramic sake cup to keep, then self-serve taste 12 different sake varieties. Also has sake soft serve ice cream. Best deal in Takayama.',
        'address': 'Sanmachi Suji (Kami-sannomachi), Takayama',
        'time_slot': 'afternoon',
        'category': 'food',
        'cost_note': '\u00a5500 for tasting + cup',
        'is_optional': True,
    },

    # === TAKAYAMA DAY 7 ===
    {
        'day_id': day_map[7],
        'title': 'Menya Shirakawa (definitive Takayama ramen)',
        'description': 'THE Takayama chuka soba. Simple, clear soy broth with thin curly noodles. Lighter and more delicate than Tokyo-style. Locals line up for this.',
        'address': 'Central Takayama',
        'time_slot': 'afternoon',
        'category': 'food',
        'cost_note': '\u00a5850-1,000',
        'is_optional': True,
    },

    # === KYOTO DAY 9 ===
    {
        'day_id': day_map[9],
        'title': 'Kaiseki dinner: Giro Giro Hitoshina (modern, approachable)',
        'description': 'Modern kaiseki with a fun twist. Counter seating, watch the chefs. Most-recommended "first kaiseki" on Reddit. \u00a55,000-6,000 per person. Reservation required.',
        'address': 'Near Gion, Kyoto',
        'time_slot': 'evening',
        'category': 'food',
        'cost_note': '\u00a55,000-6,000 course',
        'is_optional': True,
    },

    # === KYOTO DAY 10 ===
    {
        'day_id': day_map[10],
        'title': 'Menbakaichidai fire ramen (near Nijo Castle)',
        'description': 'Chef literally sets your bowl on fire by pouring 680\u00b0 oil over green onions. You wear an apron. Don\'t photograph when oil is poured. Fun spectacle, decent ramen.',
        'address': 'Near Nijo Castle, Nakagyo-ku, Kyoto',
        'url': 'https://www.fireramen.com/',
        'time_slot': 'afternoon',
        'category': 'food',
        'cost_note': '\u00a51,000-1,200',
        'is_optional': True,
    },
    {
        'day_id': day_map[10],
        'title': 'Yudofu at Nanzenji Junsei (400-year-old tofu restaurant)',
        'description': 'Kyoto\'s most famous yudofu (simmered tofu) restaurant. Beautiful Edo-period building with strolling garden. Lunch Hana Course \u00a53,300-4,400. Reservation recommended.',
        'address': 'Near Nanzen-ji Temple, Sakyo-ku, Kyoto',
        'url': 'https://www.to-fu.co.jp/en/',
        'time_slot': 'afternoon',
        'category': 'food',
        'cost_note': 'Lunch \u00a53,300-4,400',
        'is_optional': True,
    },

    # === KYOTO DAY 11 (Hiroshima) ===
    {
        'day_id': day_map[11],
        'title': 'Nagata-ya okonomiyaki (best in Hiroshima, near Peace Park)',
        'description': 'Right across from Peace Park. Hiroshima-style layered okonomiyaki. Get the special with soba noodles, pork, egg, and cheese. Expect 30-60 min line \u2014 go at 11 AM opening.',
        'address': 'Near Peace Park, Naka-ku, Hiroshima',
        'time_slot': 'afternoon',
        'category': 'food',
        'cost_note': '\u00a51,000-1,500',
        'is_optional': True,
    },
    {
        'day_id': day_map[11],
        'title': 'Yakigaki no Hayashi grilled oysters (Miyajima)',
        'description': 'First grilled oyster shop in Japan, on Miyajima\'s main street. Uses premium 3-year-old oysters \u2014 bigger and more flavorful. Also try kaki fry (fried oysters).',
        'address': 'Omotesando, Miyajima',
        'time_slot': 'afternoon',
        'category': 'food',
        'cost_note': '\u00a51,200-2,000 for a set',
        'is_optional': True,
    },

    # === OSAKA DAY 12 ===
    {
        'day_id': day_map[12],
        'title': 'Dotonbori food crawl order: takoyaki \u2192 gyoza \u2192 kushikatsu \u2192 okonomiyaki',
        'description': 'Night 1: Wanaka takoyaki \u2192 Osaka Ohsho standing gyoza bar (\u00a5200 gyoza + \u00a5200 beer) \u2192 Daruma kushikatsu. Night 2: Mizuno okonomiyaki \u2192 Hozenji Yokocho \u2192 Rikuro cheesecake. Split across 2 evenings.',
        'address': 'Dotonbori, Chuo-ku, Osaka',
        'time_slot': 'evening',
        'category': 'food',
        'is_optional': True,
    },
    {
        'day_id': day_map[12],
        'title': 'Ura-Namba: Torame Yokocho izakaya alley',
        'description': 'Lantern-lit alley with red torii gate entrance, 9 handpicked izakayas. Where locals drink \u2014 not tourists. Walk in and pick whichever stall catches your eye. South of Namba Station.',
        'address': 'Sennichimae, Chuo-ku, Osaka',
        'time_slot': 'night',
        'category': 'nightlife',
        'is_optional': True,
    },

    # === OSAKA DAY 13 ===
    {
        'day_id': day_map[13],
        'title': 'Kushikatsu Daruma (original Shinsekai)',
        'description': 'The iconic kushikatsu spot with the angry chef mascot. Classic set: pork, onion, shrimp, asparagus, quail egg, cheese. NEVER double-dip in the communal sauce.',
        'address': 'Shinsekai, Naniwa-ku, Osaka',
        'time_slot': 'afternoon',
        'category': 'food',
        'cost_note': '\u00a51,500-2,500',
        'is_optional': True,
    },
    {
        'day_id': day_map[13],
        'title': '551 Horai nikuman (Osaka iconic pork bun)',
        'description': 'Osaka\'s most beloved brand. Steaming pork buns with juicy filling. Branches everywhere but the main shop is in Namba. \u00a5200 per bun. Buy a box to eat on the shinkansen home.',
        'address': 'Namba area, Osaka',
        'time_slot': 'afternoon',
        'category': 'food',
        'cost_note': '\u00a5200 per bun',
        'is_optional': True,
    },

    # === KYOTO NIGHT ILLUMINATION ===
    {
        'day_id': day_map[9],
        'title': 'Kiyomizu-dera night illumination (spring special)',
        'description': 'Special evening opening during cherry blossom season. The temple and surrounding cherry trees are illuminated \u2014 spectacular. Check exact dates (usually through mid-April). Separate ticket from daytime.',
        'address': '1-294 Kiyomizu, Higashiyama-ku, Kyoto',
        'url': 'https://www.kiyomizudera.or.jp/en/',
        'time_slot': 'evening',
        'category': 'temple',
        'cost_note': '\u00a5400 evening ticket',
        'is_optional': True,
    },
    {
        'day_id': day_map[10],
        'title': 'Nijo Castle night cherry blossom illumination',
        'description': 'Special evening event during cherry blossom season. Projections + illuminated gardens. \u00a51,200 separate evening ticket. Check dates \u2014 usually early-mid April.',
        'address': '541 Nijojocho, Nakagyo-ku, Kyoto',
        'url': 'https://nijo-jocastle.city.kyoto.lg.jp/?lang=en',
        'time_slot': 'evening',
        'category': 'culture',
        'cost_note': '\u00a51,200 evening ticket',
        'is_optional': True,
    },
]

ok = 0
for item in activities:
    resp = requests.post(f'{BASE}/api/activities/add', json=item)
    name = item['title'][:55]
    if resp.ok:
        ok += 1
    else:
        print(f'  FAIL "{name}": {resp.status_code} {resp.text[:80]}')

print(f'Added {ok}/{len(activities)} food/bar/experience activities')
