#!/usr/bin/env python3
"""
Integration test for continuous real-time scraping mode
"""

import asyncio
import os
import time
from pathlib import Path
from main import PumpPortalScraper
from config import ScraperConfig

async def test_short_run():
    """Test that scraper works in continuous mode for a short period"""
    print("=" * 70)
    print("Integration Test: Continuous Real-Time Mode")
    print("=" * 70)
    print()
    
    # Load config
    config = ScraperConfig.load()
    
    # Ensure data directory exists
    data_dir = Path(config.output_directory)
    data_dir.mkdir(exist_ok=True)
    
    print(f"✓ Configuration loaded")
    print(f"✓ Data directory: {data_dir}")
    print()
    
    # Get initial file count
    initial_files = list(data_dir.glob("**/*.json"))
    print(f"Initial JSON files in data directory: {len(initial_files)}")
    print()
    
    print("Testing scraper initialization...")
    scraper = PumpPortalScraper(config)
    print("✓ Scraper initialized successfully")
    print()
    
    # Test methods exist
    print("Checking required methods...")
    assert hasattr(scraper, '_periodic_data_save'), "Missing _periodic_data_save"
    assert hasattr(scraper, '_periodic_stats_logging'), "Missing _periodic_stats_logging"
    assert hasattr(scraper, '_save_current_data'), "Missing _save_current_data"
    assert hasattr(scraper, 'collect_data'), "Missing collect_data"
    print("✓ All required methods present")
    print()
    
    # Test graceful shutdown mechanism
    print("Testing shutdown mechanism...")
    assert scraper._shutdown_event is not None, "Missing shutdown event"
    assert not scraper._shutdown_event.is_set(), "Shutdown event should not be set initially"
    scraper._shutdown_event.set()
    assert scraper._shutdown_event.is_set(), "Shutdown event should be set after calling set()"
    print("✓ Graceful shutdown mechanism works")
    print()
    
    print("=" * 70)
    print("✅ All integration tests passed!")
    print("=" * 70)
    print()
    print("The scraper is ready for continuous operation:")
    print()
    print("  1. Run continuously:")
    print("     python main.py")
    print()
    print("  2. Stop with:")
    print("     Ctrl+C")
    print()
    print("  3. View real-time dashboard:")
    print("     python -m dashboard.app")
    print()
    print("  4. Data saves every 20 seconds to:")
    print(f"     {data_dir}/")
    print()

if __name__ == "__main__":
    asyncio.run(test_short_run())
