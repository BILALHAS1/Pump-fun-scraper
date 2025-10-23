# 🚀 Quick Start Guide - PumpPortal.fun Official API

Get up and running with the official PumpPortal.fun API in under 5 minutes!

## ⚡ One-Minute Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the scraper (runs continuously)
python main.py

# 3. Check your data (in another terminal)
ls data/
```

That's it! You'll start collecting real-time pump.fun data immediately. Press Ctrl+C to stop.

## 📋 What Just Happened?

- ✅ Connected to official PumpPortal.fun WebSocket API
- ✅ Started collecting real-time token launches, trades, and migrations
- ✅ Data saved to `data/` directory in JSON, CSV, and SQLite formats
- ✅ No 530 errors or rate limiting issues!

## 🎛️ Common Commands

```bash
# Run continuously (default - press Ctrl+C to stop)
python main.py

# Collect for specific duration (optional)
python main.py --duration 600  # 10 minutes only

# With API key (recommended)
python main.py --api-key YOUR_API_KEY

# Verbose logging
python main.py --verbose

# Dashboard (view data in real-time)
python dashboard/app.py
```

## 📁 Output Files

After running, check these files:

```
data/
├── tokens_YYYYMMDD_HHMMSS.json     # Token information
├── transactions_YYYYMMDD_HHMMSS.json  # Trade data
├── new_launches_YYYYMMDD_HHMMSS.json  # New tokens
├── session_stats_YYYYMMDD_HHMMSS.json # Statistics
└── pump_fun_data.db                # SQLite database
```

## 🔑 Get an API Key (Optional)

1. Visit [pumpportal.fun](https://pumpportal.fun)
2. Sign up and get your API key
3. Add to config: `api_key: "your-key-here"`
4. Enjoy enhanced features and higher limits!

## 🎯 What You Can Collect

- **🪙 Token Information**: Names, prices, market caps, metadata
- **💱 Real-time Trades**: Buy/sell transactions as they happen
- **🚀 New Launches**: Token creations in real-time
- **📈 Migration Events**: Tokens moving to Raydium
- **📊 Statistics**: Session stats and performance metrics

## ⚙️ Configuration

Edit `config.yaml` to customize:

```yaml
# Your API key (optional)
api_key: "your-api-key-here"

# Output format
output_format: "both"  # json, csv, or both

# Logging level
log_level: "INFO"  # DEBUG for more details

# WebSocket settings
websocket_reconnect_delay: 5.0
websocket_ping_interval: 30.0
```

## 🐛 Troubleshooting

**No data received?**
- Make sure you have internet connection
- Try with `--verbose` flag to see detailed logs
- Ensure firewall allows WebSocket connections

**Connection issues?**
- Check if you can access https://pumpportal.fun
- Try with an API key for priority access
- Increase timeout in config.yaml

**Need help?**
- Check the full README.md
- Run `python scrape.py --help`
- Enable debug logging: `--verbose`

## 🎓 Next Steps

1. **Run Examples**: `python example.py` for guided examples
2. **Read Full Docs**: Check README.md for advanced features
3. **Customize**: Modify config.yaml for your needs
4. **Integrate**: Use the Python API in your own scripts

## 💡 Pro Tips

- Use `--api-key` for best performance
- Run continuously for real-time data feeds
- Open dashboard while scraper is running to see live updates
- Check session stats for connection quality
- Press Ctrl+C to stop gracefully

---

**Happy scraping! 🎉 No more 530 errors with the official API!**