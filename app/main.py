# main.py

from contextlib import closing
import datetime
import logging
import time
import random
import requests
import urllib3
import json
import re
import os
import yaml
from zoneinfo import ZoneInfo

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from requests import Session
from requests.exceptions import RequestException
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service

# Constants
USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36'
REQUEST_TIMEOUT = 30
SELENIUM_WAIT_TIMEOUT = 10



def load_config():
    """Load configuration from YAML file or return defaults"""
    config_file = os.path.join(os.path.dirname(__file__), 'config.yaml')
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                return yaml.safe_load(f) or {}
        except (yaml.YAMLError, IOError) as e:
            print(f"Warning: Could not load config file: {e}")
    
    return {}

# FastAPI app
app = FastAPI(title="Wisconsin Daily Flavors API", description="Get daily custard flavors from Wisconsin shops")

# Configure static file serving
static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static')
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Configure logging
config = load_config()

log_level = getattr(logging, config.get('logging', {}).get('root', 'INFO').upper())

logging.basicConfig(
    format='%(asctime)s %(name)s %(levelname)s %(message)s', 
    level=log_level
)
loggers = config.get('logging', {}).get('loggers', {})
for logger_name, logger_level in loggers.items():
    logger = logging.getLogger(logger_name)
    logger.setLevel(getattr(logging, logger_level.upper(), logging.INFO))
logger = logging.getLogger(__name__)

# Optional import for enhanced bot protection bypass
try:
    import undetected_chromedriver as uc
    UC_AVAILABLE = True
    logger.debug("undetected-chromedriver available for enhanced bot protection bypass")
except ImportError:
    UC_AVAILABLE = False
    logger.warning("undetected-chromedriver not available, using standard Selenium only")

# Disable SSL warnings for debugging
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Create persistent session
session = Session()
session.headers.update({'User-Agent': USER_AGENT})


def get_central_time():
    """Get current datetime in US Central Time (America/Chicago)"""
    return datetime.datetime.now(ZoneInfo('America/Chicago'))


def get_central_date_string():
    """Get current date string in US Central Time (YYYY-MM-DD format)"""
    return get_central_time().strftime('%Y-%m-%d')


@app.get("/")
async def root():
    """Redirect to web UI for easier access"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/ui")

@app.get("/ui")
async def web_ui():
    """Serve the web UI"""
    static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static')
    index_file = os.path.join(static_dir, 'index.html')
    
    if os.path.exists(index_file):
        return FileResponse(index_file, media_type='text/html')
    else:
        return {"message": f"Web UI not found. Looking for: {index_file}"}

@app.get("/api/flavors")
async def get_flavors():
    """API endpoint for flavors (alternative to root)"""
    return scrape_all()
  
  
def scrape_all():

    flavors = []
    scrapers = [
        scrape_culvers,
        scrape_kopps,
        scrape_murfs,
        scrape_oscars
    ]
    
    for scraper in scrapers:
        _safe_add_flavors(flavors, scraper)
    
    return flavors


def _safe_add_flavors(flavors, scraper_fn):
    """Safely execute a scraper function and add results to flavors list"""
    try:
        flavors.extend(scraper_fn())
    except Exception as err:
        logger.error(f"Scraping error in {scraper_fn.__name__}", exc_info=err)


def daily_flavor(location, flavor, description=None):
    """Create a standardized flavor dictionary"""
    return {
        'location': location,
        'flavor': flavor,
        'description': description,
        'date': get_central_date_string()
    }

def scrape_culvers():
    """Scrape multiple Culver's locations"""
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
    """Scrape a single Culver's location"""
    html = get_html(url)
    
    # Look for flavor links
    flavor_links = html.find_all('a', href=lambda x: x and '/flavor-of-the-day/' in x)
    for link in flavor_links:
        text = link.get_text().strip()
        if text:  # Found a link with actual flavor text
            # Try to get description from the flavor detail page
            description = "No description available"
            try:
                href = link.get('href', '')
                if href and href.startswith('/'):
                    detail_url = f"https://www.culvers.com{href}"
                    detail_html = get_html(detail_url)
                    if detail_html:
                        # Look for the specific Culver's description div
                        desc_div = detail_html.find('div', class_=lambda x: x and 'FlavorOfTheDayDetails_containerPrimaryContentDescription' in x)
                        if desc_div:
                            desc_text = desc_div.get_text().strip()
                            if desc_text:
                                description = desc_text
                        
                        # Fallback: look for any div with 'description' in the class name
                        if description == "No description available":
                            desc_divs = detail_html.find_all('div', class_=lambda x: x and 'description' in x.lower())
                            for div in desc_divs:
                                desc_text = div.get_text().strip()
                                if desc_text and 30 < len(desc_text) < 400:
                                    description = desc_text
                                    break
            except Exception as e:
                logger.debug(f"Could not fetch description for {text}: {e}")
            
            return text, description
    
    raise Exception("Could not find today's flavor on the page")


