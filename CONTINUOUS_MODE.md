# Continuous Real-Time Scraping Mode

This document explains the continuous real-time scraping functionality implemented in the PumpPortal scraper.

## Overview

The scraper now runs **continuously without time limits** by default, saving data in real-time so the dashboard can display coins as they are scraped.

## Key Changes

### 1. Continuous Operation (No Time Limit)

The scraper now runs indefinitely until manually stopped:

```bash
python main.py  # Runs continuously until Ctrl+C
```

**Previous behavior**: Required a duration (e.g., 20, 60, or 300 seconds)  
**New behavior**: Runs continuously by default, optional `--duration` flag for limited runs

### 2. Real-Time Data Saving

Data is now saved **every 20 seconds** while scraping:

- **Tokens**: Saved to `data/tokens/tokens_YYYYMMDD_HHMMSS.json`
- **Transactions**: Saved to `data/transactions/transactions_YYYYMMDD_HHMMSS.json`
- **New Launches**: Saved to `data/launches/new_launches_YYYYMMDD_HHMMSS.json`

**Previous behavior**: Data only saved when scraping session ended  
**New behavior**: Periodic saves every 20 seconds during scraping

### 3. Live Statistics Logging

The scraper logs live statistics **every 30 seconds**:

```
🔄 LIVE STATS | Uptime: 0:05:30 | Tokens: 42 | Transactions: 156 | New Launches: 8 | Messages: 234 | Connection: ✓ Connected
```

This shows:
- Session uptime
- Total tokens collected
- Total transactions recorded
- New launches discovered
- Messages received from WebSocket
- Connection status

### 4. Infinite Reconnection

The scraper now attempts to reconnect indefinitely if the WebSocket connection drops:

**Previous behavior**: Limited to 5 reconnection attempts  
**New behavior**: Unlimited reconnection attempts with exponential backoff (max 60s delay)

### 5. Graceful Shutdown

The scraper handles Ctrl+C gracefully:

1. Captures SIGINT/SIGTERM signals
2. Stops background tasks
3. Performs final data save
4. Saves session statistics
5. Exits cleanly

## Usage

### Run Continuously (Default)

```bash
python main.py
```

Output:
```
======================================================================
PumpPortal.fun Real-Time Scraper
======================================================================
Running continuously until stopped (Ctrl+C to exit)...
Dashboard will show coins in real-time as they are scraped.
======================================================================

[2024-01-01 12:00:00] INFO - Starting continuous data collection (no time limit)...
[2024-01-01 12:00:30] INFO - 🔄 LIVE STATS | Uptime: 0:00:30 | Tokens: 5 | ...
```

Press **Ctrl+C** to stop gracefully.

### Run with Time Limit (Optional)

```bash
python main.py --duration 600  # Run for 10 minutes only
```

### Run with Dashboard

Terminal 1 - Start scraper:
```bash
python main.py
```

Terminal 2 - Start dashboard:
```bash
python -m dashboard.app
```

Open browser to **http://localhost:5000** and watch coins appear in real-time!

## Dashboard Integration

The dashboard automatically detects new data files and updates every 20 seconds (or 1 second in live mode):

- **Data save interval**: 20 seconds
- **Dashboard refresh**: 20 seconds (default) or 1 second (live mode)
- **New coin detection**: Within 20-30 seconds

This means coins appear on the dashboard within **20-30 seconds** of being scraped.

## Implementation Details

### New Methods

**`_periodic_data_save()`**
- Background task that runs every 20 seconds
- Calls `_save_current_data()` to write files
- Continues until shutdown signal received

**`_save_current_data()`**
- Saves current tokens, transactions, and launches
- Uses timestamped filenames for each save
- Dashboard reads the latest files

**`_periodic_stats_logging()`**
- Background task that runs every 30 seconds
- Logs live statistics to console
- Shows scraper is active and collecting data

### Modified Methods

**`collect_data(duration_seconds=None)`**
- Now accepts `None` for continuous operation
- Starts three background tasks:
  1. Connection maintenance
  2. Periodic data saving
  3. Periodic stats logging
- Waits for shutdown signal or timeout

**`run_full_scrape(duration_seconds=None)`**
- Updated to support continuous mode
- Data saving handled by periodic task
- Final statistics saved on shutdown

**`maintain_connection()`**
- Infinite reconnection attempts (removed limit)
- Exponential backoff with 60s max delay
- Continues until shutdown signal

## Configuration

No configuration changes required for continuous mode. Optional settings:

```yaml
# WebSocket settings
websocket_reconnect_delay: 5.0  # Initial reconnection delay
websocket_ping_interval: 30.0   # Keep-alive ping interval
websocket_timeout: 60.0         # Connection timeout

# Output settings
output_directory: "data"
output_format: "both"  # json, csv, or both
```

## Benefits

1. **Real-time dashboard updates** - Coins appear as they are discovered
2. **No data loss** - Regular saves prevent losing data if scraper crashes
3. **Continuous monitoring** - Scraper can run indefinitely (24/7)
4. **Live feedback** - Console shows activity every 30 seconds
5. **Graceful shutdown** - Clean exit with Ctrl+C
6. **Automatic recovery** - Infinite reconnection on connection loss

## Backwards Compatibility

The `--duration` flag is still supported for limited runs:

```bash
python main.py --duration 300  # Old behavior: run for 5 minutes
```

Existing scripts and workflows continue to work unchanged.

## Testing

Run the test script to verify continuous mode:

```bash
python test_continuous.py
```

Expected output:
```
✅ All tests passed!

The scraper can now:
  • Run continuously without time limits
  • Save data every 20 seconds
  • Log statistics every 30 seconds
  • Stop gracefully on Ctrl+C
```

## FAQ

**Q: How do I stop the scraper?**  
A: Press Ctrl+C. The scraper will shut down gracefully and save all data.

**Q: How often is data saved?**  
A: Every 20 seconds during scraping, plus a final save on shutdown.

**Q: Does the dashboard update automatically?**  
A: Yes, the dashboard refreshes every 20 seconds (or 1 second in live mode) and picks up the latest data files.

**Q: What happens if the connection drops?**  
A: The scraper automatically reconnects indefinitely with exponential backoff.

**Q: Can I still run for a specific duration?**  
A: Yes, use `--duration` flag: `python main.py --duration 600`

**Q: How do I know the scraper is working?**  
A: Check the console for live stats every 30 seconds, or watch the data directory for new files.

## See Also

- **README.md** - Full documentation
- **QUICKSTART.md** - Quick start guide
- **QUICKSTART_REALTIME.md** - Dashboard setup guide
- **REALTIME_DASHBOARD.md** - Dashboard features
