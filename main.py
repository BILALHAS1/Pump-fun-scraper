#!/usr/bin/env python3
"""
PumpPortal.fun Official API Data Scraper

This script uses the official PumpPortal.fun WebSocket API to collect real-time
token information, transaction data, and trading activity with proper error handling
and rate limiting.
"""

import asyncio
import json
import signal
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlparse, parse_qs

import websockets
from websockets.client import WebSocketClientProtocol
from websockets.exceptions import ConnectionClosed, WebSocketException

from config import ScraperConfig
from models import TokenInfo, TransactionData
from utils.data_storage import DataStorage
from utils.logger import setup_logger
from utils.rate_limiter import AdaptiveRateLimiter


class PumpPortalScraper:
    """Official PumpPortal.fun API scraper using WebSocket connections"""
    
    def __init__(self, config: ScraperConfig):
        self.config = config
        self.logger = setup_logger(__name__, config.log_level)
        self.data_storage = DataStorage(config.output_directory)
        self.rate_limiter = AdaptiveRateLimiter(
            requests_per_minute=config.rate_limit_rpm,
            requests_per_hour=config.rate_limit_rph
        )
        
        # WebSocket connection
        self.websocket: Optional[WebSocketClientProtocol] = None
        self.connection_url = self._build_websocket_url()
        
        # Data collection
        self.collected_tokens: Dict[str, TokenInfo] = {}
        self.collected_transactions: List[TransactionData] = []
        self.new_launches: List[TokenInfo] = []
        self.migration_events: List[Dict[str, Any]] = []
        
        # Connection management
        self.is_connected = False
        self.should_reconnect = True
        self.reconnection_attempts = 0
        self.last_ping = time.time()
        
        # Statistics
        self.session_start = datetime.now()
        self.messages_received = 0
        self.connection_errors = 0
        
        # Graceful shutdown
        self._shutdown_event = asyncio.Event()
        self._setup_signal_handlers()
    
    def _build_websocket_url(self) -> str:
        """Build WebSocket URL with optional API key"""
        url = self.config.websocket_url
        if self.config.api_key:
            url = f"{url}?api-key={self.config.api_key}"
        return url
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            self.should_reconnect = False
            self._shutdown_event.set()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.cleanup()
    
    async def initialize(self):
        """Initialize the scraper"""
        self.logger.info("Initializing PumpPortal.fun scraper...")
        self.logger.info(f"WebSocket URL: {self.config.websocket_url}")
        if self.config.api_key:
            self.logger.info("Using API key for enhanced features")
        else:
            self.logger.info("No API key provided, using public access")
    
    async def cleanup(self):
        """Clean up resources"""
        self.should_reconnect = False
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        self.logger.info("Scraper cleanup completed")
    
    async def connect_websocket(self) -> bool:
        """Connect to PumpPortal WebSocket API"""
        try:
            self.logger.info(f"Connecting to WebSocket: {self.connection_url}")
            
            # Connection with timeout
            self.websocket = await asyncio.wait_for(
                websockets.connect(
                    self.connection_url,
                    ping_interval=self.config.websocket_ping_interval,
                    ping_timeout=self.config.websocket_timeout / 2,
                    close_timeout=10
                ),
                timeout=self.config.websocket_timeout
            )
            
            self.is_connected = True
            self.reconnection_attempts = 0
            self.last_ping = time.time()
            
            self.logger.info("WebSocket connection established successfully")
            return True
            
        except asyncio.TimeoutError:
            self.logger.error("WebSocket connection timeout")
            self.connection_errors += 1
            return False
        except Exception as e:
            self.logger.error(f"Failed to connect to WebSocket: {e}")
            self.connection_errors += 1
            return False
    
    async def subscribe_to_data_streams(self):
        """Subscribe to all available data streams"""
        if not self.websocket:
            raise RuntimeError("WebSocket not connected")
        
        subscriptions = [
            {"method": "subscribeNewToken"},
            {"method": "subscribeMigration"},
            # We can add specific token/account subscriptions later if needed
        ]
        
        for subscription in subscriptions:
            try:
                await self.websocket.send(json.dumps(subscription))
                self.logger.info(f"Subscribed to: {subscription['method']}")
                await asyncio.sleep(0.1)  # Small delay between subscriptions
            except Exception as e:
                self.logger.error(f"Failed to send subscription {subscription}: {e}")
    
    async def handle_message(self, message: str):
        """Process incoming WebSocket message"""
        try:
            data = json.loads(message)
            self.messages_received += 1
            
            # Log message type for debugging
            message_type = data.get('type', 'unknown')
            self.logger.debug(f"Received message type: {message_type}")
            
            # Handle different message types
            if message_type == 'newToken':
                await self._process_new_token(data)
            elif message_type == 'tokenTrade':
                await self._process_token_trade(data)
            elif message_type == 'accountTrade':
                await self._process_account_trade(data)
            elif message_type == 'migration':
                await self._process_migration(data)
            else:
                # Log unknown message types for debugging
                self.logger.debug(f"Unknown message type '{message_type}': {json.dumps(data, indent=2)}")
                
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to decode message as JSON: {e}")
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
    
    async def _process_new_token(self, data: Dict[str, Any]):
        """Process new token creation event"""
        try:
            token_data = data.get('data', {})
            
            # Extract token information
            token = TokenInfo(
                name=token_data.get('name', ''),
                symbol=token_data.get('symbol', ''),
                mint_address=token_data.get('mint', ''),
                price=self._safe_float(token_data.get('priceUsd')),
                market_cap=self._safe_float(token_data.get('marketCapUsd')),
                volume_24h=self._safe_float(token_data.get('volume24h')),
                created_timestamp=self._parse_timestamp(token_data.get('timestamp')),
                description=token_data.get('description', ''),
                image_uri=token_data.get('imageUrl', ''),
                twitter=token_data.get('twitter', ''),
                telegram=token_data.get('telegram', ''),
                website=token_data.get('website', '')
            )
            
            if token.mint_address:
                self.collected_tokens[token.mint_address] = token
                self.new_launches.append(token)
                
                self.logger.info(
                    f"New token: {token.name} ({token.symbol}) - "
                    f"${token.price:.6f} | MC: ${token.market_cap:,.0f}"
                )
            
        except Exception as e:
            self.logger.error(f"Error processing new token: {e}")
    
    async def _process_token_trade(self, data: Dict[str, Any]):
        """Process token trade event"""
        try:
            trade_data = data.get('data', {})
            
            transaction = TransactionData(
                signature=trade_data.get('signature', ''),
                token_mint=trade_data.get('mint', ''),
                action=trade_data.get('tradeType', '').lower(),  # 'buy' or 'sell'
                amount=self._safe_float(trade_data.get('tokenAmount')),
                price=self._safe_float(trade_data.get('priceUsd')),
                user=trade_data.get('trader', ''),
                timestamp=self._parse_timestamp(trade_data.get('timestamp'))
            )
            
            if transaction.signature:
                self.collected_transactions.append(transaction)
                
                self.logger.debug(
                    f"Trade: {transaction.action.upper()} {transaction.amount:,.0f} "
                    f"${transaction.price:.6f} by {transaction.user[:8]}..."
                )
            
        except Exception as e:
            self.logger.error(f"Error processing token trade: {e}")
    
    async def _process_account_trade(self, data: Dict[str, Any]):
        """Process account trade event"""
        # Similar to token trade but from account perspective
        await self._process_token_trade(data)
    
    async def _process_migration(self, data: Dict[str, Any]):
        """Process token migration event"""
        try:
            migration_data = data.get('data', {})
            self.migration_events.append(migration_data)
            
            token_name = migration_data.get('name', 'Unknown')
            mint_address = migration_data.get('mint', '')
            
            self.logger.info(f"Migration event: {token_name} ({mint_address[:8]}...)")
            
        except Exception as e:
            self.logger.error(f"Error processing migration: {e}")
    
    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        """Safely convert value to float"""
        if value is None:
            return default
        try:
            return float(value)
        except (TypeError, ValueError):
            return default
    
    def _parse_timestamp(self, value: Any) -> Optional[datetime]:
        """Parse timestamp from various formats"""
        if value is None:
            return None
        
        try:
            if isinstance(value, (int, float)):
                # Handle both seconds and milliseconds timestamps
                timestamp = value / 1000 if value > 1_000_000_000_000 else value
                return datetime.fromtimestamp(timestamp)
            elif isinstance(value, str):
                # Try parsing ISO format
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
        except Exception:
            pass
        
        return None
    
    async def maintain_connection(self):
        """Main connection maintenance loop"""
        while self.should_reconnect and not self._shutdown_event.is_set():
            try:
                if not self.is_connected:
                    if await self.connect_websocket():
                        await self.subscribe_to_data_streams()
                
                if self.websocket:
                    try:
                        # Wait for message with timeout
                        message = await asyncio.wait_for(
                            self.websocket.recv(), 
                            timeout=30.0
                        )
                        await self.handle_message(message)
                        
                    except asyncio.TimeoutError:
                        # Send ping to keep connection alive
                        await self.websocket.ping()
                        self.last_ping = time.time()
                        continue
                        
                    except ConnectionClosed:
                        self.logger.warning("WebSocket connection closed")
                        self.is_connected = False
                        self.websocket = None
                        
                    except Exception as e:
                        self.logger.error(f"Error receiving message: {e}")
                        self.is_connected = False
                        self.websocket = None
                
            except Exception as e:
                self.logger.error(f"Connection maintenance error: {e}")
                self.is_connected = False
                self.websocket = None
            
            # Handle reconnection
            if not self.is_connected and self.should_reconnect:
                self.reconnection_attempts += 1
                
                if self.reconnection_attempts <= self.config.websocket_reconnect_attempts:
                    delay = min(
                        self.config.websocket_reconnect_delay * (2 ** (self.reconnection_attempts - 1)),
                        60.0  # Max 60 seconds delay
                    )
                    
                    self.logger.info(
                        f"Reconnection attempt {self.reconnection_attempts}/"
                        f"{self.config.websocket_reconnect_attempts} in {delay:.1f}s"
                    )
                    
                    try:
                        await asyncio.wait_for(
                            asyncio.sleep(delay), 
                            timeout=delay + 1
                        )
                    except asyncio.TimeoutError:
                        pass
                    
                    if self._shutdown_event.is_set():
                        break
                else:
                    self.logger.error("Maximum reconnection attempts reached")
                    break
    
    async def collect_data(self, duration_seconds: Optional[int] = None) -> Dict[str, Any]:
        """Collect data for specified duration"""
        collection_duration = duration_seconds or self.config.data_collection_duration
        
        self.logger.info(f"Starting data collection for {collection_duration} seconds...")
        
        # Start connection maintenance
        connection_task = asyncio.create_task(self.maintain_connection())
        
        try:
            # Wait for specified duration or shutdown signal
            await asyncio.wait_for(
                self._shutdown_event.wait(),
                timeout=collection_duration
            )
        except asyncio.TimeoutError:
            # Normal completion after timeout
            self.logger.info("Data collection duration completed")
        
        # Stop connection maintenance
        self.should_reconnect = False
        if not connection_task.done():
            connection_task.cancel()
            try:
                await connection_task
            except asyncio.CancelledError:
                pass
        
        # Prepare results
        results = {
            'tokens': list(self.collected_tokens.values()),
            'transactions': self.collected_transactions,
            'new_launches': self.new_launches,
            'migrations': self.migration_events,
            'statistics': self._get_session_statistics()
        }
        
        self.logger.info(f"Collection complete: {len(results['tokens'])} tokens, "
                        f"{len(results['transactions'])} transactions, "
                        f"{len(results['new_launches'])} new launches")
        
        return results
    
    def _get_session_statistics(self) -> Dict[str, Any]:
        """Get session statistics"""
        duration = (datetime.now() - self.session_start).total_seconds()
        
        return {
            'session_duration': duration,
            'messages_received': self.messages_received,
            'connection_errors': self.connection_errors,
            'reconnection_attempts': self.reconnection_attempts,
            'tokens_collected': len(self.collected_tokens),
            'transactions_collected': len(self.collected_transactions),
            'new_launches': len(self.new_launches),
            'migrations': len(self.migration_events)
        }
    
    async def run_full_scrape(self) -> Dict[str, Any]:
        """Run complete data collection process"""
        try:
            # Collect real-time data
            results = await self.collect_data()
            
            # Save data
            if results['tokens']:
                await self.data_storage.save_tokens(results['tokens'])
            
            if results['transactions']:
                await self.data_storage.save_transactions(results['transactions'])
            
            if results['new_launches']:
                await self.data_storage.save_new_launches(results['new_launches'])
            
            # Save session statistics
            stats_file = f"{self.config.output_directory}/session_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(stats_file, 'w') as f:
                json.dump(results['statistics'], f, indent=2, default=str)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error during full scrape: {e}")
            raise


