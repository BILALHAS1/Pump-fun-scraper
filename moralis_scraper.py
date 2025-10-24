#!/usr/bin/env python3
"""
Moralis API Data Scraper for Pump.fun

This script uses the Moralis Web3 Data API to collect token information, 
transaction data, and trading activity from pump.fun with proper error handling.
"""

import asyncio
import logging
import signal
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set

from config import ScraperConfig
from models import TokenInfo, TransactionData
from moralis_client import MoralisClient
from utils.data_storage import DataStorage
from utils.logger import setup_logger


class MoralisScraper:
    """Pump.fun data scraper using Moralis Web3 Data API"""
    
    def __init__(self, config: ScraperConfig):
        self.config = config
        self.logger = setup_logger(__name__, config.log_level)
        self.data_storage = DataStorage(config.output_directory)
        
        # Validate Moralis API key
        if not config.moralis_api_key:
            raise ValueError(
                "Moralis API key is required. "
                "Get one at https://moralis.io and set it in config.yaml as 'moralis_api_key'"
            )
        
        # Moralis client
        self.moralis_client: Optional[MoralisClient] = None
        
        # Data collection
        self.collected_tokens: Dict[str, TokenInfo] = {}
        self.collected_transactions: List[TransactionData] = []
        self.new_launches: List[TokenInfo] = []
        self._seen_transaction_signatures: Set[str] = set()
        self._seen_launch_mints: Set[str] = set()
        
        # Statistics
        self.session_start = datetime.now()
        self.messages_received = 0
        self.api_requests = 0
        self.api_errors = 0
        
        # Control
        self.should_continue = True
        self._shutdown_event = asyncio.Event()
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            self.should_continue = False
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
        self.logger.info("Initializing Moralis pump.fun scraper...")
        self.logger.info(f"Moralis API URL: {self.config.moralis_base_url}")
        self.logger.info("Using Moralis Web3 Data API for Solana/Pump.fun")
        
        # Initialize Moralis client
        self.moralis_client = MoralisClient(
            api_key=self.config.moralis_api_key,
            timeout=self.config.timeout_seconds,
            logger=self.logger
        )
    
    async def cleanup(self):
        """Clean up resources"""
        self.should_continue = False
        if self.moralis_client:
            await self.moralis_client.__aexit__(None, None, None)
        self.logger.info("Scraper cleanup completed")
    
    async def fetch_and_process_tokens(self) -> int:
        """
        Fetch and process tokens from Moralis API
        
        Returns:
            Number of new tokens processed
        """
        try:
            self.logger.debug("Fetching tokens from Moralis API...")
            
            async with self.moralis_client:
                # Get tokens sorted by creation date (newest first)
                raw_tokens = await self.moralis_client.get_pump_fun_tokens(
                    limit=self.config.api_page_size,
                    sort_by="created_at",
                    order="desc",
                )
                
                self.api_requests += 1
                new_count = 0
                
                for raw_token in raw_tokens:
                    token = self.moralis_client.parse_token(raw_token)
                    
                    if not token or not token.mint_address:
                        continue
                    
                    # Check if this is a new token
                    is_new = token.mint_address not in self.collected_tokens
                    
                    # Check if it's a new launch (within configured timeframe)
                    is_new_launch = False
                    if token.created_timestamp:
                        age = datetime.now() - token.created_timestamp
                        is_new_launch = age < timedelta(hours=self.config.new_launches_hours)
                    
                    # Update collected tokens
                    self.collected_tokens[token.mint_address] = token
                    
                    # Add to new launches if applicable
                    if is_new_launch and token.mint_address not in self._seen_launch_mints:
                        self.new_launches.append(token)
                        self._seen_launch_mints.add(token.mint_address)
                        self.logger.info(
                            f"New token: {token.name or 'Unknown'} ({token.symbol}) - "
                            f"${token.price:.6f} | MC: ${token.market_cap:,.0f}"
                        )
                    
                    if is_new:
                        new_count += 1
                
                self.logger.debug(f"Processed {len(raw_tokens)} tokens, {new_count} new")
                return new_count
                
        except Exception as e:
            self.logger.error(f"Error fetching tokens: {e}")
            self.api_errors += 1
            return 0
    
    async def fetch_and_process_trades(self, limit: int = 100) -> int:
        """
        Fetch and process recent trades from Moralis API
        
        Args:
            limit: Maximum number of trades to fetch
            
        Returns:
            Number of new trades processed
        """
        if limit <= 0:
            self.logger.debug("Trade fetch limit is non-positive; skipping fetch")
            return 0
        
        try:
            self.logger.debug("Fetching trades from Moralis API using token mint addresses...")
            
            if not self.collected_tokens:
                self.logger.debug("No tokens collected yet; skipping trade fetch")
                return 0
            
            tokens_to_process = list(self.collected_tokens.values())
            if not tokens_to_process:
                return 0
            
            if not self.moralis_client:
                self.logger.error("Moralis client is not initialized")
                return 0
            
            max_tokens = max(1, self.config.max_tokens_for_transactions)
            tokens_to_process = tokens_to_process[:max_tokens]
            
            total_new_trades = 0
            remaining_limit = limit
            
            async with self.moralis_client:
                for index, token in enumerate(tokens_to_process):
                    if remaining_limit <= 0:
                        break
                    
                    tokens_remaining = len(tokens_to_process) - index
                    per_token_limit = self.config.transactions_per_token
                    if remaining_limit:
                        per_token_limit = min(
                            self.config.transactions_per_token,
                            max(1, remaining_limit // tokens_remaining)
                        )
                    
                    token_symbol = token.symbol or token.mint_address
                    mint_address = token.mint_address
                    self.logger.debug(
                        "Fetching up to %s trades for token %s (%s)",
                        per_token_limit,
                        token_symbol,
                        mint_address,
                    )
                    
                    try:
                        raw_trades = await self.moralis_client.get_token_trades(
                            mint_address=mint_address,
                            limit=per_token_limit,
                        )
                        self.api_requests += 1
                    except Exception as token_error:
                        self.logger.error(
                            f"Trade fetch error for token {mint_address}: {token_error}"
                        )
                        self.api_errors += 1
                        continue
                    
                    if remaining_limit:
                        remaining_limit = max(0, remaining_limit - len(raw_trades))
                    
                    for raw_trade in raw_trades:
                        transaction = self.moralis_client.parse_transaction(raw_trade)
                        
                        if not transaction or not transaction.signature:
                            continue
                        
                        if transaction.signature in self._seen_transaction_signatures:
                            continue
                        
                        self.collected_transactions.append(transaction)
                        self._seen_transaction_signatures.add(transaction.signature)
                        total_new_trades += 1
            
            self.logger.debug(
                f"Processed trades for {len(tokens_to_process)} tokens, {total_new_trades} new"
            )
            return total_new_trades
            
        except Exception as e:
            self.logger.error(f"Error fetching trades: {e}")
            self.api_errors += 1
            return 0
    
    async def poll_data(self):
        """
        Poll data from Moralis API at regular intervals
        """
        poll_interval = self.config.moralis_poll_interval
        save_interval = 20  # Save data every 20 seconds
        stats_interval = 30  # Show statistics every 30 seconds
        
        last_save = time.time()
        last_stats = time.time()
        poll_count = 0
        
        self.logger.info(f"Starting continuous data collection (polling every {poll_interval}s)...")
        self.logger.info("Press Ctrl+C to stop")
        
        while self.should_continue:
            try:
                poll_start = time.time()
                poll_count += 1
                
                # Fetch tokens and trades in parallel
                token_task = self.fetch_and_process_tokens()
                trade_task = self.fetch_and_process_trades()
                
                new_tokens, new_trades = await asyncio.gather(
                    token_task,
                    trade_task,
                    return_exceptions=True
                )
                
                # Handle exceptions from tasks
                if isinstance(new_tokens, Exception):
                    self.logger.error(f"Token fetch error: {new_tokens}")
                    new_tokens = 0
                if isinstance(new_trades, Exception):
                    self.logger.error(f"Trade fetch error: {new_trades}")
                    new_trades = 0
                
                current_time = time.time()
                
                # Save data periodically
                if current_time - last_save >= save_interval:
                    await self._save_data()
                    last_save = current_time
                
                # Show statistics periodically
                if current_time - last_stats >= stats_interval:
                    self._show_statistics()
                    last_stats = current_time
                
                # Calculate sleep time to maintain polling interval
                poll_duration = time.time() - poll_start
                sleep_time = max(0, poll_interval - poll_duration)
                
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                
            except asyncio.CancelledError:
                self.logger.info("Polling cancelled")
                break
            except Exception as e:
                self.logger.error(f"Error in polling loop: {e}")
                await asyncio.sleep(poll_interval)
        
        self.logger.info("Data collection stopped")
    
    async def _save_data(self):
        """Save collected data to storage"""
        try:
            if self.collected_tokens:
                tokens_list = list(self.collected_tokens.values())
                await self.data_storage.save_tokens(
                    tokens_list,
                    format_type=self.config.output_format,
                )
                self.logger.debug(f"Saved {len(tokens_list)} tokens")
            
            if self.collected_transactions:
                await self.data_storage.save_transactions(
                    self.collected_transactions,
                    format_type=self.config.output_format,
                )
                self.logger.debug(f"Saved {len(self.collected_transactions)} transactions")
            
            if self.new_launches:
                await self.data_storage.save_new_launches(
                    self.new_launches,
                    format_type=self.config.output_format,
                )
                self.logger.debug(f"Saved {len(self.new_launches)} new launches")
                
        except Exception as e:
            self.logger.error(f"Error saving data: {e}")
    
    def _show_statistics(self):
        """Display current statistics"""
        uptime = (datetime.now() - self.session_start).total_seconds()
        hours = int(uptime // 3600)
        minutes = int((uptime % 3600) // 60)
        seconds = int(uptime % 60)
        
        self.logger.info(
            f"📊 Stats - Uptime: {hours}h {minutes}m {seconds}s | "
            f"Tokens: {len(self.collected_tokens)} | "
            f"Transactions: {len(self.collected_transactions)} | "
            f"New Launches: {len(self.new_launches)} | "
            f"API Requests: {self.api_requests} | "
            f"Errors: {self.api_errors}"
        )
    
    async def collect_data(self, duration_seconds: Optional[int] = None) -> Dict[str, Any]:
        """
        Collect data from Moralis API for specified duration
        
        Args:
            duration_seconds: Duration to collect data (None for continuous)
            
        Returns:
            Dictionary with collected data and statistics
        """
        self.logger.info("Starting data collection...")
        
        if duration_seconds:
            self.logger.info(f"Collection duration: {duration_seconds} seconds")
            
            # Run polling for specified duration
            try:
                await asyncio.wait_for(self.poll_data(), timeout=duration_seconds)
            except asyncio.TimeoutError:
                self.logger.info("Collection duration reached")
        else:
            # Run continuously until stopped
            await self.poll_data()
        
        # Final save
        await self._save_data()
        
        # Calculate session duration
        session_duration = (datetime.now() - self.session_start).total_seconds()
        
        # Prepare results
        results = {
            'tokens': list(self.collected_tokens.values()),
            'transactions': self.collected_transactions,
            'new_launches': self.new_launches,
            'migrations': [],  # Moralis might not have migration events
            'statistics': {
                'session_duration': session_duration,
                'messages_received': self.messages_received,
                'api_requests': self.api_requests,
                'connection_errors': self.api_errors,
                'reconnection_attempts': 0,
                'tokens_collected': len(self.collected_tokens),
                'transactions_collected': len(self.collected_transactions),
                'new_launches': len(self.new_launches),
                'migrations': 0,
            }
        }
        
        self.logger.info("Data collection completed")
        return results
