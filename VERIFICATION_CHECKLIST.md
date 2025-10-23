# Verification Checklist: Continuous Real-Time Mode

Use this checklist to verify that the continuous real-time scraping mode is working correctly.

## Prerequisites

- [ ] Python 3.8+ installed
- [ ] Dependencies installed: `pip install -r requirements.txt`
- [ ] Data directory exists: `mkdir -p data`

## Unit Tests

Run the test suite:

```bash
python test_continuous.py
python test_integration.py
python test_startup.py
```

**Expected Results:**
- [ ] All tests pass with ✅ marks
- [ ] No errors or exceptions
- [ ] Methods verified: `_periodic_data_save`, `_periodic_stats_logging`, `_save_current_data`

## Functional Tests

### Test 1: Help Text

```bash
python main.py --help
```

**Expected Results:**
- [ ] Shows "Continuous Real-Time Mode" in description
- [ ] `--duration` flag shows "(default: continuous/infinite)"
- [ ] No errors displayed

### Test 2: Short Run with Duration

```bash
python main.py --duration 10
```

**Expected Results:**
- [ ] Shows startup banner
- [ ] Says "Running for 10 seconds..."
- [ ] Connects to WebSocket
- [ ] Shows "Data collection duration completed" after ~10 seconds
- [ ] Saves data to `data/` directory
- [ ] Shows final statistics
- [ ] Exits cleanly

**Check Data Files:**
```bash
ls -lh data/tokens/
ls -lh data/transactions/
ls -lh data/launches/
```

- [ ] JSON files created with timestamps
- [ ] Files are not empty (may be empty if no data received)

### Test 3: Continuous Mode with Manual Stop

```bash
python main.py --verbose
```

**Wait 30-60 seconds, then press Ctrl+C**

**Expected Results:**
- [ ] Shows "Running continuously until stopped (Ctrl+C to exit)..."
- [ ] Connects to WebSocket successfully
- [ ] Shows live stats every 30 seconds: "🔄 LIVE STATS | Uptime: ..."
- [ ] Shows connection status: "✓ Connected"
- [ ] Responds to Ctrl+C immediately
- [ ] Shows "Scraper stopped gracefully"
- [ ] Saves final data
- [ ] Exits cleanly without errors

**Check Console Output:**
- [ ] See "Starting continuous data collection (no time limit)..."
- [ ] See "🔄 LIVE STATS" messages periodically
- [ ] See "Saved X tokens to disk" in debug messages (if verbose)
- [ ] See "Scraper stopped. Final statistics saved."

### Test 4: Real-Time Dashboard Integration

**Terminal 1:**
```bash
python main.py
```

**Terminal 2:**
```bash
python -m dashboard.app
```

**Browser:**
Open http://localhost:5000

**Expected Results:**
- [ ] Dashboard loads successfully
- [ ] Shows "LIVE" badge at top
- [ ] Connection status is green "Live"
- [ ] Token list is displayed (or "No tokens" if no data yet)
- [ ] "Last updated" timestamp updates every 20 seconds
- [ ] If tokens are being scraped, they appear within 20-30 seconds

**Check Data Files During Run:**

In Terminal 3:
```bash
watch -n 5 'ls -lht data/tokens/ | head -5'
```

- [ ] New files appear every ~20 seconds
- [ ] File timestamps update regularly
- [ ] File sizes increase if data is being collected

### Test 5: Reconnection Handling

**Start scraper, then disconnect internet briefly:**

```bash
python main.py --verbose
```

**Disconnect network for 10 seconds, then reconnect**

**Expected Results:**
- [ ] Shows "WebSocket connection closed" or similar
- [ ] Attempts reconnection: "Reconnection attempt X in Y.Xs"
- [ ] Successfully reconnects after network restored
- [ ] Continues collecting data after reconnection
- [ ] No crashes or unhandled exceptions

### Test 6: Long Run Stability (Optional)

```bash
python main.py > scraper.log 2>&1 &
```

**Let run for 5-10 minutes, then check:**

```bash
tail -f scraper.log
```

**Expected Results:**
- [ ] Still running after 5-10 minutes
- [ ] Regular "🔄 LIVE STATS" messages every 30 seconds
- [ ] Uptime increases correctly
- [ ] Token/transaction counts increase if data is available
- [ ] No memory leaks or crashes
- [ ] Data files continue to update every 20 seconds

**Stop the background scraper:**
```bash
pkill -INT -f "python main.py"
```

## Edge Cases

### Test 7: No API Key

```bash
python main.py --duration 10
```

**Expected Results:**
- [ ] Shows "No API key provided, using public access"
- [ ] Still works and collects data
- [ ] No authentication errors

### Test 8: With API Key

```bash
python main.py --api-key YOUR_KEY --duration 10
```

**Expected Results:**
- [ ] Shows "Using API key for enhanced features"
- [ ] Connects successfully
- [ ] Collects data

### Test 9: Invalid Config

```bash
rm config.yaml
python main.py --duration 5
```

**Expected Results:**
- [ ] Creates default config.yaml
- [ ] Continues with defaults
- [ ] No crashes

## Documentation Verification

- [ ] README.md mentions continuous mode
- [ ] QUICKSTART.md shows continuous usage
- [ ] CONTINUOUS_MODE.md exists and is complete
- [ ] CHANGES.md documents all modifications
- [ ] Help text (`--help`) is accurate

## Final Checklist

- [ ] Scraper runs continuously by default
- [ ] Data saves every 20 seconds
- [ ] Live stats log every 30 seconds
- [ ] Dashboard shows real-time updates
- [ ] Graceful shutdown with Ctrl+C
- [ ] Infinite reconnection on connection loss
- [ ] All tests pass
- [ ] Documentation updated
- [ ] No breaking changes to existing functionality

## Success Criteria

✅ All checkboxes above should be checked  
✅ No errors or exceptions during testing  
✅ Dashboard shows coins in real-time  
✅ Scraper runs until manually stopped  
✅ Data persists and updates continuously

## Troubleshooting

If any tests fail, check:

1. **Dependencies**: `pip install -r requirements.txt`
2. **Python version**: `python --version` (should be 3.8+)
3. **Network**: Can you access https://pumpportal.fun?
4. **Firewall**: WebSocket connections allowed?
5. **Disk space**: Enough space for data files?
6. **Port 5000**: Available for dashboard?

## Report Issues

If you find any issues:

1. Note which test failed
2. Copy error messages
3. Include Python version and OS
4. Check logs in `scraper.log`
5. Review `data/` directory contents
