# PumpPortal.fun Official API Python Scraper

A comprehensive Python scraper that uses the **official PumpPortal.fun WebSocket API** to collect real-time token information, transaction data, new token launches, and trading activity with proper error handling and rate limiting.

## 🚀 New: Official API Integration

This scraper has been rebuilt from the ground up to use the **official PumpPortal.fun API** instead of web scraping, providing:

- **Real-time data** via WebSocket connections
- **No 530 errors** - uses official endpoints  
- **Higher reliability** and data accuracy
- **Better performance** with real-time streaming
- **Official API support** with optional API key for enhanced features

## Features

- **Official API Integration**: Uses PumpPortal.fun WebSocket API (`wss://pumpportal.fun/api/data`)
- **Real-time Data Streams**: Live token launches, trades, and migration events
- **Multiple Data Types**: Token info, transactions, new launches, trading volumes, timestamps
- **Robust Connection Management**: Auto-reconnection, error handling, graceful shutdown
- **API Key Support**: Optional API key for enhanced features and higher limits
- **Multiple Output Formats**: Saves data in JSON, CSV, and SQLite database
- **Comprehensive Logging**: Detailed logging with session statistics
- **Configurable Duration**: Set custom data collection periods
- **Rate Limiting**: Built-in rate limiting for WebSocket messages
- **Data Deduplication**: Prevents duplicate entries

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

### Setup

1. **Clone or download the project**
   ```bash
   git clone <repository-url>
   cd pumpportal-scraper
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Create data and logs directories**
   ```bash
   mkdir -p data logs
   ```

4. **(Optional) Get PumpPortal API Key**
   - Visit [pumpportal.fun](https://pumpportal.fun) to get an API key
   - Add it to your config or use `--api-key` flag for enhanced features

## Configuration

The scraper uses a YAML configuration file (`config.yaml`) for settings. Key configuration options:

```yaml
# Official API Configuration
api_base_url: "https://pumpportal.fun"
websocket_url: "wss://pumpportal.fun/api/data"
api_key: null  # Optional - get from pumpportal.fun
timeout_seconds: 60

# WebSocket & Data Collection Settings
websocket_reconnect_attempts: 5
websocket_reconnect_delay: 5.0
websocket_ping_interval: 30.0
websocket_timeout: 60.0
data_collection_duration: 300  # 5 minutes default

# Rate Limiting (for message processing)
rate_limit_rpm: 100    # Messages per minute
rate_limit_rph: 5000   # Messages per hour

# Output Settings
output_directory: "data"
output_format: "both"  # json, csv, or both
log_level: "INFO"
```

## Usage

### Basic Usage

**Real-time data collection** (recommended):
```bash
python main.py
# or
python scrape.py
```

**Custom collection duration**:
```bash
python scrape.py --duration 600  # Collect for 10 minutes
```

**With API key** (for enhanced features):
```bash
python scrape.py --api-key YOUR_API_KEY_HERE
```

**Quick collection** (2 minutes):
```bash
python scrape.py --quick
```

**New launches only**:
```bash
python scrape.py --new-launches
```

**Verbose logging**:
```bash
python scrape.py --verbose
```

### Command Line Options

- `--config, -c`: Specify configuration file path (default: config.yaml)
- `--duration, -d`: Data collection duration in seconds
- `--api-key`: PumpPortal API key for enhanced features
- `--new-launches, -n`: Only collect new token launches
- `--quick, -q`: Quick collection (2 minutes)
- `--output, -o`: Output format (json, csv, both)
- `--verbose, -v`: Enable verbose logging (DEBUG level)

### Programmatic Usage

```python
import asyncio
from config import ScraperConfig
from main import PumpPortalScraper

async def collect_data():
    config = ScraperConfig.load("config.yaml")
    # config.api_key = "your-api-key-here"  # Optional
    
    async with PumpPortalScraper(config) as scraper:
        # Collect real-time data for 5 minutes
        results = await scraper.collect_data(duration_seconds=300)
        
        print(f"Collected {len(results['tokens'])} tokens")
        print(f"Collected {len(results['transactions'])} transactions")
        print(f"Found {len(results['new_launches'])} new launches")
        
        # Data is automatically saved to configured output directory
        return results

# Run the scraper
asyncio.run(collect_data())
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
├── session_stats_20231201_143022.json
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

## Local Dashboard

A local Flask dashboard is included to explore the scraped pump.fun dataset with charts, tables, and summary statistics.

### Quick start

1. Install dependencies (if you have not already):
   ```bash
   pip install -r requirements.txt
   ```
2. (Optional) Point the dashboard at a fresh scrape output. Export either a directory or a single JSON file:
   ```bash
   export PUMP_FUN_DATA_SOURCE=./data                # use the latest files in ./data
   # or
   export PUMP_FUN_DATA_FILE=./data/combined.json    # use a specific JSON file
   ```
3. Launch the dashboard web server:
   ```bash
   python -m dashboard.app
   ```
