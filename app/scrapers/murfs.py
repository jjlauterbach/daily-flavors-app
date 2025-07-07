import datetime
import logging
from zoneinfo import ZoneInfo

from app.scrapers.utils import daily_flavor, get_html

logger = logging.getLogger(__name__)


def scrape_murfs():
    """Scrape Murf's Frozen Custard"""
    logger.info("🚀 MURFS: Starting scrape...")
    try:
        html = get_html("https://www.murfsfrozencustard.com/flavorForecast")
        # Find the date string in the subDateSpan (e.g., 'Sunday, Jul. 06')
        date_span = html.find("span", {"class": "subDateSpan"})
        flavor_date = None
        if date_span and date_span.text:
            # Parse e.g. 'Sunday, Jul. 06' to '2025-07-06'
            import re

            date_text = date_span.text.strip()
            m = re.search(r"([A-Za-z]+\.?)[,]?\s*(\d{2})", date_text)
            if m:
                month_str, day_str = m.groups()
                month_map = {
                    "Jan.": 1,
                    "Feb.": 2,
                    "Mar.": 3,
                    "Apr.": 4,
                    "May.": 5,
                    "Jun.": 6,
                    "Jul.": 7,
                    "Aug.": 8,
                    "Sep.": 9,
                    "Oct.": 10,
                    "Nov.": 11,
                    "Dec.": 12,
                }
                month = month_map.get(month_str, None)
                if month:
                    # Use US Central time for the year
                    central_now = datetime.datetime.now(ZoneInfo("America/Chicago"))
                    year = central_now.year
                    flavor_date = f"{year:04d}-{month:02d}-{int(day_str):02d}"
        flavor = html.find("span", {"class": "flavorOfDayWhiteSpan"}).string.strip()
        # Grab the description from the .flavorDescriptionSpan
        desc_tag = html.find("span", {"class": "flavorDescriptionSpan"})
        description = desc_tag.get_text(strip=True) if desc_tag else None
        logger.info(
            f"🍨 MURFS: Found flavor: {flavor} for date: {flavor_date} (US Central) desc: {description}"
        )
        return [daily_flavor("Murfs", flavor, description=description, date=flavor_date)]
    except Exception as e:
        logger.error(f"❌ MURFS: Failed to parse flavor: {e}")
        return []
