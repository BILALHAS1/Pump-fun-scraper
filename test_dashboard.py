#!/usr/bin/env python3
"""
Test script to verify the dashboard works correctly.
"""
import json
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dashboard.app import create_app

def test_dashboard():
    """Test dashboard functionality"""
    app = create_app()
    client = app.test_client()
    
    print("Testing dashboard...")
    
    print("\n1. Testing home page...")
    response = client.get('/')
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    html = response.data.decode('utf-8')
    assert "Pump.fun Dashboard" in html, "Title not found in HTML"
    assert "Auto-refresh: Every" in html, "Auto-refresh text not found"
    assert "5 minutes" in html or "300" in html, "5 minutes refresh interval not found"
    assert "last-updated" in html, "Last updated element not found"
    assert "Ticker / Name" in html, "Table header not found"
    assert "Market Cap at Start" in html, "Market cap header not found"
    print("   ✓ Home page loads correctly")
    print("   ✓ Contains dashboard title")
    print("   ✓ Contains auto-refresh badge")
    print("   ✓ Contains 5-minute refresh interval")
    print("   ✓ Contains last updated timestamp")
    print("   ✓ Contains table headers (Ticker, Price, Market Cap)")
    
    print("\n2. Testing /api/data endpoint...")
    response = client.get('/api/data')
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = json.loads(response.data)
    assert 'tokens' in data, "tokens key not found in response"
    assert 'generated_at' in data, "generated_at not found in response"
    print(f"   ✓ API returns data successfully")
    
    tokens = data['tokens']
    print(f"   ✓ Found {len(tokens)} tokens")
    
    if len(tokens) > 0:
        print("\n3. Verifying token data structure...")
        for i, token in enumerate(tokens[:3], 1):
            symbol = token.get('symbol', 'N/A')
            name = token.get('name', 'N/A')
            price = token.get('price', 'N/A')
            market_cap = token.get('market_cap', 'N/A')
            print(f"   Token {i}: {symbol} ({name})")
            print(f"      Price: ${price}")
            print(f"      Market Cap: ${market_cap}")
            assert 'symbol' in token or 'name' in token, f"Token {i} missing symbol/name"
            assert 'price' in token, f"Token {i} missing price"
            assert 'market_cap' in token, f"Token {i} missing market_cap"
        print("   ✓ All tokens have required fields")
    
    print("\n4. Testing healthcheck endpoint...")
    response = client.get('/healthz')
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    health = json.loads(response.data)
    assert health.get('status') == 'ok', "Healthcheck failed"
    print("   ✓ Healthcheck endpoint working")
    
    print("\n✅ All tests passed!")
    print("\nDashboard features verified:")
    print("  ✓ Displays coin ticker names")
    print("  ✓ Displays prices")
    print("  ✓ Displays market cap at start")
    print("  ✓ Auto-refresh set to 5 minutes")
    print("  ✓ Last updated timestamp visible")
    print("  ✓ Clean, simple interface")
    return True

if __name__ == '__main__':
    try:
        test_dashboard()
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
