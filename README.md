# Pump.fun Data Scraper - Moralis API Integration

A comprehensive Python scraper that collects token information, transaction data, new token launches, and trading activity from pump.fun using the **Moralis Web3 Data API** for reliable and professional data access.

## 🚀 Now Using Moralis Web3 Data API

This scraper has been **migrated to use the Moralis API** for better reliability and features:

- **Professional Web3 Data Provider** - Industry-leading API service
- **Reliable Data Access** - Better uptime and data quality
- **Rich Features** - Comprehensive Solana/Pump.fun data endpoints
- **Better Documentation** - Well-documented API with examples
- **Rate Limiting** - Clear limits and professional support

> 📘 **New to Moralis?** Check out our [Quick Start API Setup Guide](QUICKSTART_API_SETUP.md) for a 5-minute setup walkthrough!

### Legacy PumpPortal Support

The scraper still supports the legacy PumpPortal WebSocket API as a fallback option. You can switch between APIs using configuration.

## 🔥 Continuous Real-Time Mode

The scraper runs **continuously** and updates the dashboard in **real-time**:

- **Runs indefinitely** until stopped (no time limits)
- **Saves data every 20 seconds** - dashboard shows coins as they're scraped
- **Live statistics** every 30 seconds showing uptime and collection stats
- **Automatic polling** - regularly fetches latest data from Moralis
- **Graceful shutdown** with Ctrl+C

Just run `python main.py` and watch coins appear on the dashboard in real-time!

## Features

- **Moralis API Integration**: Uses Moralis Web3 Data API for Solana/Pump.fun data
- **Continuous Real-Time Operation**: Runs indefinitely with automatic polling
- **Live Dashboard Integration**: Coins appear on dashboard in real-time as they're scraped
- **Real-time Data**: Regular polling for latest token launches, trades, and market data
- **Multiple Data Types**: Token info, transactions, new launches, trading volumes, timestamps
- **Robust Error Handling**: Automatic retry and error recovery
- **Live Statistics**: Console shows uptime, tokens collected, and API stats every 30s
- **Professional API**: Moralis API key required for reliable data access
- **Multiple Output Formats**: Saves data in JSON, CSV, and SQLite database
- **Comprehensive Logging**: Detailed logging with session statistics
- **Rate Limiting**: Respects API rate limits with proper handling
- **Data Deduplication**: Prevents duplicate entries
- **Legacy Support**: Optional fallback to PumpPortal WebSocket API

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

