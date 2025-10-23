# Quick Start Guide - Moralis API

Get started with the pump.fun scraper using Moralis API in 5 minutes!

## Prerequisites

- Python 3.8 or higher
- pip package manager

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 2: Get Moralis API Key

1. Visit **https://moralis.io**
2. Click "Start for Free" and create an account
3. Go to your dashboard
4. Navigate to "API Keys" or "Web3 APIs"
5. Create a new API key
6. Copy the API key (keep it secure!)

## Step 3: Configure the Scraper

Edit `config.yaml` and add your API key:

```yaml
# Moralis API Configuration
moralis_api_key: "YOUR_API_KEY_HERE"
use_moralis: true
moralis_poll_interval: 20
```

Or use command line:

```bash
python main.py --moralis-key YOUR_API_KEY_HERE
```

## Step 4: Run the Scraper

**Continuous mode** (recommended):
```bash
python main.py
```

**Timed collection** (5 minutes):
```bash
python main.py --duration 300
```

**Quick test** (2 minutes):
```bash
python scrape.py --moralis-key YOUR_KEY --quick
```

## Step 5: View the Dashboard

Open a new terminal and run:

```bash
python -m dashboard.app
```

Then open your browser to: **http://localhost:5000**

The dashboard will show real-time data as the scraper collects it!

## Output

Data is saved to the `data/` directory in multiple formats:

- **JSON files**: `data/tokens/tokens_*.json`
- **CSV files**: `data/tokens/tokens_*.csv`
- **Database**: `data/pump_fun_data.db`

## Command Line Options

```bash
# Run with specific duration
python main.py --moralis-key YOUR_KEY --duration 600

# Run in verbose mode (see detailed logs)
python main.py --moralis-key YOUR_KEY --verbose

# Collect only new launches
python scrape.py --moralis-key YOUR_KEY --new-launches

# Quick 2-minute collection
python scrape.py --moralis-key YOUR_KEY --quick
```

## Troubleshooting

### "Moralis API key is required"
→ Make sure you've set `moralis_api_key` in `config.yaml` or use `--moralis-key`

### No data appearing
→ Wait at least 20 seconds (default polling interval)
→ Check your internet connection
→ Verify your API key is correct

### Rate limit errors
→ Increase `moralis_poll_interval` in `config.yaml` to 30 or 60 seconds
→ Check your Moralis plan limits at https://moralis.io

## Example Output

```
======================================================================
Pump.fun Scraper - Using Moralis Web3 Data API
======================================================================
Running continuously until stopped (Ctrl+C to exit)...
Dashboard will show coins in real-time as they are scraped.
======================================================================

2024-01-01 12:00:00 - INFO - Initializing Moralis pump.fun scraper...
2024-01-01 12:00:00 - INFO - Using Moralis Web3 Data API for Solana/Pump.fun
2024-01-01 12:00:01 - INFO - Starting continuous data collection...
2024-01-01 12:00:05 - INFO - New token: CoolCoin (COOL) - $0.000123 | MC: $12,345
2024-01-01 12:00:30 - INFO - 📊 Stats - Uptime: 0h 0m 30s | Tokens: 45 | ...
```

Press **Ctrl+C** to stop the scraper gracefully.

## Next Steps

- ✅ Explore the dashboard at http://localhost:5000
- ✅ Check the `data/` directory for output files
- ✅ Review `config.yaml` for more configuration options
- ✅ Read `MORALIS_MIGRATION_GUIDE.md` for advanced usage
- ✅ Check Moralis docs: https://docs.moralis.com/web3-data-api/solana/pump-fun-tutorials

## Need Help?

- **Moralis Documentation**: https://docs.moralis.com
- **Moralis Support**: https://moralis.io/support
- **GitHub Issues**: Report bugs and issues
- **Migration Guide**: See `MORALIS_MIGRATION_GUIDE.md` for detailed info

## Pro Tips

1. **Run continuously**: Let the scraper run 24/7 for comprehensive data
2. **Monitor dashboard**: Keep the dashboard open to watch real-time updates
3. **Check logs**: Look at `logs/scraper.log` for detailed information
4. **Adjust polling**: Increase `moralis_poll_interval` if you hit rate limits
5. **Backup data**: The `data/` directory contains all your collected data

## Legacy PumpPortal Mode

If you prefer to use the old PumpPortal API:

```bash
python main.py --use-pumpportal
```

But Moralis is recommended for better reliability!

---

**Happy scraping! 🚀**
