# Quick Start: Moralis API Setup

This guide will help you set up your Moralis API key and start scraping pump.fun data in 5 minutes.

## Step 1: Get Your Moralis API Key

1. Go to [moralis.io](https://moralis.io)
2. Click "Start for Free" and create an account
3. Once logged in, navigate to your dashboard
4. Click on "API Keys" in the left sidebar
5. Create a new API key or copy an existing one
6. Save this key - you'll need it in the next step

## Step 2: Configure Your API Key

### Method 1: Environment Variable (Recommended) ✅

This is the most secure method and recommended for production use.

```bash
# Copy the example .env file
cp .env.example .env

# Edit the .env file with your favorite editor
nano .env

# Add your API key (replace 'your_moralis_api_key_here' with your actual key)
MORALIS_API_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

Save and close the file. Your API key is now configured!

### Method 2: Config File (Alternative)

Edit `config.yaml` and add your API key:

```yaml
moralis_api_key: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

⚠️ **Warning**: Don't commit this file with your API key to git!

### Method 3: Command Line (Temporary)

Pass the API key directly when running:

```bash
python main.py --moralis-key "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

## Step 3: Test Your Setup

Verify everything is working:

```bash
python test_moralis_endpoints.py
```

This will test all 7 Moralis Pump.fun API endpoints and show you what data is available.

Expected output:
```
✓ API Key loaded: eyJhbGci...
============================================================
TEST 1: Get new pump.fun tokens
============================================================
✓ Success! Retrieved 5 tokens
...
✅ All tests passed!
```

## Step 4: Start Scraping!

Run the scraper in continuous mode:

```bash
python main.py
```

The scraper will:
- ✓ Poll for new tokens every 20 seconds
- ✓ Update prices in real-time
- ✓ Save data to `data/` directory
- ✓ Update the dashboard every 20 seconds
- ✓ Run continuously until you press Ctrl+C

## Step 5: View the Dashboard

In a new terminal window, start the dashboard:

```bash
python -m dashboard.app
```

Then open your browser to: http://localhost:5000

You'll see:
- Real-time token listings
- Price updates
- Trading activity
- Charts and statistics

## What Data is Collected?

The scraper collects:

| Data Type | Description |
|-----------|-------------|
| **Token Info** | Name, symbol, mint address |
| **Prices** | Current price, market cap |
| **Metadata** | Description, logo image, social links |
| **Trading** | Swaps, buy/sell transactions |
| **Timestamps** | Launch time, last update |
| **Status** | Bonding curve status, graduated status |

## Troubleshooting

### "MORALIS_API_KEY not set"

Make sure you've set up your API key using one of the methods above. The environment variable method is recommended.

### "HTTP error 401"

Your API key is invalid or expired. Get a new one from [moralis.io](https://moralis.io).

### "HTTP error 429"

You've hit the rate limit. Wait a few minutes or upgrade your Moralis plan for higher limits.

### No data appearing

- Check that your API key is valid
- Make sure there are new tokens being launched on pump.fun
- Check the logs in `logs/scraper.log` for errors

## API Endpoints Reference

All implemented endpoints:

1. **New Tokens** - `/token/mainnet/pumpfun/new`
   - Discovers newly launched tokens

2. **Token Metadata** - `/token/mainnet/{address}/metadata`
   - Gets name, symbol, description, logo

3. **Token Prices** - `/token/mainnet/{address}/price`
   - Gets current price and market data

4. **Token Swaps** - `/token/mainnet/{address}/swaps`
   - Gets trading activity

5. **Graduated Tokens** - `/token/mainnet/pumpfun/graduated`
   - Tokens that completed bonding curve

6. **Bonding Tokens** - `/token/mainnet/pumpfun/bonding`
   - Tokens currently in bonding

7. **Bonding Status** - `/token/mainnet/{address}/bonding-status`
   - Bonding curve progress

## Security Reminders

✅ **DO:**
- Store API key in `.env` file
- Add `.env` to `.gitignore` (already done)
- Use environment variables in production
- Rotate API keys periodically

❌ **DON'T:**
- Commit `.env` to git
- Share your API key publicly
- Hardcode API keys in source code
- Post API keys in issues/forums

## Next Steps

- Read the [full README](README.md) for advanced features
- Check [Moralis documentation](https://docs.moralis.com/web3-data-api/solana/tutorials/) for API details
- Explore the dashboard for data visualization
- Customize `config.yaml` for your needs

---

**Need help?** Check the troubleshooting section in the main README or visit the Moralis documentation.
