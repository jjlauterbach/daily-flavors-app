import logging
from datetime import datetime, timedelta, timezone

import requests

from app.scrapers.utils import daily_flavor

BUBBAS_URL = "https://www.bubbasfrozencustard.com"
BUBBAS_GRAPHQL_ENDPOINT = f"{BUBBAS_URL}/graphql"
BUBBAS_SECTION_ID = 1332549


def scrape_bubbas():
    """Scrape Bubba's flavor of the day using their GraphQL API."""
    logger = logging.getLogger(__name__)
    logger.info("🚀 BUBBAS: Starting scrape via GraphQL API...")
    today = datetime.now(timezone.utc).date()
    # Query a range that includes today
    range_start = today - timedelta(days=1)
    range_end = today + timedelta(days=2)
    payload = {
        "operationName": "customPageCalendarSection",
        "variables": {
            "rangeEndAt": range_end.strftime("%Y-%m-%dT05:00:00.000Z"),
            "rangeStartAt": range_start.strftime("%Y-%m-%dT05:00:00.000Z"),
            "limit": None,
            "sectionId": BUBBAS_SECTION_ID,
        },
        "extensions": {"operationId": "PopmenuClient/84a8c72179c517e7d584420f7a69a194"},
    }
    try:
        logger.debug(f"BUBBAS: Sending payload: {payload}")
        # Add required headers and cookies for authentication
        headers = {
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9",
            "cache-control": "no-cache",
            "content-type": "application/json",
            "dnt": "1",
            "origin": BUBBAS_URL,
            "pragma": "no-cache",
            "referer": f"{BUBBAS_URL}/events",
            "sec-ch-ua": '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
        }
        # NOTE: You must update this cookie string regularly or automate retrieval
        cookies = {
            # Example cookies from your curl; update as needed
            "__cfruid": "4fcaf8ee51daa496562a9d9e12d3d14278c3cc39-1752122336",
            "__cf_bm": "4Auo_PqcKcta.2VQp9IIgOeBaONB6A5cXUWOatpWHfg-1752122226-1.0.1.1-jMtsW.fftTbXaYPCUtZIrRpV1rwxJZZ5S19iXNtg71SwNOSqTbXy3RJ3lkP2NniTttIRsvLYG_hJdPR5XIn72QF.kQ8z6goQxRShhVeoPrg",
            "_popmenu_replica": "b81e7abc1fb67236",
            "_sp_ses.dcd4": "*",
            "_sp_id.dcd4": "2b309d2f-6d06-4de5-b685-52996ab57316.1751170825.6.1752122258.1752119827.087c4023-16e0-4a39-b889-2fa5845ae847",
            "Popmenu-Token": "eyJhbGciOiJIUzI1NiJ9.eyJjcmVhdGVkX2F0IjoiMjAyNS0wNi0yOSAwNDoyMDoyNSBVVEMiLCJkZXZlbG9wZXJfYXBpX292ZXJyaWRlIjpmYWxzZSwiaXNfYXV0aHlfdmVyaWZpZWQiOmZhbHNlLCJpc19wcm90ZWN0ZWRfc2l0ZV9hdXRoZW50aWNhdGVkIjpmYWxzZSwiaXNfc29mdF9hdXRoZW50aWNhdGVkIjpmYWxzZSwibGFzdF92aXNpdF9hdCI6IjIwMjUtMDctMTAgMDQ6Mzc6MzcgVVRDIiwicmVmZXJyZXJfZG9tYWluIjoid3d3LmJ1YmJhc2Zyb3plbmN1c3RhcmQuY29tIiwicmVmZXJyZXJfdXJsIjoiaHR0cHM6Ly93d3cuYnViYmFzZnJvemVuY3VzdGFyZC5jb20iLCJyZXF1ZXN0X2Z1bGxfZG9tYWluIjoid3d3LmJ1YmJhc2Zyb3plbmN1c3RhcmQuY29tIiwicmVzdGF1cmFudF9pZCI6MTA3NzgsInNlc3Npb25faWQiOiI3ZDRhYWNlNi0zNzlmLTRmOTgtOGJjNy01NDQ3NWEzNGI4M2EiLCJzdG9yYWdlIjoie30iLCJ0b2tlbl92ZXJzaW9uIjoiVjMifQ.R5k2z_DGstX6y7w7s_6dKIXoJ4BzmvPztHE3OUWPMjw",
        }
        resp = requests.post(
            BUBBAS_GRAPHQL_ENDPOINT, json=payload, headers=headers, cookies=cookies, timeout=10
        )
        logger.debug(f"BUBBAS: Response status: {resp.status_code}")
        logger.debug(f"BUBBAS: Response text: {resp.text[:1000]}")
        resp.raise_for_status()
        data = resp.json()
        logger.debug(f"BUBBAS: Parsed JSON: {data}")
        events = data.get("data", {}).get("customPageSection", {}).get("upcomingCalendarEvents", [])
        logger.debug(f"BUBBAS: Found {len(events)} events")
        for event in events:
            event_date = event.get("startAt")
            logger.debug(f"BUBBAS: Event: {event}")
            if event_date == today.strftime("%Y-%m-%d"):
                flavor = event.get("name", "")
                description = event.get("description", "")
                date_str = event_date
                url = BUBBAS_URL + event.get("calendarEventPageUrl", "/")
                logger.info(f"🍨 BUBBAS: {flavor} ({date_str})")
                return [daily_flavor("Bubbas", flavor, description, date_str, url=url)]
        logger.warning("BUBBAS: No flavor found for today.")
        return []
    except Exception as e:
        logger.error(f"❌ BUBBAS: Failed to scrape: {e}", exc_info=True)
        return []
