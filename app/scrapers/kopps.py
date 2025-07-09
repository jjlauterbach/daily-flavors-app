import logging

from app.scrapers.utils import daily_flavor, get_html

logger = logging.getLogger(__name__)


def scrape_kopps():
    """Scrape Kopp's Frozen Custard"""
    logger.info("🚀 KOPPS: Starting scrape...")
    html = get_html("https://www.kopps.com/")
    flavors = []
    flavors_section = html.find("div", class_="wp-block-todays-flavors")
    if not flavors_section:
        logger.warning("⚠️ KOPPS: Could not find wp-block-todays-flavors section")
        return flavors

    # Extract the date from the h2 inside the flavors section
    date_str = None
    heading = flavors_section.find("h2")
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

    # NEW: Find all h3 tags in the flavors_section, regardless of parent
    h3_elements = flavors_section.find_all("h3")
    for h3 in h3_elements:
        flavor_name = h3.get_text(strip=True)
        # Skip section headers like "Shake of the Month" and "Sundae of the Month"
        if any(
            skip in flavor_name.lower() for skip in ["shake of the month", "sundae of the month"]
        ):
            continue
        description = ""
        # Look for the next sibling <p> as the description, but don't require it
        p_tag = h3.find_next_sibling()
        while p_tag and p_tag.name != "p" and p_tag.name is not None:
            p_tag = p_tag.find_next_sibling()
        if p_tag and p_tag.name == "p":
            desc_text = p_tag.get_text().strip() if p_tag.get_text() else ""
            if desc_text and len(desc_text) > 5:
                description = desc_text
        if flavor_name and len(flavor_name) > 2:
            logger.info(f"🍨 KOPPS: Found flavor: {flavor_name}")
            flavors.append(daily_flavor("Kopps", flavor_name, description or "", date_str))
    if flavors:
        logger.info(f"✅ KOPPS: Completed - found {len(flavors)} flavor(s)")
    else:
        logger.warning("⚠️ KOPPS: No flavors found in today's flavors section")
    return flavors