# Compatibility functions for existing CLI interfaces
async def get_new_launches(config: ScraperConfig, hours: int = 24) -> List[TokenInfo]:
    """Get new launches from the last N hours"""
    async with PumpPortalScraper(config) as scraper:
        # Collect data for a shorter period to get recent launches
        results = await scraper.collect_data(duration_seconds=min(300, hours * 60))
        
        # Filter launches within the specified timeframe
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_launches = [
            token for token in results['new_launches']
            if token.created_timestamp and token.created_timestamp > cutoff_time
        ]
        
        return recent_launches


async def get_tokens_api(config: ScraperConfig, limit: int = 50) -> List[TokenInfo]:
    """Get token information via real-time API"""
    async with PumpPortalScraper(config) as scraper:
        # Collect data for a reasonable period to gather tokens
        results = await scraper.collect_data(duration_seconds=min(600, config.data_collection_duration))
        
        # Return limited results
        tokens = list(results['tokens'][:limit])
        return tokens


async def get_token_transactions(config: ScraperConfig, mint_address: str, limit: int = 100) -> List[TransactionData]:
    """Get transactions for specific token"""
    async with PumpPortalScraper(config) as scraper:
        # Start connection
        if await scraper.connect_websocket():
            # Subscribe to specific token trades
            subscription = {
                "method": "subscribeTokenTrade",
                "keys": [mint_address]
            }
            await scraper.websocket.send(json.dumps(subscription))
            
            # Collect data for specific token
            results = await scraper.collect_data(duration_seconds=min(300, config.data_collection_duration))
            
            # Filter transactions for the specific token
            token_transactions = [
                tx for tx in results['transactions']
                if tx.token_mint == mint_address
            ]
            
            return token_transactions[:limit]
    
    return []


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="PumpPortal.fun Official API Scraper")
    parser.add_argument("--config", "-c", default="config.yaml", help="Configuration file")
    parser.add_argument("--duration", "-d", type=int, help="Data collection duration in seconds")
    parser.add_argument("--api-key", help="PumpPortal API key")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    # Load configuration
    config = ScraperConfig.load(args.config)
    
    # Apply CLI overrides
    if args.duration:
        config.data_collection_duration = args.duration
    if args.api_key:
        config.api_key = args.api_key
    if args.verbose:
        config.log_level = "DEBUG"
    
    # Run scraper
    async def main():
        async with PumpPortalScraper(config) as scraper:
            results = await scraper.run_full_scrape()
            print(f"✓ Collected {len(results['tokens'])} tokens and {len(results['transactions'])} transactions")
    
    asyncio.run(main())