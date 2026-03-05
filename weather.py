"""Weather and currency data with file-based caching."""
import json
import os
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

CACHE_DIR = os.path.join(os.path.dirname(__file__), 'data')
WEATHER_CACHE = os.path.join(CACHE_DIR, 'weather_cache.json')
CURRENCY_CACHE = os.path.join(CACHE_DIR, 'currency_cache.json')
WEATHER_TTL = 6 * 3600    # 6 hours
CURRENCY_TTL = 4 * 3600   # 4 hours
FAIL_TTL = 15 * 60        # 15 min — cache failures to avoid repeated retries


def _read_cache(filepath, ttl):
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        if time.time() - data.get('timestamp', 0) < ttl:
            return data.get('payload')
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        pass
    return None


def _write_cache(filepath, payload):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w') as f:
        json.dump({'timestamp': time.time(), 'payload': payload}, f)


def get_weather_data(days, location_groups, days_until=None):
    """Fetch 16-day forecast from Open-Meteo for each unique location.

    Returns dict keyed by day_number -> {icon, temp_high, temp_low, rain_pct}.
    Skips API calls entirely when trip is more than 16 days away.
    """
    # Open-Meteo only provides 16-day forecasts — skip if trip is far away
    if days_until is not None and days_until > 16:
        return {}

    cached = _read_cache(WEATHER_CACHE, WEATHER_TTL)
    if cached is not None:
        return cached

    # Check if we recently failed (avoid repeated retries during outages)
    fail_cached = _read_cache(WEATHER_CACHE, FAIL_TTL)
    if fail_cached is not None:
        return fail_cached

    # Collect unique locations with coordinates
    seen = set()
    locations = []
    for group in location_groups:
        loc = group.get('location_obj')
        if loc and loc.latitude and loc.name not in seen:
            seen.add(loc.name)
            locations.append({
                'name': loc.name,
                'lat': loc.latitude,
                'lon': loc.longitude,
            })

    # Build day lookup: date_iso -> [(day_number, location_name)]
    day_lookup = {}
    for day in days:
        if day.location:
            day_lookup.setdefault(day.date.isoformat(), []).append(
                (day.day_number, day.location.name))

    def _fetch_location(loc_info):
        """Fetch weather for one location. Returns list of (day_num, weather_dict)."""
        results = []
        try:
            url = (
                f"https://api.open-meteo.com/v1/forecast?"
                f"latitude={loc_info['lat']}&longitude={loc_info['lon']}"
                f"&daily=temperature_2m_max,temperature_2m_min,"
                f"precipitation_probability_max,weather_code"
                f"&temperature_unit=fahrenheit"
                f"&timezone=Asia/Tokyo&forecast_days=16"
            )
            resp = urllib.request.urlopen(url, timeout=5)
            data = json.loads(resp.read())
            daily = data.get('daily', {})
            dates = daily.get('time', [])
            for i, date_str in enumerate(dates):
                for day_num, loc_name in day_lookup.get(date_str, []):
                    if loc_name == loc_info['name']:
                        results.append((str(day_num), {
                            'temp_high': daily['temperature_2m_max'][i],
                            'temp_low': daily['temperature_2m_min'][i],
                            'rain_pct': daily['precipitation_probability_max'][i],
                            'code': daily['weather_code'][i],
                            'icon': _weather_icon(daily['weather_code'][i]),
                        }))
        except Exception:
            pass
        return results

    # Fetch all locations in parallel (5s timeout each, but concurrent)
    weather_by_day = {}
    with ThreadPoolExecutor(max_workers=min(len(locations), 4)) as pool:
        futures = {pool.submit(_fetch_location, loc): loc for loc in locations}
        for future in as_completed(futures):
            for day_num, weather in future.result():
                weather_by_day[day_num] = weather

    # Cache even empty results so we don't retry immediately on failure
    _write_cache(WEATHER_CACHE, weather_by_day)
    return weather_by_day


def _weather_icon(code):
    """Map WMO weather code to emoji."""
    if code <= 1:
        return '\u2600\ufe0f'       # sunny
    elif code <= 3:
        return '\u26c5'             # partly cloudy
    elif code <= 48:
        return '\u2601\ufe0f'       # cloudy/fog
    elif code <= 67:
        return '\U0001f327\ufe0f'   # rain
    elif code <= 77:
        return '\u2744\ufe0f'       # snow
    elif code <= 82:
        return '\U0001f327\ufe0f'   # rain showers
    elif code <= 86:
        return '\u2744\ufe0f'       # snow showers
    else:
        return '\u26a1'             # thunderstorm


def get_exchange_rate(days_until=None):
    """Fetch USD->JPY rate from Frankfurter API with caching.

    Caches failures for FAIL_TTL to prevent repeated blocking retries.
    Skips API call when trip is more than 30 days away.
    """
    if days_until is not None and days_until > 30:
        return {'rate': None, 'updated': ''}

    cached = _read_cache(CURRENCY_CACHE, CURRENCY_TTL)
    if cached is not None:
        return cached

    try:
        url = "https://api.frankfurter.app/latest?from=USD&to=JPY"
        resp = urllib.request.urlopen(url, timeout=5)
        data = json.loads(resp.read())
        rate = data['rates']['JPY']
        result = {'rate': rate, 'updated': data.get('date', '')}
        _write_cache(CURRENCY_CACHE, result)
        return result
    except Exception:
        # Cache the failure so we don't retry on every page load
        fallback = {'rate': None, 'updated': ''}
        _write_cache(CURRENCY_CACHE, fallback)
        return fallback
