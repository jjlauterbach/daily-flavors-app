import datetime
import logging
import random
import time
from contextlib import closing
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup
from requests.exceptions import RequestException
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# Constants (moved from main.py)
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
REQUEST_TIMEOUT = 30
SELENIUM_WAIT_TIMEOUT = 10

# Session (moved from main.py)
session = requests.Session()
session.headers.update({"User-Agent": USER_AGENT})


def get_central_time():
    return datetime.datetime.now(ZoneInfo("America/Chicago"))


def get_central_date_string():
    return get_central_time().strftime("%Y-%m-%d")


def daily_flavor(location, flavor, description=None, date=None, url=None):
    return {
        "location": location,
        "flavor": flavor,
        "description": description or "",
        "date": date,
        "url": url,
    }


def get_html(url, max_retries=3, use_selenium_fallback=True):
    """Get HTML with retry logic, varying strategies, and optional Selenium fallback"""
    for attempt in range(max_retries):
        html = _get_html_attempt(url, attempt)
        if html is not None:
            return html
        if attempt < max_retries - 1:
            wait_time = random.uniform(1, 3)
            logging.info(f"Retry {attempt + 1} failed, waiting {wait_time:.1f}s")
            time.sleep(wait_time)
    # If all regular attempts failed and Selenium fallback is enabled, try Selenium
    if use_selenium_fallback:
        logging.info("All regular requests failed, trying Selenium fallback...")
        return get_html_selenium(url)
    return None


def _get_html_attempt(url, attempt):
    logging.debug(f"GET {url} (attempt {attempt + 1})")
    delay = random.uniform(1.0, 3.0) + (attempt * random.uniform(0.5, 1.5))
    time.sleep(delay)
    headers = _get_request_headers(attempt)
    try:
        with closing(
            session.get(
                url,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True,
                stream=False,
            )
        ) as resp:
            logging.debug(f"Response status: {resp.status_code}")
            logging.debug(f"Response encoding: {resp.encoding}")
            logging.debug(f"Response headers: {dict(resp.headers)}")
            if resp.status_code == 403:
                logging.warning(f"403 Forbidden on attempt {attempt + 1}")
                return None
            elif _is_valid_response(resp):
                html = BeautifulSoup(resp.text, "html.parser")
                return html
            else:
                logging.error(f"Invalid response: status={resp.status_code}")
                return None
    except RequestException as e:
        logging.error(f"Request failed (attempt {attempt + 1}): {e}")
        return None


def _get_request_headers(attempt=0):
    user_agents = [
        USER_AGENT,
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Safari/605.1.15",
    ]
    headers = {
        "User-Agent": user_agents[attempt % len(user_agents)],
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
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
    content_type = resp.headers.get("Content-Type", "").lower()
    return resp.status_code == 200 and content_type is not None and "html" in content_type


def get_html_selenium(url):
    """Get HTML using Selenium WebDriver"""
    options = _get_chrome_options()
    driver = webdriver.Chrome(options=options)
    driver.get(url)
    time.sleep(3)
    html = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()
    return html


def get_html_selenium_undetected(url):
    """Get HTML using undetected-chromedriver if available, fallback to Selenium otherwise"""
    try:
        import undetected_chromedriver as uc

        options = _get_chrome_options()
        driver = uc.Chrome(options=options)
        driver.get(url)
        time.sleep(3)
        html = BeautifulSoup(driver.page_source, "html.parser")
        driver.quit()
        return html
    except ImportError:
        logging.warning("undetected-chromedriver not available, using standard Selenium")
        return get_html_selenium(url)


def _get_chrome_options():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-browser-side-navigation")
    options.add_argument("--disable-features=VizDisplayCompositor")
    return options
