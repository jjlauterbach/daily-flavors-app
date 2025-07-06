import logging
from app.scrapers.utils import get_html, daily_flavor

def scrape_culvers():
    """Scrape multiple Culver's locations"""
    logger = logging.getLogger(__name__)
    logger.info("🚀 CULVERS: Starting scrape of all locations...")
    locations = [
        ('Culvers (Capital)', 'https://www.culvers.com/restaurants/brookfield-capitol'),
        ('Culvers (Waukesha Main St)', 'https://www.culvers.com/restaurants/waukesha-hwy-164'),
        ('Culvers (Waukesha Grandview)', 'https://www.culvers.com/restaurants/waukesha-grandview'),
        ('Culvers (Sussex)', 'https://www.culvers.com/restaurants/sussex')
    ]
    flavors = []
    for name, url in locations:
        try:
            logger.info(f"📍 CULVERS: Scraping {name}...")
            flavor, description = _scrape_culvers_location(url)
            flavors.append(daily_flavor(name, flavor, description))
            logger.info(f"🍨 CULVERS: {name} - {flavor}")
        except Exception as e:
            logger.error(f"❌ CULVERS: Failed to scrape {name}: {e}")
    logger.info(f"✅ CULVERS: Completed - found {len(flavors)} location(s)")
    return flavors

def _scrape_culvers_location(url):
    html = get_html(url)
    flavor_links = html.find_all('a', href=lambda x: x and '/flavor-of-the-day/' in x)
    for link in flavor_links:
        text = link.get_text().strip()
        if text:
            description = "No description available"
            try:
                href = link.get('href', '')
                if href and href.startswith('/'):
                    detail_url = f"https://www.culvers.com{href}"
                    detail_html = get_html(detail_url)
                    if detail_html:
                        desc_div = detail_html.find('div', class_=lambda x: x and 'FlavorOfTheDayDetails_containerPrimaryContentDescription' in x)
                        if desc_div:
                            description = desc_div.get_text().strip()
            except Exception:
                pass
            return text, description
    return "", ""
