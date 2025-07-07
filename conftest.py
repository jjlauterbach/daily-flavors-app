# pytest plugin to bring up the app in Docker before running tests
import subprocess
import time

import requests

TIMEOUT = 60  # seconds


def pytest_sessionstart(session):
    # Start docker-compose up in detached mode
    subprocess.run(["docker-compose", "up", "--build", "-d"], check=True)
    # Wait for the app to be ready
    url = "http://localhost:8080/"
    print(f"Waiting up to {TIMEOUT} sec for app to start at {url}...")
    try:
        for _ in range(TIMEOUT):
            try:
                r = requests.get(url, timeout=2)
                if r.status_code == 200:
                    print(f"App is up and running at {url}")
                    break
            except Exception:
                pass
            time.sleep(1)
        else:
            raise RuntimeError("App did not start in Docker within timeout")
    except Exception:
        # Always tear down docker-compose if startup fails
        subprocess.run(["docker-compose", "down"], check=False)
        raise


def pytest_sessionfinish(session, exitstatus):
    # Tear down docker-compose after tests
    subprocess.run(["docker-compose", "down"], check=False)
