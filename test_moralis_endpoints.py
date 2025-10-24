#!/usr/bin/env python3
"""
Test script to verify all Moralis Pump.fun API endpoints are working correctly
"""

import asyncio
import logging
import sys
from config import ScraperConfig
from moralis_client import MoralisClient


async def test_endpoints():
    """Test all Moralis API endpoints"""
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    # Load configuration
    try:
        config = ScraperConfig.load("config.yaml")
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return False
    
    # Check for API key
    if not config.moralis_api_key:
        logger.error("❌ MORALIS_API_KEY not set!")
        logger.error("Please set it in .env file or config.yaml")
        return False
    
    logger.info(f"✓ API Key loaded: {config.moralis_api_key[:8]}...")
    
    # Initialize client
    client = MoralisClient(
        api_key=config.moralis_api_key,
        timeout=30.0,
        logger=logger
    )
    
    all_passed = True
    
    async with client:
        # Test 1: Get new pump.fun tokens
        logger.info("\n" + "="*60)
        logger.info("TEST 1: Get new pump.fun tokens")
        logger.info("="*60)
        try:
            tokens = await client.get_pump_fun_tokens(limit=5)
            if tokens:
                logger.info(f"✓ Success! Retrieved {len(tokens)} tokens")
                if tokens:
                    sample = tokens[0]
                    logger.info(f"  Sample token keys: {list(sample.keys())[:10]}")
            else:
                logger.warning("⚠ No tokens returned (may be expected if no new tokens)")
        except Exception as e:
            logger.error(f"❌ Failed: {e}")
            all_passed = False
        
        # Test 2: Get token metadata
        logger.info("\n" + "="*60)
        logger.info("TEST 2: Get token metadata")
        logger.info("="*60)
        try:
            # Use a known pump.fun token address (you may need to update this)
            test_mint = "pump123..."  # Replace with actual mint address from test 1
            if tokens and len(tokens) > 0:
                test_mint = tokens[0].get('mint') or tokens[0].get('address') or tokens[0].get('mint_address')
            
            if test_mint and test_mint != "pump123...":
                metadata = await client.get_token_metadata(test_mint)
                if metadata:
                    logger.info(f"✓ Success! Retrieved metadata for {test_mint[:8]}...")
                    logger.info(f"  Metadata keys: {list(metadata.keys())}")
                else:
                    logger.warning("⚠ No metadata returned")
            else:
                logger.info("⊘ Skipped (no test token address available)")
        except Exception as e:
            logger.error(f"❌ Failed: {e}")
            all_passed = False
        
        # Test 3: Get token price
        logger.info("\n" + "="*60)
        logger.info("TEST 3: Get token price")
        logger.info("="*60)
        try:
            if test_mint and test_mint != "pump123...":
                price_data = await client.get_token_price(test_mint)
                if price_data:
                    logger.info(f"✓ Success! Retrieved price for {test_mint[:8]}...")
                    logger.info(f"  Price data keys: {list(price_data.keys())}")
                else:
                    logger.warning("⚠ No price data returned")
            else:
                logger.info("⊘ Skipped (no test token address available)")
        except Exception as e:
            logger.error(f"❌ Failed: {e}")
            all_passed = False
        
        # Test 4: Get token swaps
        logger.info("\n" + "="*60)
        logger.info("TEST 4: Get token swaps")
        logger.info("="*60)
        try:
            if test_mint and test_mint != "pump123...":
                swaps = await client.get_token_swaps(
                    mint_address=test_mint,
                    limit=5,
                )
                if swaps:
                    logger.info(f"✓ Success! Retrieved {len(swaps)} swaps")
                    sample = swaps[0]
                    logger.info(f"  Sample swap keys: {list(sample.keys())[:10]}")
                else:
                    logger.warning("⚠ No swaps returned (may be expected)")
            else:
                logger.info("⊘ Skipped (no test token address available)")
        except Exception as e:
            logger.error(f"❌ Failed: {e}")
            all_passed = False
        
        # Test 5: Get graduated tokens
        logger.info("\n" + "="*60)
        logger.info("TEST 5: Get graduated tokens")
        logger.info("="*60)
        try:
            graduated = await client.get_graduated_tokens(limit=5)
            if graduated:
                logger.info(f"✓ Success! Retrieved {len(graduated)} graduated tokens")
            else:
                logger.warning("⚠ No graduated tokens returned (may be expected)")
        except Exception as e:
            logger.error(f"❌ Failed: {e}")
            all_passed = False
        
        # Test 6: Get bonding tokens
        logger.info("\n" + "="*60)
        logger.info("TEST 6: Get bonding tokens")
        logger.info("="*60)
        try:
            bonding = await client.get_bonding_tokens(limit=5)
            if bonding:
                logger.info(f"✓ Success! Retrieved {len(bonding)} bonding tokens")
            else:
                logger.warning("⚠ No bonding tokens returned (may be expected)")
        except Exception as e:
            logger.error(f"❌ Failed: {e}")
            all_passed = False
        
        # Test 7: Get bonding status
        logger.info("\n" + "="*60)
        logger.info("TEST 7: Get token bonding status")
        logger.info("="*60)
        try:
            if test_mint and test_mint != "pump123...":
                bonding_status = await client.get_token_bonding_status(test_mint)
                if bonding_status:
                    logger.info(f"✓ Success! Retrieved bonding status for {test_mint[:8]}...")
                    logger.info(f"  Status keys: {list(bonding_status.keys())}")
                else:
                    logger.warning("⚠ No bonding status returned")
            else:
                logger.info("⊘ Skipped (no test token address available)")
        except Exception as e:
            logger.error(f"❌ Failed: {e}")
            all_passed = False
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("TEST SUMMARY")
    logger.info("="*60)
    if all_passed:
        logger.info("✅ All tests passed!")
        return True
    else:
        logger.error("❌ Some tests failed - check logs above")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_endpoints())
    sys.exit(0 if success else 1)