4. **Get Moralis API Key (Required)**
   - Visit [moralis.io](https://moralis.io) and create a free account
   - Navigate to your dashboard and create a new API key
   - Set up your API key using one of these methods (in order of preference):
     
     **Method 1: Environment Variable (Recommended)**
     ```bash
     # Copy the example .env file
     cp .env.example .env
     
     # Edit .env and add your API key
     # MORALIS_API_KEY=your_actual_api_key_here
     ```
     
     **Method 2: config.yaml file**
     ```yaml
     moralis_api_key: "your_actual_api_key_here"
     ```
     
     **Method 3: Command line flag**
     ```bash
     python main.py --moralis-key YOUR_API_KEY
     ```
   
   - ⚠️ **Never commit your API key to git** - it's already in .gitignore
   - Documentation: https://docs.moralis.com/web3-data-api/solana/pump-fun-tutorials

5. **(Optional) Get PumpPortal API Key for Legacy Mode**
   - Visit [pumpportal.fun](https://pumpportal.fun) to get an API key
   - Add it to your config or use `--api-key` flag (only if using legacy mode)

## Configuration

The scraper uses a YAML configuration file (`config.yaml`) for settings. Key configuration options:

```yaml
# Moralis API Configuration (Primary)
moralis_api_key: null  # REQUIRED - get from https://moralis.io
moralis_base_url: "https://solana-gateway.moralis.io"
use_moralis: true  # Use Moralis API (recommended)
moralis_poll_interval: 20  # Polling interval in seconds

# General Settings
timeout_seconds: 60
api_page_size: 100

# Legacy PumpPortal Configuration (Optional)
api_base_url: "https://pumpportal.fun"
websocket_url: "wss://pumpportal.fun/api/data"
api_key: null  # Only needed for legacy mode

# Output Settings
output_directory: "data"
output_format: "both"  # json, csv, or both
log_level: "INFO"

# Data Collection
max_tokens: 1000
new_launches_hours: 24
```

## Usage

### Basic Usage

**Continuous real-time data collection** (recommended):
```bash
# Make sure to set moralis_api_key in config.yaml first, then:
python main.py
# Runs continuously until stopped with Ctrl+C
# Data is saved every 20 seconds for real-time dashboard updates
```

**With Moralis API key via command line**:
```bash
python main.py --moralis-key YOUR_MORALIS_API_KEY
```

**Custom collection duration** (optional):
```bash
python main.py --duration 600  # Collect for 10 minutes only
```

**Quick collection** (2 minutes):
```bash
python scrape.py --moralis-key YOUR_KEY --quick
```

**New launches only**:
```bash
python scrape.py --moralis-key YOUR_KEY --new-launches
```

**Verbose logging**:
```bash
python scrape.py --moralis-key YOUR_KEY --verbose
```

**Use legacy PumpPortal API** (not recommended):
```bash
python main.py --use-pumpportal --api-key YOUR_PUMPPORTAL_KEY
```

### Testing API Endpoints

To verify your API key is working and test all endpoints:

```bash
python test_moralis_endpoints.py
```

This will test all 7 Moralis Pump.fun API endpoints:
1. Get new pump.fun tokens
2. Get token metadata
3. Get token prices
4. Get token swaps
5. Get graduated tokens
6. Get bonding tokens
7. Get token bonding status

### Command Line Options

- `--config, -c`: Specify configuration file path (default: config.yaml)
- `--duration, -d`: Data collection duration in seconds (default: continuous)
- `--moralis-key`: Moralis API key (overrides config file)
- `--api-key`: PumpPortal API key (only for legacy mode)
- `--use-pumpportal`: Use PumpPortal API instead of Moralis (legacy mode)
- `--new-launches, -n`: Only collect new token launches
- `--quick, -q`: Quick collection (2 minutes)
- `--output, -o`: Output format (json, csv, both)
- `--verbose, -v`: Enable verbose logging (DEBUG level)

### Programmatic Usage

**Using Moralis API** (recommended):
```python
import asyncio
from config import ScraperConfig
from moralis_scraper import MoralisScraper

async def collect_data():
    config = ScraperConfig.load("config.yaml")
    config.moralis_api_key = "your-moralis-api-key-here"  # Required
    
    async with MoralisScraper(config) as scraper:
        # Collect data for 5 minutes
        results = await scraper.collect_data(duration_seconds=300)
        
        print(f"Collected {len(results['tokens'])} tokens")
        print(f"Collected {len(results['transactions'])} transactions")
        print(f"Found {len(results['new_launches'])} new launches")
        
        # Data is automatically saved to configured output directory
        return results

# Run the scraper
asyncio.run(collect_data())
```

**Using PumpPortal API** (legacy):
```python
import asyncio
from config import ScraperConfig
from main import PumpPortalScraper

async def collect_data():
    config = ScraperConfig.load("config.yaml")
    config.use_moralis = False  # Use legacy mode
    
    async with PumpPortalScraper(config) as scraper:
        results = await scraper.collect_data(duration_seconds=300)
        return results

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

### Moralis API (Primary)

The scraper uses the **Moralis Web3 Data API** for Solana/Pump.fun:

- **API Documentation**: https://docs.moralis.com/web3-data-api/solana/pump-fun-tutorials
- **Authentication**: API key in `X-API-Key` header
- **Base URL**: `https://solana-gateway.moralis.io`
- **Rate Limits**: Varies by plan (check Moralis dashboard)

**Available Endpoints** (implemented):
- **New Tokens**: Get newly launched pump.fun tokens
  - Endpoint: `/token/mainnet/pumpfun/new`
  - Documentation: https://docs.moralis.com/web3-data-api/solana/tutorials/get-new-pump-fun-tokens
- **Token Metadata**: Get token name, symbol, description, image
  - Endpoint: `/token/mainnet/{mint_address}/metadata`
  - Documentation: https://docs.moralis.com/web3-data-api/solana/tutorials/get-pump-fun-token-metadata
- **Token Prices**: Get current token prices and market data
  - Endpoint: `/token/mainnet/{mint_address}/price`
  - Documentation: https://docs.moralis.com/web3-data-api/solana/tutorials/get-pump-fun-token-prices
- **Token Swaps**: Get trading activity and swap transactions
  - Endpoint: `/token/mainnet/{mint_address}/swaps`
  - Documentation: https://docs.moralis.com/web3-data-api/solana/tutorials/get-pump-fun-token-swaps
- **Graduated Tokens**: Get tokens that have graduated from bonding curve
  - Endpoint: `/token/mainnet/pumpfun/graduated`
  - Documentation: https://docs.moralis.com/web3-data-api/solana/tutorials/get-graduated-pump-fun-tokens
- **Bonding Tokens**: Get tokens currently in bonding curve
  - Endpoint: `/token/mainnet/pumpfun/bonding`
  - Documentation: https://docs.moralis.com/web3-data-api/solana/tutorials/get-bonding-pump-fun-tokens
- **Bonding Status**: Get bonding curve status for a specific token
  - Endpoint: `/token/mainnet/{mint_address}/bonding-status`
  - Documentation: https://docs.moralis.com/web3-data-api/solana/tutorials/get-token-bonding-status

### Data Collection

- **Polling Mechanism**: Regular API calls at configurable intervals (default: 20s)
- **Data Validation**: Pydantic models ensure data quality
- **Deduplication**: Prevents duplicate tokens and transactions
- **Timestamp Parsing**: Handles multiple timestamp formats
- **Error Recovery**: Automatic retry with backoff
- **Rate Limit Handling**: Respects API limits with proper delays

### Legacy PumpPortal WebSocket (Optional)

If using legacy mode with `--use-pumpportal`:

- **WebSocket Subscriptions**: Real-time streams for new tokens, trades, migrations
- **Auto-reconnection**: Automatic reconnection with exponential backoff
- **Ping/Pong**: Regular ping messages to maintain connection
- **Graceful Shutdown**: SIGINT/SIGTERM signal handling

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

### Moralis API (Recommended)

- **Base URL**: `https://solana-gateway.moralis.io`
- **Documentation**: https://docs.moralis.com/web3-data-api/solana/pump-fun-tutorials
- **Get Started**: https://moralis.io

### PumpPortal API (Legacy)

- **WebSocket API**: `wss://pumpportal.fun/api/data` (real-time data streams)
- **Documentation**: Available at [pumpportal.fun](https://pumpportal.fun)

## Migration Notes

### Migrating from PumpPortal to Moralis

If you're using the old PumpPortal version:

1. **Get Moralis API Key**: Sign up at https://moralis.io and get an API key
2. **Update Configuration**: 
   ```yaml
   moralis_api_key: "YOUR_API_KEY"
   use_moralis: true
   ```
3. **All features maintained**: Token data, prices, market cap, images, timestamps all still work
4. **Better reliability**: More stable API with better documentation
5. **Optional fallback**: Keep PumpPortal as backup by setting `use_moralis: false`

### Changes from Old Scraper Version

If you're upgrading from the old web-scraping version:

1. **API-based**: Now uses professional APIs instead of web scraping
2. **API Key Required**: Moralis API key required for operation
3. **Polling-based**: Uses regular polling instead of WebSocket (more reliable)
4. **Same Output**: All data formats (JSON, CSV, SQLite) remain the same
5. **Same Features**: Dashboard, continuous mode, all features maintained

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality  
4. Submit a pull request

## License

This project is open source. Please use responsibly and respect Moralis and PumpPortal.fun's terms of service.

## API Endpoint Implementation Details

### Moralis Pump.fun API Endpoints

All endpoints are properly implemented according to the official Moralis documentation:

| Endpoint | Purpose | Documentation |
|----------|---------|---------------|
| `/token/mainnet/pumpfun/new` | Get new token launches | [Get New Tokens](https://docs.moralis.com/web3-data-api/solana/tutorials/get-new-pump-fun-tokens) |
| `/token/mainnet/{address}/metadata` | Get token metadata | [Get Metadata](https://docs.moralis.com/web3-data-api/solana/tutorials/get-pump-fun-token-metadata) |
| `/token/mainnet/{address}/price` | Get token prices | [Get Prices](https://docs.moralis.com/web3-data-api/solana/tutorials/get-pump-fun-token-prices) |
| `/token/mainnet/{address}/swaps` | Get token swaps | [Get Swaps](https://docs.moralis.com/web3-data-api/solana/tutorials/get-pump-fun-token-swaps) |
| `/token/mainnet/pumpfun/graduated` | Get graduated tokens | [Get Graduated](https://docs.moralis.com/web3-data-api/solana/tutorials/get-graduated-pump-fun-tokens) |
| `/token/mainnet/pumpfun/bonding` | Get bonding tokens | [Get Bonding](https://docs.moralis.com/web3-data-api/solana/tutorials/get-bonding-pump-fun-tokens) |
| `/token/mainnet/{address}/bonding-status` | Get bonding status | [Get Status](https://docs.moralis.com/web3-data-api/solana/tutorials/get-token-bonding-status) |

### Data Collection Process

1. **Continuous Polling**: Scraper polls every 20 seconds (configurable)
2. **New Token Discovery**: Uses "get new tokens" endpoint to find new launches
3. **Price Updates**: Fetches latest prices for discovered tokens
4. **Metadata Enrichment**: Gets token names, symbols, descriptions, images
5. **Trading Activity**: Collects swap/trade data for active tokens
6. **Real-time Storage**: Saves data every 20 seconds for dashboard updates
7. **Deduplication**: Prevents duplicate entries based on mint addresses

### Security Best Practices

✅ **API Key Storage:**
- ✓ Store in `.env` file (recommended)
- ✓ Use environment variable `MORALIS_API_KEY`
- ✓ Never commit `.env` to git (already in `.gitignore`)
- ✓ Never hardcode API keys in source code

✅ **Configuration Priority:**
1. Environment variable `MORALIS_API_KEY` (highest priority)
2. `config.yaml` file
3. Command line flag `--moralis-key`

## Disclaimer

This tool is for educational and research purposes. Users are responsible for:
- Complying with Moralis API terms of service
- Complying with pump.fun and Solana network policies
- Respecting rate limits and fair usage
- Understanding applicable laws and regulations

The authors are not responsible for any misuse or damage caused by this software.

---

**✨ Now powered by Moralis Web3 Data API for better reliability and features!**