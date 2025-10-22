#!/usr/bin/env python3
"""
Simple CLI interface for the pump.fun scraper
"""

import asyncio
import argparse
import sys
from pathlib import Path

from config import ScraperConfig
from main import PumpFunScraper


def main():
    parser = argparse.ArgumentParser(
        description="Pump.fun Data Scraper - Simple CLI Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scrape.py                    # Run full scrape with default config
  python scrape.py --tokens 100      # Scrape 100 tokens only
  python scrape.py --new-launches    # Get new launches from last 24 hours
  python scrape.py --quick           # Quick scrape (50 tokens, no transactions)
  python scrape.py --config my.yaml  # Use custom configuration file
        """
    )
    
    parser.add_argument(
        "--config", "-c",
        default="config.yaml",
        help="Configuration file path (default: config.yaml)"
    )
    
    parser.add_argument(
        "--tokens", "-t",
        type=int,
        help="Number of tokens to scrape (overrides config)"
    )
    
    parser.add_argument(
        "--new-launches", "-n",
        action="store_true",
        help="Only scrape new token launches from last 24 hours"
    )
    
    parser.add_argument(
        "--quick", "-q",
        action="store_true",
        help="Quick scrape: 50 tokens, no transactions (faster)"
    )
    
    parser.add_argument(
        "--output", "-o",
        choices=["json", "csv", "both"],
        help="Output format (overrides config)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging (DEBUG level)"
    )
    
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Disable browser fallback (API only)"
    )
    
    args = parser.parse_args()
    
    # Check if config file exists
    if not Path(args.config).exists():
        print(f"Error: Configuration file '{args.config}' not found.")
        print("Run the main scraper first to create a default config file.")
        sys.exit(1)
    
    # Load and modify configuration based on arguments
    try:
        config = ScraperConfig.load(args.config)
    except Exception as e:
        print(f"Error loading configuration: {e}")
        sys.exit(1)
    
    # Apply command line overrides
    if args.tokens:
        config.max_tokens = args.tokens
        print(f"Set max tokens to: {args.tokens}")
    
    if args.output:
        config.output_format = args.output
        print(f"Set output format to: {args.output}")
    
    if args.verbose:
        config.log_level = "DEBUG"
        print("Enabled verbose logging")
    
    if args.no_browser:
        config.use_browser_fallback = False
        print("Disabled browser fallback")
    
    if args.quick:
        config.max_tokens = 50
        config.max_tokens_for_transactions = 0  # No transactions in quick mode
        config.transactions_per_token = 0
        print("Quick mode: 50 tokens, no transactions")
    
    # Run the scraper
    try:
        asyncio.run(run_scraper(config, args))
    except KeyboardInterrupt:
        print("\nScraping interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Error during scraping: {e}")
        sys.exit(1)


async def run_scraper(config: ScraperConfig, args):
    """Run the scraper with given configuration and arguments"""
    
    async with PumpFunScraper(config) as scraper:
        print(f"Starting pump.fun scraper...")
        print(f"Output directory: {config.output_directory}")
        print(f"Output format: {config.output_format}")
        print(f"Rate limit: {config.rate_limit_rpm} requests/minute")
        print("-" * 50)
        
        if args.new_launches:
            # Only scrape new launches
            print("Scraping new token launches from last 24 hours...")
            new_launches = await scraper.get_new_launches(hours=24)
            
            if new_launches:
                await scraper.data_storage.save_new_launches(new_launches)
                print(f"✓ Found and saved {len(new_launches)} new launches")
                
                # Print summary of new launches
                print("\nNew Launches Summary:")
                for launch in new_launches[:5]:  # Show first 5
                    print(f"  • {launch.name} ({launch.symbol}) - ${launch.price:.6f}")
                
                if len(new_launches) > 5:
                    print(f"  ... and {len(new_launches) - 5} more")
            else:
                print("No new launches found in the last 24 hours")
        
        else:
            # Full or quick scrape
            print("Running comprehensive scrape...")
            results = await scraper.run_full_scrape()
            
            # Print results summary
            print("\n" + "=" * 50)
            print("SCRAPING RESULTS SUMMARY")
            print("=" * 50)
            
            print(f"Tokens scraped: {len(results['tokens'])}")
            print(f"Transactions scraped: {len(results['transactions'])}")
            print(f"New launches found: {len(results['new_launches'])}")
            
            if results['tokens']:
                # Token statistics
                market_caps = [t.market_cap for t in results['tokens'] if t.market_cap > 0]
                if market_caps:
                    avg_market_cap = sum(market_caps) / len(market_caps)
                    print(f"Average market cap: ${avg_market_cap:,.2f}")
                    print(f"Highest market cap: ${max(market_caps):,.2f}")
                
                # Show top 5 tokens by market cap
                top_tokens = sorted(results['tokens'], key=lambda x: x.market_cap, reverse=True)[:5]
                print(f"\nTop 5 Tokens by Market Cap:")
                for i, token in enumerate(top_tokens, 1):
                    print(f"  {i}. {token.name} ({token.symbol}) - ${token.market_cap:,.2f}")
            
            if results['transactions']:
                # Transaction statistics
                buy_txs = [tx for tx in results['transactions'] if tx.action == 'buy']
                sell_txs = [tx for tx in results['transactions'] if tx.action == 'sell']
                
                print(f"\nTransaction Breakdown:")
                print(f"  Buy transactions: {len(buy_txs)}")
                print(f"  Sell transactions: {len(sell_txs)}")
                
                if buy_txs:
                    total_buy_volume = sum(tx.amount * tx.price for tx in buy_txs)
                    print(f"  Total buy volume: ${total_buy_volume:,.2f}")
            
            # File locations
            print(f"\nData saved to:")
            print(f"  📁 Directory: {config.output_directory}/")
            print(f"  📄 Format: {config.output_format}")
            print(f"  🗃️  Database: {config.output_directory}/pump_fun_data.db")
        
        print("\n✓ Scraping completed successfully!")


if __name__ == "__main__":
    main()