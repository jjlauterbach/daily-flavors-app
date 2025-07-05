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

# Check for debug config
def load_config():
    """Load configuration from YAML file or return defaults"""
    default_config = {
        'logging': {
            'debug': False,
            'level': 'INFO'
        },
        'scraping': {
            'timeout': 30,
            'selenium_timeout': 10,
            'max_retries': 3
        },
        'app': {
            'user_agent': USER_AGENT
        }
    }
    
    config_file = os.path.join(os.path.dirname(__file__), 'config.yaml')
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                file_config = yaml.safe_load(f) or {}
                # Merge with defaults (file config takes precedence)
                return _merge_config(default_config, file_config)
        except (yaml.YAMLError, IOError) as e:
            print(f"Warning: Could not load config file: {e}")
    
    return default_config

def _merge_config(default, override):
    """Recursively merge configuration dictionaries"""
    result = default.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _merge_config(result[key], value)
        else:
            result[key] = value
    return result

def is_debug_enabled():
    """Check if debug logging is enabled via environment variable or config file"""
    # Check environment variable first (highest priority)
    if os.getenv('DEBUG', '').lower() in ('true', '1', 'yes', 'on'):
        return True
    
    # Check config file
    config = load_config()
    return config.get('logging', {}).get('debug', False)

# FastAPI app
app = FastAPI()

# Configure logging based on config
config = load_config()
debug_enabled = is_debug_enabled()
log_level = logging.DEBUG if debug_enabled else logging.INFO

logging.basicConfig(
    format='%(asctime)s %(name)s %(levelname)s %(message)s', 
    level=log_level
)
logger = logging.getLogger(__name__)
logger.setLevel(log_level)

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
    """Scrape Bubba's Frozen Custard daily flavors using only Selenium"""
    logger.info("🚀 BUBBAS: Starting scrape (Selenium only)...")
    url = 'https://www.bubbasfrozencustard.com/'
    
    # Use only Selenium for Bubba's due to React/PopMenu structure
    html = get_html_selenium(url)
    if html is None:
        logger.error("❌ BUBBAS: Failed to get HTML with Selenium")
        return []

    # Parse modern PopMenu React site structure
    flavors = _parse_bubbas_modern_site(html)
    if not flavors:
        logger.warning("⚠️ BUBBAS: Could not parse any flavors from site")
    else:
        logger.info(f"✅ BUBBAS: Found {len(flavors)} flavor(s)")
    
    return flavors


def _parse_bubbas_modern_site(html):
    """Parse the modern PopMenu React-based site for Bubba's daily flavors"""
    try:
        apollo_state = _extract_apollo_state(html)
        if not apollo_state:
            return []
        
        flavors = []
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        
        # Search for calendar events
        for value in apollo_state.values():
            if not isinstance(value, dict):
                continue
                
            typename = value.get('__typename', '')
            
            # Check calendar events for today's flavor
            if typename == 'CalendarEvent':
                event_date = value.get('eventDate', '')
                if event_date.startswith(today):
                    flavor_name = value.get('name', '')
                    flavor_description = value.get('description', '')
                    if flavor_name:
                        logger.info(f"🍨 BUBBAS: Found today's flavor: {flavor_name}")
                        flavors.append(daily_flavor('Bubbas', flavor_name, flavor_description))
        
        return flavors
        
    except Exception as e:
        logger.error(f"Error parsing modern Bubbas site: {e}")
        return []



