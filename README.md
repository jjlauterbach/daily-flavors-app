# Daily Flavors App 🍦

A web scraper application that collects daily flavor information from frozen custard shops and displays them in a modern web UI.

## Supported Locations

- **Culver's**
- **Kopp's Frozen Custard**
- **Oscar's Frozen Custard**
- **Murf's Frozen Custard**

## Features
- Robust scrapers for each shop, extracting date, flavor, and description
- Modern UI with date-anchored cards
- Automated tests (unit, integration, and Selenium UI)
- CI/CD with linting, formatting, security, and coverage checks
- Pre-commit hooks for code quality

## Quick Start

### Using Docker (Recommended)

```bash
# Clone the repository
git clone <your-repo-url>
cd daily-flavors-app

# Build and run with Docker Compose
docker-compose up --build

# Access the app in your browser
open http://localhost:8080
```

### Local Development

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install .            # For production
pip install -e .[dev]    # For development/testing (includes test/lint tools)

# Install Chrome and ChromeDriver (for Selenium UI tests)
brew install --cask google-chrome
brew install chromedriver

# Run the application
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

## Testing & Quality

- **Run all tests (including Selenium UI):**
  ```bash
  pytest
  ```
- **Run pre-commit hooks manually:**
  ```bash
  pre-commit run --all-files
  ```
- **Install pre-commit hooks locally:**
  ```bash
  pre-commit install
  ```
- **Lint, format, and security checks:**
  - `flake8`, `black`, `isort`, `autoflake`, `pip-audit` are all run in CI and pre-commit

## Ecosystem Testing

A dedicated ecosystem test suite checks that all scrapers are working against live sites. This is run daily via GitHub Actions and can be run locally:

```bash
pytest --ecosystem
```

- The ecosystem test is skipped by default unless you pass the `--ecosystem` flag.
- The test will fail if any scraper fails to return a valid flavor for today.
- The daily workflow will alert you if a site changes or breaks scraping.

## Continuous Integration

- GitHub Actions workflow runs on PRs and main branch:
  - Linting, formatting, security audit, and test coverage
  - Brings up the app in Docker and runs Selenium UI tests

## Configuration

The application uses a YAML configuration file located at `app/config.yaml`.

### Configuration Options

```yaml
# Logging configuration
logging:
  debug: false  # Enable debug logging
  level: INFO   # Log level (DEBUG, INFO, WARNING, ERROR)

# Scraping configuration
scraping:
  timeout: 30           # HTTP request timeout in seconds
  selenium_timeout: 10  # Selenium wait timeout in seconds
  max_retries: 3        # Maximum retry attempts for failed requests

# Application configuration
app:
  user_agent: "Mozilla/5.0 ..."  # User agent for HTTP requests
```

### Environment Variables

You can also use environment variables to override configuration:

- `DEBUG=true` - Enable debug logging

## Docker Deployment

### Build and Run

```bash
# Build the container
docker build -t daily-flavors-app .

# Run the container
docker run -p 8080:80 daily-flavors-app

# Or use Docker Compose
docker-compose up --build
```

## Troubleshooting

### Common Issues

1. **ChromeDriver not found**
   ```bash
   # Install ChromeDriver manually
   brew install chromedriver  # macOS
   ```

2. **Module import errors**
   ```bash
   # Ensure all dependencies are installed
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

3. **Encoding issues**
   - Enable debug logging to see detailed encoding attempts
   - The scrapers include multiple encoding fallback strategies

4. **Site structure changes**
   - Enable debug logging to inspect HTML structure
   - Update selectors in the relevant scraper function

## Contributing

- Please run pre-commit and all tests before submitting a PR.
- All code is auto-formatted and linted in CI.

