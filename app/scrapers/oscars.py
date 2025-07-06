import logging
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from app.scrapers.utils import get_central_time, daily_flavor, _get_chrome_options

logger = logging.getLogger(__name__)
SELENIUM_WAIT_TIMEOUT = 10

def scrape_oscars():
    """Scrape Oscar's Frozen Custard"""
    logger.info("🚀 OSCARS: Starting scrape...")
    chrome_options = _get_chrome_options()
    driver = None
    try:
        try:
            driver = webdriver.Chrome(options=chrome_options)
        except Exception:
            service = Service("/usr/local/bin/chromedriver")
            driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined});'
        })
        driver.set_window_size(1920, 1080)
        url = 'https://www.oscarscustard.com/index.php/flavors'
        driver.get(url)
        WebDriverWait(driver, SELENIUM_WAIT_TIMEOUT).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(3)
        today = get_central_time()
        today_day = today.day
        today_weekday = today.strftime("%a")
        today_display = f"{today_weekday} {today_day}"
        calendar_xpath = f"//table//tr[td[contains(text(), '{today_display}')]]"
        calendar_rows = driver.find_elements(By.XPATH, calendar_xpath)
        if not calendar_rows:
            logger.warning(f"OSCARS: Could not find calendar row for {today_display}")
            driver.quit()
            return []
        row = calendar_rows[0]
        flavor_link = None
        for link in row.find_elements(By.TAG_NAME, "a"):
            if link.is_displayed():
                flavor_link = link
                break
        if not flavor_link:
            logger.warning("OSCARS: Could not find flavor link for today")
            driver.quit()
            return []
        expected_flavor = flavor_link.text.strip()
        logger.info(f"OSCARS: Clicking flavor link: {expected_flavor}")
        driver.execute_script("arguments[0].click();", flavor_link)
        time.sleep(2)
        overlay = None
        overlays = driver.find_elements(By.XPATH, "//*[contains(@class, 'divioverlay-open')]")
        for o in overlays:
            if o.is_displayed():
                overlay = o
                break
        if not overlay:
            logger.warning("OSCARS: Could not find open overlay/modal after click")
            driver.quit()
            return []
        overlay_html = overlay.get_attribute("innerHTML")
        soup = BeautifulSoup(overlay_html, 'html.parser')
        flavor_tag = soup.find('h4')
        flavor_name = flavor_tag.get_text(strip=True) if flavor_tag else expected_flavor
        description = ""
        if flavor_tag:
            next_tag = flavor_tag.find_next(['span', 'div', 'p'])
            while next_tag:
                desc_text = next_tag.get_text(strip=True)
                if desc_text and len(desc_text) > 10 and desc_text.upper() != flavor_name.upper():
                    description = desc_text
                    break
                next_tag = next_tag.find_next(['span', 'div', 'p'])
        if not description:
            desc_candidates = []
            for tag in soup.find_all(['span', 'div', 'p']):
                t = tag.get_text(strip=True)
                if t and len(t) > 10 and t.upper() != flavor_name.upper():
                    desc_candidates.append(t)
            if desc_candidates:
                description = max(desc_candidates, key=len)
        driver.quit()
        logger.info(f"OSCARS: Flavor: {flavor_name}")
        logger.info(f"OSCARS: Description: {description}")
        return [daily_flavor('Oscars', flavor_name, description)]
    except Exception as e:
        logger.error(f"OSCARS: Scraper failed: {e}")
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass
        return []