4. Open your browser to [http://localhost:5000](http://localhost:5000) to view the dashboard.

If no environment variables are provided, the dashboard falls back to the bundled `sample_output.json` dataset so that you can explore the UI immediately.

### Configuration

- `PUMP_FUN_DATA_SOURCE`: Path to a directory containing scraper outputs (JSON/CSV). The dashboard automatically picks the most recent JSON files from `tokens/`, `transactions/`, and `launches/` subdirectories when this is set.
- `PUMP_FUN_DATA_FILE`: Path to a single combined JSON export. Takes precedence over the directory option.
- `PUMP_FUN_REFRESH_SECONDS`: Controls how often the frontend requests updated data (default `30` seconds).

### Dashboard features

- Responsive Bootstrap layout with dark header and light content cards
- Auto-refreshing statistics for token counts, volume, transactions, and top movers
- Searchable and sortable token table with launch timestamps
- Transaction table with action filters and calculated trade values
- Chart.js visualisations for price trend, trading volume split (buy vs sell), and activity timelines
- Timeline view of the most recent token launches with quick links to project resources

## API Integration Details

### WebSocket Subscriptions

The scraper automatically subscribes to these data streams:

- **New Token Events**: `subscribeNewToken` - Real-time token launches
- **Migration Events**: `subscribeMigration` - Token migration to Raydium
- **Token Trade Events**: `subscribeTokenTrade` - Live trading activity
- **Account Trade Events**: `subscribeAccountTrade` - Account-specific trades

### Connection Management

- **Auto-reconnection**: Automatic reconnection with exponential backoff
- **Ping/Pong**: Regular ping messages to maintain connection
- **Graceful Shutdown**: SIGINT/SIGTERM signal handling
- **Error Recovery**: Robust error handling and logging

### Data Processing

- **Real-time Processing**: Messages processed as they arrive
- **Data Validation**: Pydantic models ensure data quality
- **Deduplication**: Prevents duplicate tokens and transactions
- **Timestamp Parsing**: Handles multiple timestamp formats

## Monitoring & Statistics

### Session Statistics

Each scraping session generates comprehensive statistics:

```json
{
  "session_duration": 300.5,
  "messages_received": 1250,
  "connection_errors": 1,
  "reconnection_attempts": 1,
  "tokens_collected": 45,
  "transactions_collected": 892,
  "new_launches": 12,
  "migrations": 3
}
```

### Log Files

Logs are saved to `logs/scraper.log` with rotation. Log levels:

- **DEBUG**: Detailed WebSocket messages and data processing
- **INFO**: General operations, connections, and statistics  
- **WARNING**: Connection issues, reconnections, rate limits
- **ERROR**: Connection failures and processing errors

## Error Handling & Reliability

- **Connection Resilience**: Auto-reconnection with exponential backoff
- **Message Validation**: JSON schema validation for all messages
- **Rate Limiting**: Built-in rate limiting for WebSocket messages
- **Graceful Degradation**: Continues processing despite individual message errors
- **Signal Handling**: Clean shutdown on SIGINT/SIGTERM

## API Rate Limits & Best Practices

- **No Hard Limits**: WebSocket API doesn't have strict rate limits like REST APIs
- **Message Processing**: Built-in rate limiting for processing WebSocket messages
- **Connection Limits**: Respect connection limits (typically 1-5 concurrent per API key)
- **API Key Benefits**: Higher limits and priority access with API key
- **Respectful Usage**: Built-in delays and reconnection backoff

## Troubleshooting

### Common Issues

**Issue**: "WebSocket connection failed"
- **Solution**: Check internet connection, verify WebSocket URL, try with API key

**Issue**: "Connection timeout"  
- **Solution**: Increase `websocket_timeout` in config.yaml

**Issue**: "No data received"
- **Solution**: Ensure data collection duration is sufficient, check verbose logs

**Issue**: "Frequent reconnections"
- **Solution**: Check network stability, consider using API key for priority access

### Debug Mode

Enable debug logging to see detailed WebSocket communication:

```yaml
log_level: "DEBUG"
```

Or run with debug flag:
```bash
python scrape.py --verbose
```

## API Endpoints

The scraper uses the official PumpPortal.fun API:

- **WebSocket API**: `wss://pumpportal.fun/api/data` (real-time data streams)
- **API Documentation**: Available at [pumpportal.fun](https://pumpportal.fun)

## Migration from Old Version

If you're upgrading from the old web-scraping version:

1. **Update configuration**: The new `config.yaml` uses WebSocket settings
2. **API Key**: Get an API key from pumpportal.fun (optional but recommended)
3. **Duration-based**: Set `data_collection_duration` instead of `max_tokens`
4. **Real-time**: Data is collected in real-time streams, not paginated requests

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality  
4. Submit a pull request

## License

This project is open source. Please use responsibly and respect PumpPortal.fun's terms of service.

## Disclaimer

This tool is for educational and research purposes. Users are responsible for complying with PumpPortal.fun's terms of service and applicable laws. The authors are not responsible for any misuse or damage caused by this software.

---

**✨ Now using official PumpPortal.fun API - No more 530 errors!**