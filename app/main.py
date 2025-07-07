# main.py

import logging
import os
from datetime import datetime

import yaml
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.scrapers.culvers import scrape_culvers
from app.scrapers.kopps import scrape_kopps
from app.scrapers.murfs import scrape_murfs
from app.scrapers.oscars import scrape_oscars


def load_config():
    """Load configuration from YAML file or return defaults"""
    config_file = os.path.join(os.path.dirname(__file__), "config.yaml")
    if os.path.exists(config_file):
        try:
            with open(config_file, "r") as f:
                return yaml.safe_load(f) or {}
        except (yaml.YAMLError, IOError) as e:
            print(f"Warning: Could not load config file: {e}")
    return {}


# FastAPI app
app = FastAPI(title="Daily Flavors API", description="Get daily custard flavors from shops")

# Configure static file serving
static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Configure logging
config = load_config()
log_level = getattr(logging, config.get("logging", {}).get("root", "INFO").upper())
logging.basicConfig(format="%(asctime)s %(name)s %(levelname)s %(message)s", level=log_level)
loggers = config.get("logging", {}).get("loggers", {})
for logger_name, logger_level in loggers.items():
    logger = logging.getLogger(logger_name)
    logger.setLevel(getattr(logging, logger_level.upper(), logging.INFO))
logger = logging.getLogger(__name__)


@app.get("/")
async def root():
    """Redirect to web UI for easier access"""
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url="/ui")


@app.get("/ui")
async def web_ui():
    """Serve the web UI"""
    static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file, media_type="text/html")
    else:
        return {"message": f"Web UI not found. Looking for: {index_file}"}


# Daily cache for flavors
flavors_cache = {"date": None, "data": None}  # YYYY-MM-DD string


@app.get("/api/flavors")
async def get_flavors():
    """API endpoint for flavors (alternative to root) with daily cache"""
    today = datetime.now().strftime("%Y-%m-%d")
    if flavors_cache["date"] == today and flavors_cache["data"] is not None:
        return flavors_cache["data"]
    # Refresh cache
    data = scrape_all()
    flavors_cache["date"] = today
    flavors_cache["data"] = data
    return data


def scrape_all():
    flavors = []
    scrapers = [scrape_culvers, scrape_kopps, scrape_murfs, scrape_oscars]
    for scraper in scrapers:
        _safe_add_flavors(flavors, scraper)
    return flavors


def _safe_add_flavors(flavors, scraper_fn):
    """Safely execute a scraper function and add results to flavors list"""
    try:
        flavors.extend(scraper_fn())
    except Exception as err:
        logger.error(f"Scraping error in {scraper_fn.__name__}", exc_info=err)


def refresh_flavors_cache():
    today = datetime.now().strftime("%Y-%m-%d")
    logger.info(f"Refreshing flavors cache for {today}")
    data = scrape_all()
    flavors_cache["date"] = today
    flavors_cache["data"] = data


# Preload cache on startup
refresh_flavors_cache()


# Schedule daily cache refresh at configured time
def schedule_cache_refresh():
    refresh_time = config.get("cache_refresh_time", "08:00")
    hour, minute = map(int, refresh_time.split(":"))
    scheduler = BackgroundScheduler()
    scheduler.add_job(refresh_flavors_cache, "cron", hour=hour, minute=minute)
    scheduler.start()
    logger.info(f"Scheduled daily cache refresh at {refresh_time}")


schedule_cache_refresh()
