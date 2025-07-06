# main.py

import logging
import os
import yaml
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.scrapers.culvers import scrape_culvers
from app.scrapers.kopps import scrape_kopps
from app.scrapers.murfs import scrape_murfs
from app.scrapers.oscars import scrape_oscars


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
app = FastAPI(title="Daily Flavors API", description="Get daily custard flavors from shops")

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



