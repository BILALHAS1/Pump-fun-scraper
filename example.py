#!/usr/bin/env python3
"""
PumpPortal.fun Official API Example

This example demonstrates how to use the official PumpPortal.fun API
to collect real-time token data, transactions, and new launches.
"""

import asyncio
import json
from datetime import datetime
from config import ScraperConfig
from main import PumpPortalScraper


async def basic_example():
    """Basic example: Collect data for 30 seconds"""
    print("=== Basic PumpPortal.fun API Example ===")
    
    # Load configuration
    config = ScraperConfig.load("config.yaml")
    
    # Optional: Set API key for enhanced features
    # config.api_key = "your-api-key-here"
    
    async with PumpPortalScraper(config) as scraper:
        print(f"Collecting real-time data for 30 seconds...")
        print(f"WebSocket URL: {config.websocket_url}")
        print("-" * 50)
        
        # Collect data for 30 seconds
        results = await scraper.collect_data(duration_seconds=30)
        
        # Display results
        print(f"\n✓ Collection complete!")
        print(f"Messages received: {results['statistics']['messages_received']}")
        print(f"Tokens collected: {len(results['tokens'])}")
        print(f"Transactions collected: {len(results['transactions'])}")
        print(f"New launches: {len(results['new_launches'])}")
        print(f"Migrations: {len(results['migrations'])}")
        
        # Show sample new launches
        if results['new_launches']:
            print(f"\n🚀 New Token Launches:")
            for launch in results['new_launches'][:3]:
                print(f"  • {launch.name} ({launch.symbol}) - ${launch.price:.6f}")
        
        # Show sample transactions
        if results['transactions']:
            print(f"\n💱 Recent Transactions:")
            for tx in results['transactions'][:3]:
                print(f"  • {tx.action.upper()} {tx.amount:,.0f} tokens @ ${tx.price:.6f}")
        
        return results


async def new_launches_example():
    """Example: Monitor only new token launches"""
    print("\n=== New Launches Monitor Example ===")
    
    config = ScraperConfig.load("config.yaml")
    
    async with PumpPortalScraper(config) as scraper:
        print("Monitoring for new token launches (15 seconds)...")
        
        # Connect and subscribe only to new token events
        if await scraper.connect_websocket():
            # Subscribe specifically to new tokens
            subscription = {"method": "subscribeNewToken"}
            await scraper.websocket.send(json.dumps(subscription))
            print("✓ Subscribed to new token events")
            
            # Collect for 15 seconds
            results = await scraper.collect_data(duration_seconds=15)
            
            new_launches = results['new_launches']
            print(f"\n🚀 Found {len(new_launches)} new launches:")
            
            for launch in new_launches:
                print(f"  📈 {launch.name} ({launch.symbol})")
                print(f"     Price: ${launch.price:.8f}")
                print(f"     Market Cap: ${launch.market_cap:,.0f}")
                if launch.website:
                    print(f"     Website: {launch.website}")
                print()


async def custom_duration_example():
    """Example: Custom collection with statistics tracking"""
    print("\n=== Custom Duration Collection Example ===")
    
    config = ScraperConfig.load("config.yaml")
    
    async with PumpPortalScraper(config) as scraper:
        duration = 45  # 45 seconds
        print(f"Collecting data for {duration} seconds with live statistics...")
        
        # Start data collection
        start_time = datetime.now()
        results = await scraper.collect_data(duration_seconds=duration)
        end_time = datetime.now()
        
        # Calculate statistics
        stats = results['statistics']
        actual_duration = (end_time - start_time).total_seconds()
        
        print(f"\n📊 Collection Statistics:")
        print(f"  Planned duration: {duration} seconds")
        print(f"  Actual duration: {actual_duration:.1f} seconds")
        print(f"  Messages received: {stats['messages_received']}")
        print(f"  Connection errors: {stats['connection_errors']}")
        print(f"  Reconnection attempts: {stats['reconnection_attempts']}")
        
        if stats['messages_received'] > 0:
            msg_rate = stats['messages_received'] / actual_duration
            print(f"  Message rate: {msg_rate:.1f} messages/second")
        
        print(f"\n📦 Data Collected:")
        print(f"  Unique tokens: {len(results['tokens'])}")
        print(f"  Total transactions: {len(results['transactions'])}")
        print(f"  New launches: {len(results['new_launches'])}")
        print(f"  Migration events: {len(results['migrations'])}")


async def api_key_example():
    """Example: Using API key for enhanced features"""
    print("\n=== API Key Enhanced Features Example ===")
    
    config = ScraperConfig.load("config.yaml")
    
    if not config.api_key:
        print("ℹ No API key configured - using public access")
        print("To use enhanced features:")
        print("1. Get an API key from https://pumpportal.fun")
        print("2. Add it to config.yaml or use --api-key flag")
        print("3. Run this example again")
        return
    
    async with PumpPortalScraper(config) as scraper:
        print(f"✓ Using API key: {config.api_key[:8]}...")
        print("Enhanced features may include:")
        print("  • Higher rate limits")
        print("  • Priority access")
        print("  • Additional data fields")
        print("  • Better connection stability")
        
        results = await scraper.collect_data(duration_seconds=20)
        
        print(f"\n📊 Results with API key:")
        print(f"  Messages: {results['statistics']['messages_received']}")
        print(f"  Connection errors: {results['statistics']['connection_errors']}")
        print(f"  Data quality: Enhanced with API key features")


async def main():
    """Run all examples"""
    try:
        print("🚀 PumpPortal.fun Official API Examples")
        print("=" * 50)
        
        # Run examples
        await basic_example()
        await new_launches_example()
        await custom_duration_example()
        await api_key_example()
        
        print("\n" + "=" * 50)
        print("✅ All examples completed successfully!")
        print("Check the 'data/' directory for saved output files.")
        
    except KeyboardInterrupt:
        print("\n⚠ Examples interrupted by user")
    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())