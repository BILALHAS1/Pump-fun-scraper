# Quick Start Guide - Pump.fun Scraper

Get up and running with the pump.fun scraper in minutes!

## 🚀 Installation

### Option 1: Automated Setup (Recommended)
```bash
# Run the setup script
python setup.py
```

### Option 2: Manual Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Install browser for web scraping
python -m playwright install chromium

# Create directories
mkdir -p data logs
```

## ⚡ Quick Usage

### 1. Simple Token Scraping
```bash
# Get 50 tokens quickly (no transactions)
python scrape.py --quick
```

### 2. New Token Launches
```bash
# Check for new tokens launched in last 24 hours
python scrape.py --new-launches
```

### 3. Full Scraping Session
```bash
# Complete scraping with transactions
python scrape.py
```

### 4. Custom Number of Tokens
```bash
# Scrape exactly 100 tokens
python scrape.py --tokens 100
```

## 📊 Check Your Data

After scraping, your data will be in the `data/` directory:

```bash
# View token data
ls data/tokens/

# View JSON output
cat data/tokens/tokens_*.json | head -20

# View CSV output  
head data/tokens/tokens_*.csv
```

## 🔧 Configuration

Edit `config.yaml` to customize:

```yaml
# Basic settings
max_tokens: 500           # How many tokens to scrape
rate_limit_rpm: 30        # Requests per minute (be respectful!)
output_format: "both"     # json, csv, or both

# Rate limiting (adjust if getting blocked)
request_delay: 2.0        # Seconds between requests
rate_limit_rpm: 20        # Reduce if needed
```

## 📈 View Results

The scraper provides immediate feedback:

```
✓ Found and saved 47 new launches

SCRAPING RESULTS SUMMARY
========================
Tokens scraped: 100
Transactions scraped: 2,340
New launches found: 47

Top 5 Tokens by Market Cap:
  1. MegaPump (MEGA) - $1,234,567.89
  2. SafeMoon2 (SAFE2) - $987,654.32
  ...
```

## 🛠️ Troubleshooting

**"No module named 'yaml'"**
```bash
pip install -r requirements.txt
```

**"Rate limit exceeded"**  
- Increase `request_delay` in config.yaml
- Reduce `rate_limit_rpm`

**"No data returned"**
- Check internet connection
- Try: `python scrape.py --no-browser` for API-only mode

## 🎯 What's Next?

1. **Schedule Regular Scraping**: Set up cron jobs
2. **Analyze Data**: Use the SQLite database for queries
3. **Monitor New Launches**: Run with `--new-launches` regularly
4. **Custom Analysis**: Check out `example.py` for code samples

## 📚 More Information

- See `README.md` for detailed documentation
- Run `python scrape.py --help` for all options
- Check `example.py` for programmatic usage examples

---

**Happy Scraping! 🚀**