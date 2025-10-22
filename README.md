# Pump.fun Python Scraper

A comprehensive Python scraper for collecting data from pump.fun, including token information, transaction data, new token launches, and trading activity with proper rate limiting and error handling.

## Features

- **Multi-source data collection**: Scrapes token info, transactions, new launches, and trading volumes
- **Dual approach**: API calls with web scraping fallback for reliability
- **Bot mitigation**: Browser-backed requests, realistic headers, and adaptive retries to avoid 530/Cloudflare blocks
- **Rate limiting**: Built-in rate limiting to avoid being blocked
- **Multiple output formats**: Saves data in JSON, CSV, and SQLite database
- **Comprehensive logging**: Detailed logging with statistics tracking
- **Error handling**: Robust error handling and retry mechanisms
- **Configurable**: Flexible configuration via YAML file
- **Asynchronous**: Fast async/await implementation
- **Timestamps**: All data includes scraping timestamps
- **Data deduplication**: Prevents duplicate entries

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

### Setup

1. **Clone or download the project**
   ```bash
   git clone <repository-url>
   cd pump-fun-scraper
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Playwright browsers** (for web scraping fallback)
   ```bash
   playwright install chromium
   ```

4. **Create data and logs directories**
   ```bash
   mkdir -p data logs
   ```

## Configuration

The scraper uses a YAML configuration file (`config.yaml`) for settings. Key configuration options:

```yaml
# API Configuration
base_url: "https://pump.fun"
api_base_url: "https://frontend-api.pump.fun"
timeout_seconds: 30
api_page_size: 100

# Optional Headers & Proxy Support
api_extra_headers:
  Sec-Fetch-Dest: "empty"
  Sec-Fetch-Mode: "cors"
  Sec-Fetch-Site: "same-site"
proxy_url: null
playwright_proxy: null

# Rate Limiting
rate_limit_rpm: 30          # Requests per minute
rate_limit_rph: 1000        # Requests per hour
request_delay: 2.0          # Delay between requests

# Scraping Limits
max_tokens: 500             # Maximum tokens to scrape
max_tokens_for_transactions: 50  # Max tokens to get transaction data for
transactions_per_token: 100      # Transactions per token

# Browser Fallback
use_browser_fallback: true
preload_browser_cookies: true
browser_page_settle_delay: 1.5
browser_request_timeout_ms: 30000
cookie_sync_interval: 300

# Output
output_directory: "data"    # Where to save files
output_format: "both"       # json, csv, or both
log_level: "INFO"          # Logging level

# Retry
max_retries: 5
retry_delay: 5.0
max_retry_backoff: 45.0
```

## Usage

### Basic Usage

**Full scraping session** (recommended):
```bash
python main.py
```

**Scrape tokens only**:
```bash
python main.py --tokens-only
```

**Scrape new launches only**:
```bash
python main.py --new-launches
```

**Limit number of tokens**:
```bash
python main.py --max-tokens 100
```

**Use custom config file**:
```bash
python main.py --config my_config.yaml
```

### Command Line Options

- `--config, -c`: Specify configuration file path (default: config.yaml)
- `--tokens-only`: Only scrape token information
- `--transactions-only`: Only scrape transaction data
- `--new-launches`: Only scrape new token launches
- `--max-tokens`: Override maximum number of tokens to scrape

### Programmatic Usage

```python
import asyncio
from config import ScraperConfig
from main import PumpFunScraper

async def scrape_data():
    config = ScraperConfig.load("config.yaml")
    
    async with PumpFunScraper(config) as scraper:
        # Get latest tokens
        tokens = await scraper.get_tokens_api(limit=100)
        
        # Get new launches from last 24 hours
        new_launches = await scraper.get_new_launches(hours=24)
        
        # Get transactions for a specific token
        if tokens:
            transactions = await scraper.get_token_transactions(
                tokens[0].mint_address, limit=50
            )
        
        # Save data
        await scraper.data_storage.save_tokens(tokens)
        await scraper.data_storage.save_new_launches(new_launches)

