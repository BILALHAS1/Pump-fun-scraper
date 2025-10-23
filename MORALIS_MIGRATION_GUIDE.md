# Moralis API Migration Guide

This guide explains the migration from PumpPortal WebSocket API to Moralis Web3 Data API.

## Overview

The scraper has been migrated to use the **Moralis Web3 Data API** as the primary data source for pump.fun token information. This provides:

- **Better Reliability**: Professional API service with better uptime
- **Richer Data**: Comprehensive Solana/Pump.fun data endpoints
- **Better Documentation**: Well-documented API with examples
- **Clear Rate Limits**: Transparent rate limiting and professional support
- **Established Provider**: Industry-leading Web3 data infrastructure

## What Changed

### API Architecture

**Before (PumpPortal)**:
- WebSocket-based real-time streaming
- `wss://pumpportal.fun/api/data`
- Real-time message processing
- Reconnection handling for WebSocket

**After (Moralis)**:
- REST API with regular polling
- `https://solana-gateway.moralis.io`
- Configurable polling interval (default: 20 seconds)
- Standard HTTP error handling

### Configuration Changes

**New Configuration Options** in `config.yaml`:

```yaml
# Moralis API Configuration (Primary)
moralis_api_key: null  # REQUIRED - get from https://moralis.io
moralis_base_url: "https://solana-gateway.moralis.io"
use_moralis: true  # Set to true to use Moralis API
moralis_poll_interval: 20  # Polling interval in seconds
```

**Legacy Configuration** (still supported):

```yaml
# Legacy PumpPortal API Configuration
api_base_url: "https://pumpportal.fun"
websocket_url: "wss://pumpportal.fun/api/data"
api_key: null  # PumpPortal API key (optional)
```

### Command Line Changes

**New Arguments**:
- `--moralis-key`: Specify Moralis API key
- `--use-pumpportal`: Force use of legacy PumpPortal API

**Example Usage**:
```bash
# Use Moralis (recommended)
python main.py --moralis-key YOUR_MORALIS_KEY

# Use PumpPortal (legacy)
python main.py --use-pumpportal --api-key YOUR_PUMPPORTAL_KEY
```

## Migration Steps

### For New Users

1. **Sign up for Moralis**:
   - Visit https://moralis.io
   - Create a free account
   - Navigate to your dashboard

2. **Get API Key**:
   - In Moralis dashboard, create a new API key
   - Copy the API key

3. **Configure Scraper**:
   - Edit `config.yaml`
   - Set `moralis_api_key: "YOUR_API_KEY"`
   - Ensure `use_moralis: true`

4. **Run Scraper**:
   ```bash
   python main.py
   ```

### For Existing Users (PumpPortal)

1. **Get Moralis API Key** (as above)

2. **Update Configuration**:
   ```yaml
   # Add to your existing config.yaml
   moralis_api_key: "YOUR_MORALIS_API_KEY"
   use_moralis: true
   moralis_poll_interval: 20
   ```

3. **Test Migration**:
   ```bash
   # Run with Moralis
   python main.py --moralis-key YOUR_KEY --duration 60
   
   # Compare with PumpPortal (optional)
   python main.py --use-pumpportal --api-key YOUR_PUMPPORTAL_KEY --duration 60
   ```

4. **Switch Permanently**:
   - Once satisfied, update `config.yaml` with Moralis key
   - Set `use_moralis: true` (default)

### Rollback to PumpPortal

If you need to use PumpPortal API:

```yaml
# config.yaml
use_moralis: false
```

Or via command line:
```bash
python main.py --use-pumpportal
```

## API Comparison

| Feature | Moralis | PumpPortal |
|---------|---------|------------|
| **Connection Type** | REST (polling) | WebSocket (streaming) |
| **Authentication** | API key in header | API key in URL (optional) |
| **Data Freshness** | Polling interval (20s) | Real-time |
| **Reliability** | High (professional API) | Good |
| **Documentation** | Comprehensive | Basic |
| **Rate Limits** | Clear, plan-based | Unspecified |
| **Support** | Professional | Community |
| **Cost** | Free tier + paid plans | Free |

## New Files

### moralis_client.py
HTTP client for Moralis API with:
- Token data fetching
- Trade/transaction data
- New token launches
- Response parsing to data models

