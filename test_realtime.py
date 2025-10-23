#!/usr/bin/env python3
"""Test script for real-time dashboard functionality"""

import time
from dashboard.app import create_app


def test_sse_endpoint():
    """Test that SSE endpoint is available and streaming"""
    app = create_app()
    
    with app.test_client() as client:
        # Test main route
        response = client.get('/')
        assert response.status_code == 200
        assert b'LIVE' in response.data
        assert b'connection-status' in response.data
        print("✓ Main page loads with live mode indicators")
        
        # Test API data endpoint
        response = client.get('/api/data')
        assert response.status_code == 200
        data = response.get_json()
        assert 'tokens' in data
        print("✓ API data endpoint returns token data")
        
        # Test SSE stream endpoint (just verify it starts)
        response = client.get('/api/stream')
        assert response.status_code == 200
        assert response.mimetype == 'text/event-stream'
        print("✓ SSE stream endpoint is available")
        
        # Get first chunk of SSE data
        chunks = []
        for i, chunk in enumerate(response.response):
            chunks.append(chunk)
            if i >= 1:  # Get first 2 chunks
                break
        
        # Verify we got data
        assert len(chunks) > 0
        print(f"✓ SSE stream is sending data ({len(chunks)} chunks received)")
        
        # Check for connection message
        first_chunk = chunks[0].decode('utf-8')
        assert 'connected' in first_chunk or 'update' in first_chunk
        print("✓ SSE stream sends proper event messages")


def test_live_update_interval():
    """Test that updates happen at expected interval"""
    app = create_app()
    
    with app.test_client() as client:
        response = client.get('/api/stream')
        
        start_time = time.time()
        chunks = []
        
        # Collect chunks for ~2.5 seconds
        for chunk in response.response:
            chunks.append(chunk)
            elapsed = time.time() - start_time
            if elapsed > 2.5:
                break
        
        # Should have received at least 2-3 updates (at 1 second intervals)
        assert len(chunks) >= 2
        print(f"✓ Received {len(chunks)} updates in {elapsed:.1f} seconds (expected ~2-3)")


if __name__ == '__main__':
    print("Testing Real-Time Dashboard Functionality\n")
    print("=" * 50)
    
    try:
        test_sse_endpoint()
        print("\n" + "=" * 50)
        test_live_update_interval()
        print("\n" + "=" * 50)
        print("\n✅ All tests passed! Real-time dashboard is working.")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        exit(1)
