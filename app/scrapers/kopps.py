import logging
from app.scrapers.utils import get_html, daily_flavor

logger = logging.getLogger(__name__)

def scrape_kopps():
    """Scrape Kopp's Frozen Custard"""
    logger.info("🚀 KOPPS: Starting scrape...")
    html = get_html('https://www.kopps.com/')
    flavors = []
    flavors_section = html.find('div', class_='wp-block-todays-flavors')
    if not flavors_section:
        logger.warning("⚠️ KOPPS: Could not find wp-block-todays-flavors section")
        return flavors

    # Extract the date from the h2 inside the flavors section
    date_str = None
    heading = flavors_section.find('h2')
    if heading and heading.text:
        import re
        # Accept various apostrophes and whitespace
        match = re.search(r"TODAY[’'`sS]* FLAVORS\s*[–-]\s*(.+)", heading.text, re.IGNORECASE)
        if match:
            date_str = match.group(1).strip()
            logger.info(f"📅 KOPPS: Found date: {date_str}")
        else:
            logger.warning(f"⚠️ KOPPS: Could not extract date from heading text: {heading.text}")
    else:
        logger.warning("⚠️ KOPPS: Could not find heading for today's flavors")

    flavor_divs = flavors_section.find_all('div', class_='mw-100')
    for flavor_div in flavor_divs:
        h3_elements = flavor_div.find_all('h3')
        for h3 in h3_elements:
            if h3.string:
                flavor_name = h3.string.strip()
                description = ""
                p_tag = flavor_div.find('p')
                if p_tag:
                    desc_text = p_tag.get_text().strip() if p_tag.get_text() else ""
                    if desc_text and len(desc_text) > 5:
                        description = desc_text
                if flavor_name and len(flavor_name) > 2:
                    logger.info(f"🍨 KOPPS: Found flavor: {flavor_name}")
                    flavors.append(daily_flavor('Kopps', flavor_name, description or "", date_str))
    if flavors:
        logger.info(f"✅ KOPPS: Completed - found {len(flavors)} flavor(s)")
    else:
        logger.warning("⚠️ KOPPS: No flavors found in today's flavors section")
    return flavors
