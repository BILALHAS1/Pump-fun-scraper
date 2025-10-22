#!/usr/bin/env python3
"""
Pump.fun Comprehensive Data Scraper

This script scrapes token information, transaction data, and trading activity
from pump.fun platform with proper rate limiting and error handling.
"""

import asyncio
import json
import csv
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import argparse

import httpx
import aiofiles
from playwright.async_api import async_playwright, Page, Browser

from config import ScraperConfig
from models import TokenInfo, TransactionData
from utils.rate_limiter import RateLimiter
from utils.data_storage import DataStorage
from utils.logger import setup_logger


class PumpFunScraper:
    """Main scraper class for pump.fun platform"""
    
    def __init__(self, config: ScraperConfig):
        self.config = config
        self.logger = setup_logger(__name__, config.log_level)
        self.rate_limiter = RateLimiter(
            requests_per_minute=config.rate_limit_rpm,
            requests_per_hour=config.rate_limit_rph
        )
        self.data_storage = DataStorage(config.output_directory)
        self.session: Optional[httpx.AsyncClient] = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.cleanup()
    
    async def initialize(self):
        """Initialize the scraper with HTTP client and browser if needed"""
        # Initialize HTTP client
        self.session = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            headers={
                "User-Agent": self.config.user_agent,
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache"
            },
            follow_redirects=True
        )
        
        # Initialize browser for web scraping if API fails
        if self.config.use_browser_fallback:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(
                headless=self.config.headless_browser
            )
            context = await self.browser.new_context(
                user_agent=self.config.user_agent,
                viewport={"width": 1920, "height": 1080}
            )
            self.page = await context.new_page()
        
        self.logger.info("Scraper initialized successfully")
    
    async def cleanup(self):
        """Clean up resources"""
        if self.session:
            await self.session.aclose()
        
        if self.browser:
            await self.browser.close()
        
        self.logger.info("Scraper cleanup completed")
    
    async def get_tokens_api(self, offset: int = 0, limit: int = 50) -> List[TokenInfo]:
        """
        Fetch token information using API calls
        """
        await self.rate_limiter.wait_if_needed()
        
        try:
            url = f"{self.config.api_base_url}/coins"
            params = {
                "offset": offset,
                "limit": limit,
                "sort": "created_timestamp",
                "order": "DESC"
            }
            
            self.logger.debug(f"Fetching tokens from API: {url}")
            response = await self.session.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                tokens = []
                
                for coin_data in data.get("coins", []):
                    token = self._parse_token_data(coin_data)
                    if token:
                        tokens.append(token)
                
                self.logger.info(f"Successfully fetched {len(tokens)} tokens via API")
                return tokens
            
            else:
                self.logger.warning(f"API request failed with status {response.status_code}")
                return []
        
        except Exception as e:
            self.logger.error(f"Error fetching tokens via API: {e}")
            return []
    
    async def get_tokens_web_scraping(self, max_tokens: int = 100) -> List[TokenInfo]:
        """
        Fetch token information using web scraping as fallback
        """
        if not self.page:
            self.logger.error("Browser not initialized for web scraping")
            return []
        
        await self.rate_limiter.wait_if_needed()
        
        try:
            self.logger.info("Starting web scraping for tokens")
            await self.page.goto(self.config.base_url, wait_until="networkidle")
            
            tokens = []
            scroll_count = 0
            max_scrolls = max_tokens // 20  # Approximate tokens per scroll
            
            while scroll_count < max_scrolls:
                # Extract token cards from current view
                token_elements = await self.page.query_selector_all('[data-testid="coin-card"]')
                
                for element in token_elements:
                    token_data = await self._extract_token_from_element(element)
                    if token_data and token_data not in tokens:
                        tokens.append(token_data)
                
                # Scroll to load more tokens
                await self.page.keyboard.press("End")
                await asyncio.sleep(2)  # Wait for new content to load
                scroll_count += 1
                
                if len(tokens) >= max_tokens:
                    break
            
            self.logger.info(f"Successfully scraped {len(tokens)} tokens")
            return tokens[:max_tokens]
        
        except Exception as e:
            self.logger.error(f"Error during web scraping: {e}")
            return []
    
    async def get_token_transactions(self, mint_address: str, limit: int = 100) -> List[TransactionData]:
        """
        Fetch transaction data for a specific token
        """
        await self.rate_limiter.wait_if_needed()
        
        try:
            url = f"{self.config.api_base_url}/trades/{mint_address}"
            params = {"limit": limit}
            
            response = await self.session.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                transactions = []
                
                for trade_data in data.get("trades", []):
                    transaction = self._parse_transaction_data(trade_data, mint_address)
                    if transaction:
                        transactions.append(transaction)
                
                self.logger.info(f"Fetched {len(transactions)} transactions for token {mint_address}")
                return transactions
            
            else:
                self.logger.warning(f"Transaction API request failed with status {response.status_code}")
                return []
        
        except Exception as e:
            self.logger.error(f"Error fetching transactions for {mint_address}: {e}")
            return []
    
    async def get_new_launches(self, hours: int = 24) -> List[TokenInfo]:
        """
        Get newly launched tokens within specified hours
        """
        try:
            all_tokens = await self.get_tokens_api(limit=200)
            
            # Filter tokens created in the last N hours
            cutoff_time = datetime.now().timestamp() - (hours * 3600)
            new_launches = []
            
            for token in all_tokens:
                if token.created_timestamp and token.created_timestamp.timestamp() > cutoff_time:
                    new_launches.append(token)
            
            self.logger.info(f"Found {len(new_launches)} new launches in last {hours} hours")
            return new_launches
        
        except Exception as e:
            self.logger.error(f"Error fetching new launches: {e}")
            return []
    
    def _parse_token_data(self, coin_data: Dict[str, Any]) -> Optional[TokenInfo]:
        """Parse raw coin data into TokenInfo model"""
        try:
            return TokenInfo(
                name=coin_data.get("name", ""),
                symbol=coin_data.get("symbol", ""),
                price=float(coin_data.get("usd_market_cap", 0)) / float(coin_data.get("supply", 1)),
                market_cap=float(coin_data.get("usd_market_cap", 0)),
                volume_24h=float(coin_data.get("volume_24h", 0)),
                created_timestamp=datetime.fromtimestamp(coin_data.get("created_timestamp", 0)),
                mint_address=coin_data.get("mint", ""),
                description=coin_data.get("description", ""),
                image_uri=coin_data.get("image_uri", ""),
                twitter=coin_data.get("twitter", ""),
                telegram=coin_data.get("telegram", ""),
                website=coin_data.get("website", "")
            )
        except Exception as e:
            self.logger.error(f"Error parsing token data: {e}")
            return None
    
    def _parse_transaction_data(self, trade_data: Dict[str, Any], mint_address: str) -> Optional[TransactionData]:
        """Parse raw transaction data into TransactionData model"""
        try:
            return TransactionData(
                signature=trade_data.get("signature", ""),
                token_mint=mint_address,
                action=trade_data.get("is_buy", True) and "buy" or "sell",
                amount=float(trade_data.get("token_amount", 0)),
                price=float(trade_data.get("sol_amount", 0)),
                user=trade_data.get("user", ""),
                timestamp=datetime.fromtimestamp(trade_data.get("timestamp", 0))
            )
        except Exception as e:
            self.logger.error(f"Error parsing transaction data: {e}")
            return None
    
    async def _extract_token_from_element(self, element) -> Optional[TokenInfo]:
        """Extract token information from web element"""
        try:
            # This would need to be customized based on actual HTML structure
            name = await element.query_selector(".token-name")
            symbol = await element.query_selector(".token-symbol")
            price_element = await element.query_selector(".token-price")
            
            if name and symbol:
                name_text = await name.text_content()
                symbol_text = await symbol.text_content()
                price_text = await price_element.text_content() if price_element else "0"
                
                return TokenInfo(
                    name=name_text.strip(),
                    symbol=symbol_text.strip(),
                    price=float(price_text.replace("$", "").replace(",", "") or 0),
                    market_cap=0.0,  # Would need additional scraping
                    volume_24h=0.0   # Would need additional scraping
                )
        except Exception as e:
            self.logger.error(f"Error extracting token from element: {e}")
            return None
    
    async def run_full_scrape(self) -> Dict[str, Any]:
        """
        Run a comprehensive scraping session
        """
        results = {
            "tokens": [],
            "transactions": [],
            "new_launches": [],
            "scrape_timestamp": datetime.now()
        }
        
        try:
            self.logger.info("Starting comprehensive pump.fun scrape")
            
            # 1. Get all tokens (try API first, fallback to web scraping)
            tokens = await self.get_tokens_api(limit=self.config.max_tokens)
            
            if not tokens and self.config.use_browser_fallback:
                self.logger.info("API failed, falling back to web scraping")
                tokens = await self.get_tokens_web_scraping(self.config.max_tokens)
            
            results["tokens"] = tokens
            
            # 2. Get transactions for top tokens
            top_tokens = tokens[:self.config.max_tokens_for_transactions]
            all_transactions = []
            
            for token in top_tokens:
                if token.mint_address:
                    transactions = await self.get_token_transactions(
                        token.mint_address, 
                        self.config.transactions_per_token
                    )
                    all_transactions.extend(transactions)
                    await asyncio.sleep(1)  # Rate limiting between requests
            
            results["transactions"] = all_transactions
            
            # 3. Get new launches
            new_launches = await self.get_new_launches(self.config.new_launches_hours)
            results["new_launches"] = new_launches
            
            # 4. Save all data
            await self.data_storage.save_tokens(tokens)
            await self.data_storage.save_transactions(all_transactions)
            await self.data_storage.save_new_launches(new_launches)
            
            self.logger.info(
                f"Scrape completed: {len(tokens)} tokens, "
                f"{len(all_transactions)} transactions, "
                f"{len(new_launches)} new launches"
            )
            
            return results
        
        except Exception as e:
            self.logger.error(f"Error during full scrape: {e}")
            raise


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Pump.fun Data Scraper")
    parser.add_argument("--config", "-c", default="config.yaml", help="Configuration file path")
    parser.add_argument("--tokens-only", action="store_true", help="Only scrape token information")
    parser.add_argument("--transactions-only", action="store_true", help="Only scrape transaction data")
    parser.add_argument("--new-launches", action="store_true", help="Only scrape new launches")
    parser.add_argument("--max-tokens", type=int, help="Maximum number of tokens to scrape")
    
    args = parser.parse_args()
    
    # Load configuration
    config = ScraperConfig.load(args.config)
    
    # Override config with command line arguments
    if args.max_tokens:
        config.max_tokens = args.max_tokens
    
    # Run scraper
    async with PumpFunScraper(config) as scraper:
        if args.tokens_only:
            tokens = await scraper.get_tokens_api(limit=config.max_tokens)
            await scraper.data_storage.save_tokens(tokens)
            print(f"Scraped {len(tokens)} tokens")
        
        elif args.transactions_only:
            # This would need token addresses as input
            print("Transaction-only mode requires specific token addresses")
        
        elif args.new_launches:
            new_launches = await scraper.get_new_launches(config.new_launches_hours)
            await scraper.data_storage.save_new_launches(new_launches)
            print(f"Found {len(new_launches)} new launches")
        
        else:
            results = await scraper.run_full_scrape()
            print(f"Full scrape completed:")
            print(f"  Tokens: {len(results['tokens'])}")
            print(f"  Transactions: {len(results['transactions'])}")
            print(f"  New Launches: {len(results['new_launches'])}")


if __name__ == "__main__":
    asyncio.run(main())