#!/usr/bin/env python3
"""
Example usage of the pump.fun scraper
"""

import asyncio
from datetime import datetime, timedelta
from config import ScraperConfig
from main import PumpFunScraper


async def basic_example():
    """Basic scraping example"""
    print("🚀 Basic Pump.fun Scraping Example")
    print("-" * 40)
    
    # Load configuration
    config = ScraperConfig.load("config.yaml")
    
    # Reduce limits for example
    config.max_tokens = 20
    config.max_tokens_for_transactions = 5
    
    async with PumpFunScraper(config) as scraper:
        # Get latest tokens
        print("📊 Fetching latest tokens...")
        tokens = await scraper.get_tokens_api(limit=20)
        
        if tokens:
            print(f"✅ Found {len(tokens)} tokens")
            
            # Show top 5 by market cap
            top_tokens = sorted(tokens, key=lambda x: x.market_cap, reverse=True)[:5]
            print("\n🏆 Top 5 Tokens by Market Cap:")
            for i, token in enumerate(top_tokens, 1):
                print(f"  {i}. {token.name} ({token.symbol})")
                print(f"     💰 Market Cap: ${token.market_cap:,.2f}")
                print(f"     💵 Price: ${token.price:.6f}")
                print()
        
        # Get new launches
        print("🆕 Checking for new launches...")
        new_launches = await scraper.get_new_launches(hours=24)
        
        if new_launches:
            print(f"✅ Found {len(new_launches)} new launches in last 24 hours")
            for launch in new_launches[:3]:  # Show first 3
                print(f"  • {launch.name} ({launch.symbol}) - ${launch.price:.6f}")
        else:
            print("ℹ️  No new launches found in last 24 hours")
        
        # Get transactions for first token
        if tokens and tokens[0].mint_address:
            print(f"\n💱 Getting transactions for {tokens[0].name}...")
            transactions = await scraper.get_token_transactions(
                tokens[0].mint_address, 
                limit=10
            )
            
            if transactions:
                print(f"✅ Found {len(transactions)} transactions")
                buy_count = len([tx for tx in transactions if tx.action == "buy"])
                sell_count = len([tx for tx in transactions if tx.action == "sell"])
                print(f"  📈 Buys: {buy_count}, 📉 Sells: {sell_count}")
        
        # Save data
        print("\n💾 Saving data...")
        if tokens:
            await scraper.data_storage.save_tokens(tokens)
        if new_launches:
            await scraper.data_storage.save_new_launches(new_launches)
        
        print("✅ Example completed successfully!")


async def monitoring_example():
    """Example of continuous monitoring"""
    print("\n🔄 Monitoring Example (runs for 2 minutes)")
    print("-" * 40)
    
    config = ScraperConfig.load("config.yaml")
    config.max_tokens = 10
    
    async with PumpFunScraper(config) as scraper:
        end_time = datetime.now() + timedelta(minutes=2)
        
        while datetime.now() < end_time:
            print(f"⏰ {datetime.now().strftime('%H:%M:%S')} - Checking for updates...")
            
            # Quick check for new launches
            new_launches = await scraper.get_new_launches(hours=1)
            
            if new_launches:
                print(f"🚨 ALERT: {len(new_launches)} new token(s) launched!")
                for launch in new_launches:
                    print(f"  🆕 {launch.name} ({launch.symbol})")
            else:
                print("  ✅ No new launches detected")
            
            # Wait 30 seconds before next check
            await asyncio.sleep(30)
        
        print("🏁 Monitoring example completed")


async def data_analysis_example():
    """Example of analyzing scraped data"""
    print("\n📊 Data Analysis Example")
    print("-" * 40)
    
    config = ScraperConfig.load("config.yaml")
    
    async with PumpFunScraper(config) as scraper:
        # Get daily summary
        summary = await scraper.data_storage.get_daily_summary()
        
        print("📈 Today's Statistics:")
        print(f"  Tokens tracked: {summary['tokens']['count']}")
        print(f"  Total volume: ${summary['tokens']['total_volume']:,.2f}")
        print(f"  Transactions: {summary['transactions']['count']}")
        print(f"  Unique trading tokens: {summary['transactions']['unique_tokens']}")
        
        # Export recent data
        start_date = datetime.now() - timedelta(days=1)
        export_file = await scraper.data_storage.export_data(
            start_date=start_date,
            format_type="json"
        )
        print(f"📁 Data exported to: {export_file}")


async def main():
    """Run all examples"""
    try:
        await basic_example()
        # await monitoring_example()  # Uncomment for continuous monitoring
        # await data_analysis_example()  # Uncomment for data analysis
        
    except Exception as e:
        print(f"❌ Error in example: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("🎯 Pump.fun Scraper Examples")
    print("=" * 50)
    asyncio.run(main())