def scrape_oscars():
    """Scrape Oscar's Frozen Custard"""
    logger.info("🚀 OSCARS: Starting scrape...")
    chrome_options = _get_chrome_options()
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
        # Find today's date in the calendar (e.g., 'Sun 6')
        today = get_central_time()
        today_day = today.day
        today_weekday = today.strftime("%a")  # e.g., 'Sun'
        today_display = f"{today_weekday} {today_day}"
        # Find the calendar row for today
        calendar_xpath = f"//table//tr[td[contains(text(), '{today_display}')]]"
        calendar_rows = driver.find_elements(By.XPATH, calendar_xpath)
        if not calendar_rows:
            logger.warning(f"OSCARS: Could not find calendar row for {today_display}")
            driver.quit()
            return []
        row = calendar_rows[0]
        # Find the flavor link in the row
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
        # Find the open overlay/modal (look for .divioverlay-open)
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
        # Find the flavor name in <h4>
        flavor_tag = soup.find('h4')
        flavor_name = flavor_tag.get_text(strip=True) if flavor_tag else expected_flavor
        # Find the description: next <span>, <div>, or <p> after <h4>
        description = None
        if flavor_tag:
            # Look for next tag with text
            next_tag = flavor_tag.find_next(['span', 'div', 'p'])
            while next_tag:
                desc_text = next_tag.get_text(strip=True)
                if desc_text and len(desc_text) > 10 and desc_text.upper() != flavor_name.upper():
                    description = desc_text
                    break
                next_tag = next_tag.find_next(['span', 'div', 'p'])
        if not description:
            # Fallback: find the longest <span> or <div> with food words
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
        if 'driver' in locals():
            try:
                driver.quit()
            except:
                pass
        return []


def scrape_kopps():
    """Scrape Kopp's Frozen Custard"""
    logger.info("🚀 KOPPS: Starting scrape...")
    html = get_html('https://www.kopps.com/')
    
    # Look for the "TODAY'S FLAVORS" section using the specific class
    flavors = []
    
    # Find the specific div that contains today's flavors
    flavors_section = html.find('div', class_='wp-block-todays-flavors')
    
    if not flavors_section:
        logger.warning("⚠️ KOPPS: Could not find wp-block-todays-flavors section")
        return flavors
    
    # Find divs with class 'mw-100' which contain the actual flavors
    flavor_divs = flavors_section.find_all('div', class_='mw-100')
    
    for flavor_div in flavor_divs:
        # Find h3 elements within each mw-100 div
        h3_elements = flavor_div.find_all('h3')
        
        for h3 in h3_elements:
            if h3.string:
                flavor_name = h3.string.strip()
                
                # Get the description directly from the p tag under this mw-100 div
                description = ""
                p_tag = flavor_div.find('p')
                if p_tag:
                    desc_text = p_tag.get_text().strip() if p_tag.get_text() else ""
                    if desc_text and len(desc_text) > 5:  # Any reasonable description
                        description = desc_text
                
                # Add the flavor (since we're in mw-100 divs within the flavors section)
                if flavor_name and len(flavor_name) > 2:  # Basic sanity check
                    logger.info(f"🍨 KOPPS: Found flavor: {flavor_name}")
                    flavors.append(daily_flavor('Kopps', flavor_name, description or ""))
    
    if flavors:
        logger.info(f"✅ KOPPS: Completed - found {len(flavors)} flavor(s)")
    else:
        logger.warning("⚠️ KOPPS: No flavors found in today's flavors section")
    
    return flavors


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

def get_html(url, max_retries=3, use_selenium_fallback=True):
    """Get HTML with retry logic, varying strategies, and optional Selenium fallback"""
    for attempt in range(max_retries):
        html = _get_html_attempt(url, attempt)
        if html is not None:
            return html
        
        if attempt < max_retries - 1:
            wait_time = random.uniform(1, 3)
            logger.info(f"Retry {attempt + 1} failed, waiting {wait_time:.1f}s")
            time.sleep(wait_time)
    
    # If all regular attempts failed and Selenium fallback is enabled, try Selenium
    if use_selenium_fallback:
        logger.info("All regular requests failed, trying Selenium fallback...")
        return get_html_selenium(url)
    
    return None


