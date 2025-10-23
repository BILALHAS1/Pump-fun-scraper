# Dashboard Simplification - Changes Summary

## Overview
Fixed the dashboard to display coins correctly and simplified it to show only essential token information with auto-refresh every 5 minutes.

## Changes Made

### 1. Updated Auto-Refresh Interval (dashboard/app.py)
- Changed `DEFAULT_REFRESH_INTERVAL` from 30 seconds to 300 seconds (5 minutes)
- Ensures dashboard automatically refreshes data every 5 minutes as required

### 2. Simplified HTML Template (dashboard/templates/index.html)
**Removed:**
- Complex charts (price trend, volume, activity timeline)
- Transaction tables
- Multiple summary cards
- Search and filter functionality
- All Chart.js and Luxon dependencies (no longer needed)

**Kept/Added:**
- Clean, minimal table layout
- Only 3 columns: Ticker/Name, Price, Market Cap at Start
- Prominent "Auto-refresh: Every 5 minutes" badge
- "Last updated" timestamp with formatting
- Loading state indicator
- Mobile-responsive design

### 3. Simplified JavaScript (dashboard/static/js/dashboard.js)
**Removed:**
- Chart rendering logic
- Complex data filtering and sorting
- Transaction processing
- Multiple state management objects
- Luxon date library dependency

**Implemented:**
- Simple data fetching from `/api/data` endpoint
- Clean table row generation
- 5-minute auto-refresh using `setInterval`
- Real-time "Last updated" timestamp
- Proper currency and market cap formatting
- Error handling with "No data" state

### 4. Added Test Suite (test_dashboard.py)
- Comprehensive test script to verify dashboard functionality
- Tests all required features:
  - Home page loads correctly
  - API endpoint returns data
  - Tokens display with ticker, price, and market cap
  - Auto-refresh is set to 5 minutes (300 seconds)
  - Last updated timestamp is present
  - Healthcheck endpoint works

## Features Verified

✅ **Coins Display**: Dashboard correctly loads and displays coins from data source
✅ **Essential Info Only**: Shows only ticker name, price, and market cap at start
✅ **Auto-Refresh**: Automatically refreshes every 5 minutes (300 seconds)
✅ **Last Updated**: Displays timestamp when data was last refreshed
✅ **Clean UI**: Minimal, focused interface without unnecessary complexity
✅ **Data Source**: Works with sample data and can be configured via environment variables

## Testing

Run the test suite:
```bash
python test_dashboard.py
```

Run the dashboard:
```bash
python -m dashboard.app
```

Then visit: http://127.0.0.1:5000/

## Configuration

The dashboard can be configured with environment variables:
- `PUMP_FUN_DATA_SOURCE`: Path to data file or directory
- `PUMP_FUN_REFRESH_SECONDS`: Override auto-refresh interval (default: 300)
- `PORT`: Server port (default: 5000)

## Data Format

The dashboard expects data in the format returned by the scraper:
```json
{
  "tokens": [
    {
      "symbol": "PUMP",
      "name": "PumpCoin",
      "price": 0.000045,
      "market_cap": 45123.89
    }
  ]
}
```

Falls back to `sample_output.json` if no data source is specified.