def _extract_apollo_state(html):
    """Extract Apollo GraphQL state from HTML scripts"""
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
                return apollo_state
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse Apollo state JSON: {e}")
    
    logger.debug("Could not find or parse Apollo state data")
    return None

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
    
    # Look for today's flavor in the new site structure
    # Try multiple selectors to find the flavor name
    flavor = None
    description = None
    
    # Method 1: Look for flavor links with text content
    flavor_links = html.find_all('a', href=lambda x: x and '/flavor-of-the-day/' in x)
    for link in flavor_links:
        if link.string and link.string.strip():
            flavor = link.string.strip()
            break
    
    # Method 2: Look for h2 headings that might contain flavor names
    if not flavor:
        h2_elements = html.find_all('h2')
        for h2 in h2_elements:
            if h2.string and h2.string.strip() and h2.string.strip() not in ['Closed - Opens 10:00 AM', 'RESTAURANT CALENDAR']:
                text = h2.string.strip()
                # Skip common non-flavor headings
                if not any(skip in text.lower() for skip in ['closed', 'open', 'calendar', 'contact', 'what flavor']):
                    flavor = text
                    break
    
    # Method 3: Look for any element with "Flavor of the Day:" text
    if not flavor:
        flavor_text_elements = html.find_all(text=lambda text: text and 'Flavor of the Day:' in text)
        for element in flavor_text_elements:
            # Find the next sibling or parent that contains the flavor name
            parent = element.parent
            if parent and parent.find('a'):
                link = parent.find('a')
                if link.string:
                    flavor = link.string.strip()
                    break
    
    # If we found a flavor, try to get its description by visiting the flavor detail page
    if flavor:
        try:
            # The flavor links follow a pattern like /flavor-of-the-day/chocolate-heath-crunch
            flavor_slug = flavor.lower().replace(' ', '-').replace('®', '').replace('&', 'and')
            detail_url = f"https://www.culvers.com/flavor-of-the-day/{flavor_slug}"
            detail_html = get_html(detail_url)
            
            if detail_html:
                # Look for description in the detail page
                desc_elements = detail_html.find_all(['p', 'div'], class_=lambda x: x and 'description' in x.lower())
                for elem in desc_elements:
                    if elem.string and len(elem.string.strip()) > 20:  # Reasonable description length
                        description = elem.string.strip()
                        break
                
                # Fallback: look for any paragraph with substantial text
                if not description:
                    paragraphs = detail_html.find_all('p')
                    for p in paragraphs:
                        if p.string and len(p.string.strip()) > 30:
                            description = p.string.strip()
                            break
        except Exception as e:
            logger.debug(f"Could not fetch description for {flavor}: {e}")
    
    if not flavor:
        raise Exception("Could not find today's flavor on the page")
    
    return flavor, description or "No description available"


