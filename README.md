# Daily Flavors App 🍦

A web scraper application that collects daily flavor information from frozen custard shops.

## Supported Locations

- **Bubba's Frozen Custard**
- **Culver's**
- **Kopp's Frozen Custard**
- **Oscar's Frozen Custard**
- **Murf's Frozen Custard**


## Quick Start

### Using Docker (Recommended)

```bash
# Clone the repository
git clone <your-repo-url>
cd daily-flavors-app

# Build and run with Docker Compose
docker-compose up --build

# Access the API
curl http://localhost:8080
```

### Local Development

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Chrome and ChromeDriver (for Selenium)
# On macOS with Homebrew:
brew install --cask google-chrome
brew install chromedriver

# Run the application
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```


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
   ```

3. **Encoding issues**
   - Enable debug logging to see detailed encoding attempts
   - The scrapers include multiple encoding fallback strategies

4. **Site structure changes**
   - Enable debug logging to inspect HTML structure
   - Update selectors in the relevant scraper function

