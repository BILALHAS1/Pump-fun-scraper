#!/usr/bin/env python3
"""
Quick connection test for PumpPortal.fun API
Tests WebSocket connectivity without collecting data for extended periods.
"""

import asyncio
import json
from datetime import datetime
from config import ScraperConfig
from main import PumpPortalScraper


async def test_websocket_connection():
    """Test basic WebSocket connection to PumpPortal.fun"""
    print("🧪 Testing PumpPortal.fun WebSocket API Connection")
    print("=" * 50)
    
    config = ScraperConfig.load("config.yaml")
    print(f"WebSocket URL: {config.websocket_url}")
    
    if config.api_key:
        print(f"API Key: {config.api_key[:8]}...")
    else:
        print("API Key: Not provided (using public access)")
    
    try:
        async with PumpPortalScraper(config) as scraper:
            print("\n📡 Attempting to connect to WebSocket...")
            
            if await scraper.connect_websocket():
                print("✅ WebSocket connection successful!")
                
                print("\n📝 Sending subscription requests...")
                await scraper.subscribe_to_data_streams()
                print("✅ Subscriptions sent successfully!")
                
                print("\n⏱️ Testing message reception (10 seconds)...")
                start_time = datetime.now()
                messages_received = 0
                
                # Listen for messages for 10 seconds
                try:
                    while (datetime.now() - start_time).total_seconds() < 10:
                        try:
                            message = await asyncio.wait_for(
                                scraper.websocket.recv(), 
                                timeout=1.0
                            )
                            
                            # Parse message to see what type it is
                            data = json.loads(message)
                            msg_type = data.get('type', 'unknown')
                            
                            messages_received += 1
                            
                            if messages_received <= 3:  # Show first few messages
                                print(f"  📨 Received: {msg_type}")
                            elif messages_received == 4:
                                print(f"  📨 ... (and more)")
                            
                        except asyncio.TimeoutError:
                            continue  # No message received in 1 second, continue
                        except json.JSONDecodeError:
                            print(f"  ⚠️ Received non-JSON message")
                        except Exception as e:
                            print(f"  ❌ Error processing message: {e}")
                
                except Exception as e:
                    print(f"❌ Error during message listening: {e}")
                
                duration = (datetime.now() - start_time).total_seconds()
                
                print(f"\n📊 Test Results:")
                print(f"  Duration: {duration:.1f} seconds")
                print(f"  Messages received: {messages_received}")
                
                if messages_received > 0:
                    rate = messages_received / duration
                    print(f"  Message rate: {rate:.1f} messages/second")
                    print("✅ Connection is working and receiving data!")
                    return True
                else:
                    print("⚠️ No messages received (this might be normal if no activity)")
                    print("✅ Connection established but no data in test period")
                    return True
                    
            else:
                print("❌ Failed to establish WebSocket connection")
                return False
                
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        print(f"Full traceback:\n{traceback.format_exc()}")
        return False


async def test_configuration():
    """Test configuration loading and validation"""
    print("\n🔧 Testing Configuration")
    print("-" * 30)
    
    try:
        config = ScraperConfig.load("config.yaml")
        print("✅ Configuration loaded successfully")
        
        config.validate_config()
        print("✅ Configuration validation passed")
        
        print(f"  • WebSocket URL: {config.websocket_url}")
        print(f"  • Data collection duration: {config.data_collection_duration}s")
        print(f"  • Output format: {config.output_format}")
        print(f"  • Log level: {config.log_level}")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False


async def test_data_models():
    """Test data model creation"""
    print("\n📋 Testing Data Models")
    print("-" * 25)
    
    try:
        from models import TokenInfo, TransactionData
        
        # Test TokenInfo
        token = TokenInfo(
            name="Test Token",
            symbol="TEST",
            price=0.001,
            market_cap=1000000,
            volume_24h=50000,
            mint_address="test123456789"
        )
        
        print(f"✅ TokenInfo created: {token.name} ({token.symbol})")
        
        # Test TransactionData
        transaction = TransactionData(
            signature="test_signature",
            token_mint="test123456789",
            action="buy",
            amount=1000.0,
            price=0.001,
            user="test_user",
            timestamp=datetime.now()
        )
        
        print(f"✅ TransactionData created: {transaction.action} {transaction.amount}")
        
        return True
        
    except Exception as e:
        print(f"❌ Data model test failed: {e}")
        return False


async def main():
    """Run all tests"""
    print("🚀 PumpPortal.fun API Connection Test Suite")
    print("=" * 60)
    
    tests_passed = 0
    total_tests = 3
    
    # Test 1: Configuration
    if await test_configuration():
        tests_passed += 1
    
    # Test 2: Data Models
    if await test_data_models():
        tests_passed += 1
    
    # Test 3: WebSocket Connection
    if await test_websocket_connection():
        tests_passed += 1
    
    # Summary
    print("\n" + "=" * 60)
    print(f"📊 TEST SUMMARY: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed! Your setup is working correctly.")
        print("\n🚀 Ready to use the PumpPortal.fun API scraper!")
        print("   Run: python scrape.py --duration 30")
    else:
        print("⚠️ Some tests failed. Please check the error messages above.")
        
    return tests_passed == total_tests


if __name__ == "__main__":
    asyncio.run(main())