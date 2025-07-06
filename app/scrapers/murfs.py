import logging
from app.scrapers.utils import get_html, daily_flavor

logger = logging.getLogger(__name__)

def scrape_murfs():
    """Scrape Murf's Frozen Custard"""
    logger.info("🚀 MURFS: Starting scrape...")
    try:
        html = get_html('http://www.murfsfrozencustard.com/flavorForecast')
        flavor = html.find('span', {'class': 'flavorOfDayWhiteSpan'}).string.strip()
        logger.info(f"🍨 MURFS: Found flavor: {flavor}")
        return [daily_flavor('Murfs', flavor)]
    except Exception as e:
        logger.error(f"❌ MURFS: Failed to parse flavor: {e}")
        return []