# Run the scraper
asyncio.run(scrape_data())
```

## Output Data

### Data Formats

The scraper saves data in three formats:

1. **JSON files**: Human-readable, nested structure
2. **CSV files**: Spreadsheet-compatible, flat structure  
3. **SQLite database**: Queryable, relational structure

### File Structure

```
data/
├── tokens/
│   ├── tokens_20231201_143022.json
│   └── tokens_20231201_143022.csv
├── transactions/
│   ├── transactions_20231201_143022.json
│   └── transactions_20231201_143022.csv
├── launches/
│   ├── new_launches_20231201_143022.json
│   └── new_launches_20231201_143022.csv
└── pump_fun_data.db
```

### Sample Data

**Token Information**:
```json
{
  "name": "Sample Token",
  "symbol": "SAMPLE",
  "price": 0.000123,
  "market_cap": 12345.67,
  "volume_24h": 8901.23,
  "created_timestamp": "2023-12-01T14:30:22.123456",
  "mint_address": "ABC123...",
  "description": "A sample token",
  "image_uri": "https://...",
  "twitter": "@sample_token",
  "telegram": "t.me/sample",
  "website": "https://sample.com",
  "scraped_at": "2023-12-01T14:30:22.123456"
}
```

**Transaction Data**:
```json
{
  "signature": "XYZ789...",
  "token_mint": "ABC123...",
  "action": "buy",
  "amount": 1000000.0,
  "price": 0.001,
  "user": "DEF456...",
  "timestamp": "2023-12-01T14:25:10.000000",
  "scraped_at": "2023-12-01T14:30:22.123456"
}
```

## Advanced Features

### Database Queries

The SQLite database allows for complex queries:

```python
import sqlite3

# Connect to database
conn = sqlite3.connect('data/pump_fun_data.db')

# Get tokens by market cap
cursor.execute("""
    SELECT name, symbol, market_cap 
    FROM tokens 
    WHERE market_cap > 10000 
    ORDER BY market_cap DESC
""")

# Get top trading tokens
cursor.execute("""
    SELECT t.name, t.symbol, COUNT(tx.id) as trade_count
    FROM tokens t
    JOIN transactions tx ON t.mint_address = tx.token_mint
    GROUP BY t.mint_address
    ORDER BY trade_count DESC
    LIMIT 10
""")
```

### Custom Rate Limiting

```python
from utils.rate_limiter import AdaptiveRateLimiter

# Create adaptive rate limiter that adjusts based on responses
rate_limiter = AdaptiveRateLimiter(
    requests_per_minute=20,
    requests_per_hour=800
)

# Use with your requests
await rate_limiter.wait_if_needed()
# ... make request ...
await rate_limiter.record_response(status_code, error=False)
```

### Data Export

```python
from utils.data_storage import DataStorage
from datetime import datetime, timedelta

storage = DataStorage("data")

# Export last 7 days of data
start_date = datetime.now() - timedelta(days=7)
end_date = datetime.now()

export_file = await storage.export_data(start_date, end_date, "json")
print(f"Data exported to: {export_file}")
```

## Monitoring & Logging

### Log Files

Logs are saved to `logs/scraper.log` with rotation. Log levels:

- **DEBUG**: Detailed request/response info
- **INFO**: General operations and statistics  
- **WARNING**: Non-critical issues (rate limits, retries)
- **ERROR**: Request failures and exceptions

### Session Statistics

The scraper tracks comprehensive statistics:

```python
# Get current session stats
stats = scraper.logger.get_stats()
print(f"Success Rate: {stats['success_rate']:.1f}%")
print(f"Tokens Scraped: {stats['tokens_scraped']}")
print(f"Requests Made: {stats['requests_made']}")
```

## Error Handling

The scraper includes robust error handling:

- **Network errors**: Automatic retries with exponential backoff
- **Rate limiting**: Adaptive delays when limits are hit
- **API failures**: Automatic fallback to web scraping
- **Data validation**: Pydantic models ensure data quality
- **Graceful degradation**: Continues on non-critical errors

## Security & Best Practices

- **User-Agent rotation**: Mimics real browser requests
- **Rate limiting**: Respects server limits to avoid blocking  
- **Request delays**: Randomized delays between requests
- **Error logging**: Comprehensive error tracking without exposing sensitive data
- **Data validation**: Input sanitization and type checking

## Troubleshooting

### Common Issues

**Issue**: "Rate limit exceeded" or 429 errors
- **Solution**: Increase `request_delay` in config.yaml or reduce `rate_limit_rpm`

**Issue**: "Connection timeout" errors  
- **Solution**: Increase `timeout_seconds` in config.yaml or check internet connection

**Issue**: No data returned from API
- **Solution**: Enable `use_browser_fallback: true` in config for web scraping fallback

**Issue**: Browser automation fails
- **Solution**: Run `playwright install chromium` to install browser

### Debug Mode

Enable debug logging to see detailed request/response information:

```yaml
log_level: "DEBUG"
```

Or run with debug flag:
```bash
python main.py --config config.yaml 2>&1 | tee debug.log
```

## API Endpoints

The scraper uses these pump.fun endpoints:

- **Tokens**: `https://frontend-api.pump.fun/coins`
- **Transactions**: `https://frontend-api.pump.fun/trades/{mint_address}`
- **Web Interface**: `https://pump.fun` (fallback scraping)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality  
4. Submit a pull request

## License

This project is open source. Please use responsibly and respect pump.fun's terms of service.

## Disclaimer

This tool is for educational and research purposes. Users are responsible for complying with pump.fun's terms of service and applicable laws. The authors are not responsible for any misuse or damage caused by this software.