def scrape_oscars():
    """Scrape Oscar's Frozen Custard"""
    logger.info("🚀 OSCARS: Starting scrape...")
    
    # Try regular requests with improved encoding handling
    html = get_html('https://www.oscarscustard.com/', use_selenium_fallback=False)
    
    # Check if we got valid content
    if html is None:
        logger.warning("⚠️ OSCARS: Regular request failed, will try alternative approach")
        # Try once more with a different user agent or approach
        html = get_html('https://www.oscarscustard.com/', max_retries=1, use_selenium_fallback=False)
    
    if html is None:
        logger.error("❌ OSCARS: Failed to get HTML content")
        return []
    
    # Check if content still looks corrupted
    page_text = html.get_text()
    replacement_char_count = page_text.count('�')
    if replacement_char_count > 50:  # If still very corrupted
        logger.warning(f"⚠️ OSCARS: Content still appears corrupted ({replacement_char_count} replacement chars), but proceeding...")
    
    try:
        # Try multiple methods to find the flavor
        flavor = None
        
        # Method 0: Look for any text containing today's date and a colon (most robust)
        today = datetime.datetime.now()
        date_patterns = [
            today.strftime("%A, %B %d").upper(),  # "SATURDAY, JULY 5"
            today.strftime("%A, %B %-d").upper(), # "SATURDAY, JULY 5" (no leading zero) 
            today.strftime("%A, %B %d"),          # "Saturday, July 5"
            today.strftime("%A, %B %-d"),         # "Saturday, July 5" (no leading zero)
        ]
        
        for pattern in date_patterns:
            # Look for any element containing this date pattern followed by a colon
            elements = html.find_all(text=lambda text: text and pattern in text and ':' in text)
            for element in elements:
                text = element.strip()
                if ':' in text:
                    parts = text.split(':')
                    if len(parts) >= 2:
                        potential_flavor = parts[-1].strip()
                        if potential_flavor:  # Make sure we found something
                            flavor = potential_flavor
                            logger.debug(f"Found flavor via date pattern '{pattern}': {flavor}")
                            break
            if flavor:
                break
        
        # Method 1: Look for h5 elements with flavor information
        h5_elements = html.find_all('h5')
        for h5 in h5_elements:
            text = h5.get_text().strip()
            if text and ':' in text:
                # Format: "SATURDAY, JULY 5: GRASSHOPPER PIE"
                parts = text.split(':')
                if len(parts) >= 2:
                    flavor = parts[-1].strip()
                    logger.debug(f"Found flavor via h5 method: {flavor}")
                    break
        
        # Method 2: Look for any element containing today's date pattern
        if not flavor:
            today = datetime.datetime.now()
            day_patterns = [
                today.strftime("%A, %B %d").upper(),  # "SATURDAY, JULY 5"
                today.strftime("%A, %B %-d").upper(), # "SATURDAY, JULY 5" (no leading zero)
                today.strftime("%A, %B %d"),          # "Saturday, July 5"
                today.strftime("%A, %B %-d"),         # "Saturday, July 5" (no leading zero)
            ]
            
            for pattern in day_patterns:
                elements = html.find_all(text=lambda text: text and pattern in text)
                for element in elements:
                    if ':' in element:
                        parts = element.split(':')
                        if len(parts) >= 2:
                            flavor = parts[-1].strip()
                            break
                if flavor:
                    break
        
        # Method 3: Look for elements with "FLAVOR OF THE DAY" context
        if not flavor:
            flavor_section = html.find(text=lambda text: text and 'FLAVOR OF THE DAY' in text)
            if flavor_section:
                # Look for siblings or nearby elements that might contain the flavor
                parent = flavor_section.parent
                if parent:
                    # Look for h5 elements in the same section
                    nearby_h5 = parent.find_next_siblings('h5')
                    for h5 in nearby_h5[:3]:  # Check first 3 siblings
                        text = h5.get_text().strip()
                        if text and ':' in text:
                            parts = text.split(':')
                            if len(parts) >= 2:
                                flavor = parts[-1].strip()
                                logger.debug(f"Found flavor via nearby h5: {flavor}")
                                break
        
        # Method 4: Look for any h5 element that contains a colon (likely date: flavor format)
        if not flavor:
            h5_elements = html.find_all('h5')
            for h5 in h5_elements:
                if h5.get_text() and ':' in h5.get_text():
                    text = h5.get_text().strip()
                    # Look for patterns like "SATURDAY, JULY 5: GRASSHOPPER PIE"
                    if any(day in text.upper() for day in ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY']):
                        parts = text.split(':')
                        if len(parts) >= 2:
                            flavor = parts[-1].strip()
                            logger.debug(f"Found flavor via day pattern: {flavor}")
                            break
        
        # Method 5: Look for the old selector as a fallback, but more defensively
        if not flavor:
            try:
                flavor_elements = html.select('div .et_pb_text_inner h5')
                for elem in flavor_elements:
                    if elem.get_text() and ':' in elem.get_text():
                        text = elem.get_text().strip()
                        parts = text.split(':')
                        if len(parts) >= 2:
                            flavor = parts[-1].strip()
                            logger.debug(f"Found flavor via old selector: {flavor}")
                            break
            except Exception as e:
                logger.debug(f"Old selector method failed: {e}")
        
        # Method 6: As a last resort, search the raw HTML content for known patterns
        if not flavor:
            try:
                # Get the raw HTML content as a string and search for flavor patterns
                page_html = str(html)
                
                # Look for common flavor names that might be visible even in corrupted content
                common_flavors = [
                    'GRASSHOPPER PIE', 'VANILLA', 'CHOCOLATE', 'STRAWBERRY', 'MINT CHIP',
                    'COOKIES AND CREAM', 'BUTTER PECAN', 'ROCKY ROAD', 'CARAMEL',
                    'PEANUT BUTTER', 'OREO', 'BIRTHDAY CAKE', 'CHERRY', 'LEMON'
                ]
                
                # Look for patterns like ": FLAVOR_NAME" in the raw HTML
                import re
                for flavor_name in common_flavors:
                    # Look for patterns like ": GRASSHOPPER PIE" or ">SATURDAY, JULY 5: GRASSHOPPER PIE<"
                    patterns = [
                        rf':\s*{re.escape(flavor_name)}',
                        rf'JULY\s+5.*?:\s*{re.escape(flavor_name)}',
                        rf'SATURDAY.*?:\s*{re.escape(flavor_name)}',
                    ]
                    
                    for pattern in patterns:
                        matches = re.findall(pattern, page_html, re.IGNORECASE)
                        if matches:
                            flavor = flavor_name
                            logger.debug(f"Found flavor via raw HTML pattern search: {flavor}")
                            break
                    
                    if flavor:
                        break
                        
            except Exception as e:
                logger.debug(f"Raw HTML pattern search failed: {e}")
        
        if flavor:
            logger.info(f"🍨 OSCARS: Found flavor: {flavor}")
            return [daily_flavor('Oscars', flavor)]
        else:
            # Log some debugging info to help understand the page structure
            logger.debug("Could not find flavor. Available h5 elements:")
            h5_elements = html.find_all('h5')
            for i, h5 in enumerate(h5_elements[:10]):  # Log first 10 h5 elements
                text = h5.get_text().strip() if h5.get_text() else 'No text'
                logger.debug(f"  h5[{i}]: '{text}'")
            
            # Also check for any text containing "GRASSHOPPER PIE" or today's date
            logger.debug("Searching for any text containing colon or flavor patterns...")
            all_text_with_colon = html.find_all(text=lambda text: text and ':' in text)
            for i, text in enumerate(all_text_with_colon[:10]):
                cleaned_text = text.strip()
                if cleaned_text:
                    logger.debug(f"  colon_text[{i}]: '{cleaned_text}'")
            
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