def _get_html_attempt(url, attempt):
    """Single attempt to get HTML with progressive strategies"""
    logger.debug(f"GET {url} (attempt {attempt + 1})")
    
    # Progressive delays
    delay = random.uniform(1.0, 3.0) + (attempt * random.uniform(0.5, 1.5))
    time.sleep(delay)
    
    headers = _get_request_headers(attempt)
    
    try:
        with closing(session.get(url, headers=headers, timeout=REQUEST_TIMEOUT, 
                                allow_redirects=True, stream=False)) as resp:
            logger.debug(f"Response status: {resp.status_code}")
            logger.debug(f"Response encoding: {resp.encoding}")
            logger.debug(f"Response headers: {dict(resp.headers)}")
            
            if resp.status_code == 403:
                logger.warning(f"403 Forbidden on attempt {attempt + 1}")
                return None
            elif _is_valid_response(resp):
                # Parse HTML content
                html = BeautifulSoup(resp.text, 'html.parser')
                return html
            else:
                logger.error(f"Invalid response: status={resp.status_code}")
                return None
    except RequestException as e:
        logger.error(f"Request failed (attempt {attempt + 1}): {e}")
        return None


def _get_request_headers(attempt=0):
    """Generate request headers, varying by attempt to avoid detection"""
    user_agents = [
        USER_AGENT,
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Safari/605.1.15"
    ]
    
    headers = {
        "User-Agent": user_agents[attempt % len(user_agents)],
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",  # Try without brotli on retry
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0",
        "DNT": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none" if attempt == 0 else "cross-site",
        "Sec-Fetch-User": "?1",
        "Accept-Charset": "utf-8, iso-8859-1;q=0.5",
    }
    
    if attempt > 0:
        headers["Referer"] = "https://www.google.com/"
    
    return headers


def _is_valid_response(resp):
    """Check if response is valid HTML"""
    content_type = resp.headers.get('Content-Type', '').lower()
    return (resp.status_code == 200 and 
            content_type is not None and 
            'html' in content_type)

def get_html_selenium(url):
    """Get HTML using Selenium Chrome headless browser"""
    logger.debug("Starting Selenium Chrome browser")
    
    chrome_options = _get_chrome_options()
    
    try:
        # Try to create Chrome driver, fallback to explicit service path if needed
        try:
            driver = webdriver.Chrome(options=chrome_options)
        except Exception:
            service = Service("/usr/local/bin/chromedriver")
            driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Basic anti-detection
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined});'
        })
        
        driver.set_window_size(1920, 1080)
        
        logger.debug(f"Loading {url}")
        driver.get(url)
        
        # Wait for page to load
        WebDriverWait(driver, SELENIUM_WAIT_TIMEOUT).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Wait for dynamic content
        time.sleep(5)
        
        # Check for bot protection and wait if needed
        page_source = driver.page_source.lower()
        if any(indicator in page_source for indicator in ["cloudflare", "access denied", "checking your browser"]):
            logger.warning("Bot protection detected, waiting...")
            time.sleep(15)
        
        final_source = driver.page_source
        logger.debug(f"Retrieved {len(final_source)} characters of HTML")
        
        driver.quit()
        return BeautifulSoup(final_source, 'html.parser')
        
    except Exception as e:
        logger.error(f"Selenium request failed for {url}: {e}")
        if 'driver' in locals():
            try:
                driver.quit()
            except:
                pass
        return None


def get_html_selenium_undetected(url):
    """Get HTML using undetected-chromedriver for better bot protection bypass"""
    if not UC_AVAILABLE:
        logger.debug("Undetected Chrome not available, skipping")
        return None
        
    logger.debug("Starting undetected Chrome browser")
    
    try:
        # Configure undetected Chrome options for Docker environment
        options = uc.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-web-security")
        options.add_argument("--disable-features=VizDisplayCompositor")
        options.add_argument("--single-process")  # For Docker stability
        
        # Create undetected Chrome instance
        driver = uc.Chrome(options=options, version_main=None, driver_executable_path="/usr/local/bin/chromedriver")
        
        logger.debug(f"Loading {url} with undetected Chrome")
        driver.get(url)
        
        # Wait for page load
        WebDriverWait(driver, SELENIUM_WAIT_TIMEOUT).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Wait for dynamic content
        time.sleep(10)
        
        # Get final page content
        final_source = driver.page_source
        logger.debug(f"Retrieved {len(final_source)} characters with undetected Chrome")
        
        driver.quit()
        return BeautifulSoup(final_source, 'html.parser')
        
    except Exception as e:
        logger.error(f"Undetected Chrome request failed for {url}: {e}")
        if 'driver' in locals():
            try:
                driver.quit()
            except:
                pass
        return None

def _get_chrome_options():
    """Configure Chrome options for Selenium"""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(f"--user-agent={USER_AGENT}")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--single-process")
    
    return options



