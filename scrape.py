#!/usr/bin/env python3
"""
Simple CLI interface for the pump.fun scraper
"""

import asyncio
import argparse
import sys
from pathlib import Path

from config import ScraperConfig
from main import PumpPortalScraper


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
        "--duration", "-d",
        type=int,
        help="Data collection duration in seconds (overrides config)"
    )
    
    parser.add_argument(
        "--api-key",
        help="PumpPortal API key for enhanced features"
    )
    
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Disable browser fallback (deprecated - now uses WebSocket API)"
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
    
    if args.duration:
        config.data_collection_duration = args.duration
        print(f"Set data collection duration to: {args.duration} seconds")
    
    if args.api_key:
        config.api_key = args.api_key
        print("✓ API key provided for enhanced features")
    
    if args.output:
        config.output_format = args.output
        print(f"Set output format to: {args.output}")
    
    if args.verbose:
        config.log_level = "DEBUG"
        print("Enabled verbose logging")
    
    if args.no_browser:
        print("ℹ Browser fallback is deprecated (now uses official WebSocket API)")
    
    if args.quick:
        config.data_collection_duration = min(120, config.data_collection_duration)
        print(f"Quick mode: {config.data_collection_duration} second collection")
    
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
    
    async with PumpPortalScraper(config) as scraper:
        print(f"Starting PumpPortal.fun official API scraper...")
        print(f"WebSocket URL: {config.websocket_url}")
        print(f"Output directory: {config.output_directory}")
        print(f"Output format: {config.output_format}")
        print(f"Data collection duration: {config.data_collection_duration} seconds")
        if config.api_key:
            print("✓ Using API key for enhanced features")
        else:
            print("ℹ No API key provided, using public access")
        print("-" * 50)
        
        if args.new_launches:
            # Only scrape new launches
            print("Collecting new token launches from real-time stream...")
            print("This will collect data for a short period to capture recent launches")
            
            # Use a shorter duration for new launches
            results = await scraper.collect_data(duration_seconds=min(300, args.tokens or 300))
            new_launches = results['new_launches']
            
            if new_launches:
                await scraper.data_storage.save_new_launches(
                    new_launches,
                    format_type=config.output_format,
                )
                print(f"✓ Found and saved {len(new_launches)} new launches")
                
                # Print summary of new launches
                print("\nNew Launches Summary:")
                for launch in new_launches[:5]:  # Show first 5
                    print(f"  • {launch.name} ({launch.symbol}) - ${launch.price:.6f}")
                
                if len(new_launches) > 5:
                    print(f"  ... and {len(new_launches) - 5} more")
            else:
                print("No new launches detected during collection period")
        
        else:
            # Full or quick scrape
            collection_duration = config.data_collection_duration
            if args.quick:
                collection_duration = min(120, collection_duration)  # Shorter for quick mode
                print(f"Running quick scrape (collecting for {collection_duration} seconds)...")
            else:
                print(f"Running comprehensive scrape (collecting for {collection_duration} seconds)...")
            
            results = await scraper.collect_data(duration_seconds=collection_duration)
            
            # Save collected data
            if results['tokens']:
                await scraper.data_storage.save_tokens(
                    results['tokens'],
                    format_type=config.output_format,
                )
            if results['transactions']:
                await scraper.data_storage.save_transactions(
                    results['transactions'],
                    format_type=config.output_format,
                )
            if results['new_launches']:
                await scraper.data_storage.save_new_launches(
                    results['new_launches'],
                    format_type=config.output_format,
                )
            
            # Print results summary
            print("\n" + "=" * 50)
            print("SCRAPING RESULTS SUMMARY")
            print("=" * 50)
            
            print(f"Messages received: {results['statistics']['messages_received']}")
            print(f"Tokens collected: {len(results['tokens'])}")
            print(f"Transactions collected: {len(results['transactions'])}")
            print(f"New launches found: {len(results['new_launches'])}")
            print(f"Migration events: {len(results['migrations'])}")
            
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
            
            # Session statistics
            stats = results['statistics']
            print(f"\nSession Statistics:")
            print(f"  Duration: {stats['session_duration']:.1f} seconds")
            print(f"  Connection errors: {stats['connection_errors']}")
            print(f"  Reconnection attempts: {stats['reconnection_attempts']}")
        
        print("\n✓ Scraping completed successfully!")


if __name__ == "__main__":
    main()