### moralis_scraper.py
Main scraper class using Moralis:
- Polling-based data collection
- Same output formats (JSON, CSV, SQLite)
- Same statistics and monitoring
- Continuous mode support

## Maintained Features

All existing features work with Moralis:

✅ **Data Types**:
- Token information (name, symbol, price, market cap)
- Transaction/trade data
- New token launches
- Timestamps and metadata
- Images and social links

✅ **Output Formats**:
- JSON files
- CSV files
- SQLite database

✅ **Operation Modes**:
- Continuous/infinite mode
- Timed collection
- Quick mode
- New launches only

✅ **Dashboard**:
- Real-time updates
- All visualizations
- Same data structure

✅ **Configuration**:
- YAML config file
- Command line arguments
- Programmatic usage

## Code Structure

```
project/
├── moralis_client.py      # New: Moralis API client
├── moralis_scraper.py     # New: Moralis scraper class
├── main.py                # Updated: Now supports both APIs
├── scrape.py              # Updated: CLI for both APIs
├── config.py              # Updated: Moralis config options
├── config.yaml            # Updated: Moralis settings
├── models.py              # Unchanged: Same data models
├── utils/                 # Unchanged: Same utilities
└── dashboard/             # Unchanged: Same dashboard
```

## Troubleshooting

### "Moralis API key is required"

**Problem**: No API key configured

**Solution**:
```yaml
# config.yaml
moralis_api_key: "YOUR_API_KEY"
```

Or:
```bash
python main.py --moralis-key YOUR_API_KEY
```

### "No data received"

**Problem**: API might not be returning data

**Solutions**:
1. Check API key is valid
2. Check Moralis API status
3. Try increasing `moralis_poll_interval`
4. Enable verbose logging: `--verbose`

### "Rate limit exceeded"

**Problem**: Too many API requests

**Solutions**:
1. Increase `moralis_poll_interval` in config
2. Upgrade Moralis plan
3. Check Moralis dashboard for rate limit info

### Want to use PumpPortal

**Solution**:
```bash
python main.py --use-pumpportal
```

## Support

- **Moralis Documentation**: https://docs.moralis.com/web3-data-api/solana/pump-fun-tutorials
- **Moralis Support**: https://moralis.io/support
- **GitHub Issues**: For scraper-specific issues

## API Documentation

### Moralis Endpoints Used

1. **GET /pumpfun/tokens**
   - Get list of pump.fun tokens
   - Parameters: limit, offset, sort_by, order
   - Response: Array of token objects

2. **GET /pumpfun/token/{address}**
   - Get specific token details
   - Parameters: mint address
   - Response: Token object

3. **GET /pumpfun/trades**
   - Get recent trades
   - Parameters: limit, offset, token (optional)
   - Response: Array of trade objects

4. **GET /pumpfun/tokens/new**
   - Get newly created tokens
   - Parameters: limit, from_date
   - Response: Array of token objects

### Response Mapping

Moralis responses are automatically mapped to existing data models:

- `TokenInfo`: name, symbol, price, market_cap, volume_24h, mint_address, etc.
- `TransactionData`: signature, token_mint, action, amount, price, user, timestamp

## Benefits of Migration

1. **Professional API**: Industry-standard Web3 data provider
2. **Better Reliability**: Higher uptime and stability
3. **Comprehensive Data**: Rich metadata and historical data
4. **Clear Documentation**: Well-documented endpoints and responses
5. **Scalability**: Plans for higher usage as needed
6. **Support**: Professional support channels
7. **Future-Proof**: Active development and maintenance

## Backward Compatibility

The scraper maintains full backward compatibility:

- Legacy PumpPortal mode still available
- Same output formats and structure
- Same CLI interface (with new options)
- Same programmatic API
- Existing config files work (with new options added)

## Next Steps

1. ✅ Get Moralis API key
2. ✅ Update configuration
3. ✅ Test with short duration
4. ✅ Verify data quality
5. ✅ Switch to continuous mode
6. ✅ Monitor and optimize

## Questions?

- Check Moralis documentation: https://docs.moralis.com
- Review this guide
- Check GitHub issues
- Contact Moralis support for API-specific questions
