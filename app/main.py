# main.py

from contextlib import closing
import datetime
import logging
import time
import random
import urllib3
import json
import re
import os
import yaml

from fastapi import FastAPI
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
app = FastAPI()

# Configure logging
config = load_config()

# Set log level: DEBUG env var overrides config file
log_level = logging.DEBUG if os.getenv('DEBUG', '').lower() in ('true', '1', 'yes', 'on') else \
            getattr(logging, config.get('logging', {}).get('level', 'INFO').upper(), logging.INFO)

logging.basicConfig(
    format='%(asctime)s %(name)s %(levelname)s %(message)s', 
    level=log_level
)
logger = logging.getLogger(__name__)

# Disable SSL warnings for debugging
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Create persistent session
session = Session()
session.headers.update({'User-Agent': USER_AGENT})


@app.get("/")
async def root():
    return scrape_all()
  
  
def scrape_all():

    flavors = []
    scrapers = [
        scrape_bubbas,
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
        'date': datetime.datetime.today().strftime('%Y-%m-%d')
    }

    

def scrape_bubbas():
    """Scrape Bubba's Frozen Custard daily flavors using Selenium"""
    logger.info("🚀 BUBBAS: Starting scrape...")
    url = 'https://www.bubbasfrozencustard.com/'
    
    # Use Selenium for Bubba's because its using bot detection
    html = get_html_selenium(url)
    if html is None:
        logger.error("❌ BUBBAS: Failed to get HTML with Selenium")
        return []

    try:
        # Extract Apollo GraphQL state from HTML scripts
        apollo_state = None
        scripts = html.find_all('script')
        
        for script in scripts:
            if not script.string or 'window.POPMENU_APOLLO_STATE' not in script.string:
                continue
                
            # Extract JSON from JavaScript assignment
            match = re.search(r'window\.POPMENU_APOLLO_STATE\s*=\s*({.*?});', 
                             script.string, re.DOTALL)
            if match:
                try:
                    apollo_state = json.loads(match.group(1))
                    logger.debug("Successfully parsed Apollo state JSON")
                    break
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse Apollo state JSON: {e}")
        
        if not apollo_state:
            logger.debug("Could not find or parse Apollo state data")
            return []
        
        # Search for today's flavor in calendar events
        flavors = []
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        
        for value in apollo_state.values():
            if not isinstance(value, dict):
                continue
                
            # Check calendar events for today's flavor
            if value.get('__typename') == 'CalendarEvent':
                event_date = value.get('eventDate', '')
                if event_date.startswith(today):
                    flavor_name = value.get('name', '')
                    flavor_description = value.get('description', '')
                    if flavor_name:
                        logger.info(f"🍨 BUBBAS: Found today's flavor: {flavor_name}")
                        flavors.append(daily_flavor('Bubbas', flavor_name, flavor_description))
        
        if not flavors:
            logger.warning("⚠️ BUBBAS: Could not parse any flavors from site")
        else:
            logger.info(f"✅ BUBBAS: Found {len(flavors)} flavor(s)")
        
        return flavors
        
    except Exception as e:
        logger.error(f"❌ BUBBAS: Error parsing site: {e}")
        return []

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
    
    html = get_html('https://www.oscarscustard.com/', use_selenium_fallback=False)
    if html is None:
        logger.error("❌ OSCARS: Failed to get HTML content")
        return []
    
    try:
        # Generate today's date patterns for matching
        today = datetime.datetime.now()
        date_patterns = [
            today.strftime("%A, %B %d").upper(),   # "SATURDAY, JULY 5"
            today.strftime("%A, %B %-d").upper(),  # "SATURDAY, JULY 5" (no leading zero)
            today.strftime("%A, %B %d"),           # "Saturday, July 5"
            today.strftime("%A, %B %-d"),          # "Saturday, July 5" (no leading zero)
        ]
        
        # Primary method: Look for h5 elements with date/flavor format
        h5_elements = html.find_all('h5')
        for h5 in h5_elements:
            text = h5.get_text().strip()
            if not text or ':' not in text:
                continue
                
            # Check if this h5 contains today's date pattern
            for pattern in date_patterns:
                if pattern in text:
                    parts = text.split(':')
                    if len(parts) >= 2:
                        flavor = parts[-1].strip()
                        if flavor:
                            logger.info(f"🍨 OSCARS: Found flavor: {flavor}")
                            return [daily_flavor('Oscars', flavor)]
        
        # Fallback method: Look for any text containing today's date and a colon
        for pattern in date_patterns:
            elements = html.find_all(text=lambda text: text and pattern in text and ':' in text)
            for element in elements:
                text = element.strip()
                if ':' in text:
                    parts = text.split(':')
                    if len(parts) >= 2:
                        flavor = parts[-1].strip()
                        if flavor:
                            logger.info(f"🍨 OSCARS: Found flavor: {flavor}")
                            return [daily_flavor('Oscars', flavor)]
        
        # If we reach here, no flavor was found
        logger.debug("Could not find today's flavor. Available h5 elements:")
        for i, h5 in enumerate(h5_elements[:5]):
            text = h5.get_text().strip() if h5.get_text() else 'No text'
            logger.debug(f"  h5[{i}]: '{text}'")
        
        raise Exception("Could not find today's flavor on the page")
        
    except Exception as e:
        logger.error(f"❌ OSCARS: Failed to parse flavor: {e}")
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
        service = Service("/usr/local/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Remove webdriver property to avoid detection
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        logger.debug(f"Loading {url}")
        driver.get(url)
        
        # Wait for page to load
        WebDriverWait(driver, SELENIUM_WAIT_TIMEOUT).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Log page info
        title = driver.title
        logger.debug(f"Page title: {title}")
        
        # Check for bot detection
        page_source = driver.page_source.lower()
        if any(term in page_source for term in ["cloudflare", "access denied", "forbidden"]):
            logger.warning("Detected bot protection page")
        
        # Wait for dynamic content
        time.sleep(random.uniform(3, 6))
        
        # Wait for specific content to load
        try:
            WebDriverWait(driver, SELENIUM_WAIT_TIMEOUT).until(
                lambda d: (d.find_elements(By.CLASS_NAME, "pm-calendar-events") or 
                          "flavor" in d.page_source.lower() or
                          d.find_elements(By.TAG_NAME, "h1"))
            )
            logger.debug("Page content loaded successfully")
        except:
            logger.warning("Timeout waiting for page content")
        
        html_content = driver.page_source
        logger.debug(f"Retrieved {len(html_content)} characters")
        
        driver.quit()
        return BeautifulSoup(html_content, 'html.parser')
        
    except Exception as e:
        logger.error(f"Selenium request failed for {url}: {e}")
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
    options.add_argument("--remote-debugging-port=9222")
    return options
