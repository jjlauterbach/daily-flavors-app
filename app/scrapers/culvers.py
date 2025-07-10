import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from app.scrapers.utils import daily_flavor, get_html

CULVERS_LOCATIONS = [
    ("Culvers (Capital)", "https://www.culvers.com/restaurants/brookfield-capitol"),
    ("Culvers (Waukesha Main St)", "https://www.culvers.com/restaurants/waukesha-hwy-164"),
    ("Culvers (Waukesha Grandview)", "https://www.culvers.com/restaurants/waukesha-grandview"),
    ("Culvers (Sussex)", "https://www.culvers.com/restaurants/sussex"),
]


def scrape_culvers():
    """Scrape multiple Culver's locations"""
    logger = logging.getLogger(__name__)
    logger.info("🚀 CULVERS: Starting scrape of all locations...")
    flavors = []
    for name, url in CULVERS_LOCATIONS:
        try:
            logger.info(f"📍 CULVERS: Scraping {name}...")
            flavor, description, flavor_date = _scrape_culvers_location(url)
            flavors.append(daily_flavor(name, flavor, description, flavor_date, url=url))
            logger.info(f"🍨 CULVERS: {name} - {flavor} ({flavor_date})")
        except Exception as e:
            logger.error(f"❌ CULVERS: Failed to scrape {name}: {e}")
    logger.info(f"✅ CULVERS: Completed - found {len(flavors)} location(s)")
    return flavors


def _scrape_culvers_location(url):
    html = get_html(url)
    script_tag = html.find("script", id="__NEXT_DATA__", type="application/json")
    if not script_tag or not script_tag.string:
        raise Exception("Could not find Culver's JSON data on the page.")
    data = json.loads(script_tag.string)
    # Try all plausible locations for the flavors array
    flavors = None
    pageProps = data.get("props", {}).get("pageProps", {})
    # Try all known paths
    paths = [
        ["restaurantCalendar", "flavors"],
        ["page", "customData", "flavorDetails", "flavors"],
        ["customData", "flavorDetails", "flavors"],
        ["flavorDetails", "flavors"],
        ["page", "customData", "restaurantCalendar", "flavors"],  # <-- add this path
    ]
    for path in paths:
        d = pageProps
        for key in path:
            if isinstance(d, dict) and key in d:
                d = d[key]
            else:
                d = None
                break
        if isinstance(d, list):
            flavors = d
            break
    if not flavors:
        # Log available keys for debugging
        import logging

        logger = logging.getLogger(__name__)
        logger.warning(f"CULVERS: Could not find flavors. pageProps keys: {list(pageProps.keys())}")
        return "", "", None
    # Use US/Central timezone for 'today'
    tz = ZoneInfo("America/Chicago")
    now_central = datetime.now(tz)
    today = now_central.date()
    # Collect all entries with valid dates
    dated_entries = []
    for entry in flavors:
        date_str = entry.get("onDate") or entry.get("calendarDate")
        if not date_str:
            continue
        try:
            date = datetime.strptime(date_str[:10], "%Y-%m-%d").date()
            dated_entries.append((date, entry))
        except Exception:
            continue
    if not dated_entries:
        return "", "", None
    # Sort by date ascending
    dated_entries.sort()
    # Try to find today's flavor
    for date, entry in dated_entries:
        if date == today:
            flavor = entry.get("title") or entry.get("name") or ""
            description = entry.get("description") or ""
            date_str = (entry.get("onDate") or entry.get("calendarDate") or "")[:10]
            return flavor, description, date_str
    # Try to find the next future flavor
    for date, entry in dated_entries:
        if date > today:
            flavor = entry.get("title") or entry.get("name") or ""
            description = entry.get("description") or ""
            date_str = (entry.get("onDate") or entry.get("calendarDate") or "")[:10]
            return flavor, description, date_str
    flavor = entry.get("title") or entry.get("name") or ""
    description = entry.get("description") or ""
    date_str = (entry.get("onDate") or entry.get("calendarDate") or "")[:10]
    return flavor, description, date_str
