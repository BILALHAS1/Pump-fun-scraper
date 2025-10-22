#!/usr/bin/env python3
"""
Pump.fun Comprehensive Data Scraper

This script scrapes token information, transaction data, and trading activity
from pump.fun platform with proper rate limiting and error handling.
"""

import argparse
import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode, urlparse

import httpx
from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright

from config import ScraperConfig
from models import TokenInfo, TransactionData
from utils.data_storage import DataStorage
from utils.logger import setup_logger
from utils.rate_limiter import AdaptiveRateLimiter


class PumpFunScraper:
    """Main scraper class for pump.fun platform"""
    
    def __init__(self, config: ScraperConfig):
        self.config = config
        self.logger = setup_logger(__name__, config.log_level)
        self.rate_limiter = AdaptiveRateLimiter(
            requests_per_minute=config.rate_limit_rpm,
            requests_per_hour=config.rate_limit_rph
        )
        self.data_storage = DataStorage(config.output_directory)
        self.session: Optional[httpx.AsyncClient] = None
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.browser_context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self._api_headers = self._build_api_headers()
        self._last_cookie_sync: Optional[datetime] = None
    
    def _build_api_headers(self) -> Dict[str, str]:
        """Construct default headers for pump.fun requests."""
        headers = {
            "User-Agent": self.config.user_agent,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Connection": "keep-alive",
            "Origin": self.config.base_url,
            "Referer": f"{self.config.base_url}/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
        }
        if self.config.api_extra_headers:
            headers.update(self.config.api_extra_headers)
        return headers
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.cleanup()
    
    async def initialize(self):
        """Initialize the scraper with HTTP client and browser if needed"""
        client_kwargs: Dict[str, Any] = {
            "timeout": httpx.Timeout(self.config.timeout_seconds),
            "headers": self._api_headers.copy(),
            "follow_redirects": True,
            "http2": True,
        }
        
        if self.config.proxy_url:
            client_kwargs["proxies"] = self.config.proxy_url
            self.logger.info("Using proxy for API requests")
        
        self.session = httpx.AsyncClient(**client_kwargs)
        
        if self.config.use_browser_fallback:
            await self._ensure_browser()
            if self.config.preload_browser_cookies:
                await self._refresh_session_with_browser(force_reload=True)
        
        self.logger.info("Scraper initialized successfully")
    
    async def cleanup(self):
        """Clean up resources"""
        if self.session:
            await self.session.aclose()
            self.session = None
        
        if self.page:
            await self.page.close()
            self.page = None
        
        if self.browser_context:
            await self.browser_context.close()
            self.browser_context = None
        
        if self.browser:
            await self.browser.close()
            self.browser = None
        
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
        
        self._last_cookie_sync = None
        
        self.logger.info("Scraper cleanup completed")
    
    async def _ensure_browser(self):
        """Ensure the Playwright browser context is ready."""
        if not self.config.use_browser_fallback:
            raise RuntimeError("Browser fallback is disabled in configuration")
        
        if not self.playwright:
            self.playwright = await async_playwright().start()
        
        if not self.browser:
            launch_args: Dict[str, Any] = {
                "headless": self.config.headless_browser,
            }
            if self.config.playwright_proxy:
                launch_args["proxy"] = {"server": self.config.playwright_proxy}
                self.logger.info("Using proxy for Playwright browser")
            self.browser = await self.playwright.chromium.launch(**launch_args)
        
        if not self.browser_context:
            context_headers = {
                key: value for key, value in self._api_headers.items()
                if key.lower() not in {"content-length"}
            }
            self.browser_context = await self.browser.new_context(
                user_agent=self.config.user_agent,
                viewport={"width": 1920, "height": 1080},
                extra_http_headers=context_headers,
            )
        
        if not self.page:
            self.page = await self.browser_context.new_page()
    
    async def _refresh_session_with_browser(self, force_reload: bool = False):
        """Open pump.fun in the browser and sync cookies to the HTTP client."""
        if not self.config.use_browser_fallback:
            return
        
        await self._ensure_browser()
        should_refresh = force_reload
        if self._last_cookie_sync is None:
            should_refresh = True
        else:
            elapsed = (datetime.now() - self._last_cookie_sync).total_seconds()
            if elapsed > self.config.cookie_sync_interval:
                should_refresh = True
        
        if should_refresh:
            await self.page.goto(self.config.base_url, wait_until="networkidle")
            await self.page.wait_for_timeout(int(self.config.browser_page_settle_delay * 1000))
            await self._sync_cookies_from_browser()
        elif self.session and not self.session.cookies:
            await self._sync_cookies_from_browser()
    
    async def _sync_cookies_from_browser(self):
        """Copy cookies from Playwright browser context to httpx session."""
        if not self.browser_context or not self.session:
            return
        
        cookies = await self.browser_context.cookies()
        if not cookies:
            return
        
        jar = httpx.Cookies()
        base_domain = urlparse(self.config.base_url).hostname or "pump.fun"
        for cookie in cookies:
            domain = (cookie.get("domain") or base_domain).lstrip(".")
            jar.set(
                cookie.get("name"),
                cookie.get("value"),
                domain=domain,
                path=cookie.get("path", "/"),
            )
        self.session.cookies.clear()
        self.session.cookies.update(jar)
        self._last_cookie_sync = datetime.now()
        self.logger.debug("Synchronized browser cookies with HTTP session")
    
    async def _browser_fetch_json(self, url: str, params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """Fetch JSON using the Playwright page context (with cookies)."""
        await self._refresh_session_with_browser(force_reload=False)
        if not self.page:
            return None
        
        request_url = url
        if params:
            query = urlencode([(key, str(value)) for key, value in params.items() if value is not None])
            if query:
                separator = "&" if "?" in request_url else "?"
                request_url = f"{request_url}{separator}{query}"
        
        fetch_headers = {
            key: value for key, value in self._api_headers.items()
            if key.lower() not in {"accept-encoding", "content-length"}
        }
        script = """
            async ({ url, headers }) => {
                const response = await fetch(url, {
                    method: 'GET',
                    headers,
                    credentials: 'include',
                });
                const text = await response.text();
                try {
                    return JSON.parse(text);
                } catch (error) {
                    return { "__error": "invalid_json", "message": error.message, "raw": text };
                }
            }
        """
        result = await self.page.evaluate(
            script,
            {"url": request_url, "headers": fetch_headers},
            timeout=self.config.browser_request_timeout_ms,
        )
        if isinstance(result, dict) and result.get("__error") == "invalid_json":
            self.logger.error(f"Browser fetch returned non-JSON content from {request_url}")
            return None
        return result
    
    async def _request_with_retries(
        self,
        method: str,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        json_body: Any = None,
        data: Any = None,
    ) -> Optional[httpx.Response]:
        """Perform an HTTP request with retry and exponential backoff."""
        if not self.session:
            return None
        
        retries = max(1, self.config.max_retries)
        backoff = self.config.retry_delay
        last_exception: Optional[Exception] = None
        
        for attempt in range(1, retries + 1):
            try:
                request_headers = self._api_headers.copy()
                if headers:
                    request_headers.update(headers)
                
                await self.rate_limiter.wait_if_needed()
                response = await self.session.request(
                    method,
                    url,
                    params=params,
                    headers=request_headers,
                    json=json_body,
                    data=data,
                )
                
                if hasattr(self.rate_limiter, "record_response"):
                    await self.rate_limiter.record_response(
                        response.status_code,
                        error=response.status_code >= 500,
                    )
                
                if response.status_code == 200:
                    return response
                
                if response.status_code in {401, 403, 429, 500, 502, 503, 504, 520, 522, 525, 530}:
                    self.logger.warning(
                        f"Request to {url} returned {response.status_code} (attempt {attempt}/{retries})"
                    )
                    if response.status_code == 530 and self.config.use_browser_fallback:
                        await self._refresh_session_with_browser(force_reload=True)
                    if attempt < retries:
                        await asyncio.sleep(min(backoff, self.config.max_retry_backoff))
                        backoff = min(backoff * 2, self.config.max_retry_backoff)
                        continue
                else:
                    response.raise_for_status()
                    return response
            except httpx.RequestError as exc:
                last_exception = exc
                self.logger.warning(
                    f"Request error (attempt {attempt}/{retries}) for {url}: {exc}"
                )
                if hasattr(self.rate_limiter, "record_response"):
                    await self.rate_limiter.record_response(0, error=True)
                if attempt < retries:
                    if self.config.use_browser_fallback:
                        await self._refresh_session_with_browser(force_reload=False)
                    await asyncio.sleep(min(backoff, self.config.max_retry_backoff))
                    backoff = min(backoff * 2, self.config.max_retry_backoff)
                    continue
            except Exception as exc:
                last_exception = exc
                self.logger.error(f"Unexpected error during request to {url}: {exc}")
                if attempt < retries:
                    await asyncio.sleep(min(backoff, self.config.max_retry_backoff))
                    backoff = min(backoff * 2, self.config.max_retry_backoff)
                    continue
                break
        
        if last_exception:
            self.logger.error(f"Failed to complete request to {url}: {last_exception}")
        return None
    
    def _parse_tokens_from_data(self, data: Any) -> List[TokenInfo]:
        """Extract TokenInfo models from API/browser response."""
        if not data:
            return []
        
        if isinstance(data, dict):
            possible_lists = [
                data.get("coins"),
                data.get("data"),
                data.get("items"),
                data.get("result"),
                data.get("results"),
            ]
            coins = None
            for value in possible_lists:
                if isinstance(value, list):
                    coins = value
                    break
                if isinstance(value, dict):
                    nested = value.get("items") or value.get("data")
                    if isinstance(nested, list):
                        coins = nested
                        break
            if coins is None and {"name", "mint"}.issubset(data.keys()):
                coins = [data]
            elif coins is None:
                coins = []
        elif isinstance(data, list):
            coins = data
        else:
            coins = []
        
        tokens: Dict[str, TokenInfo] = {}
        for coin in coins:
            if not isinstance(coin, dict):
                continue
            token = self._parse_token_data(coin)
            if not token:
                continue
            key = token.mint_address or f"{token.name}:{token.symbol}:{len(tokens)}"
            if key not in tokens:
                tokens[key] = token
        return list(tokens.values())
    
    def _parse_transactions_from_data(self, data: Any, mint_address: str) -> List[TransactionData]:
        """Extract TransactionData models from response payload."""
        if not data:
            return []
        
        if isinstance(data, dict):
            trades = (
                data.get("trades")
                or data.get("data")
                or data.get("items")
                or data.get("results")
            )
            if isinstance(trades, dict):
                trades = trades.get("items") or trades.get("data")
            if not isinstance(trades, list):
                trades = []
        elif isinstance(data, list):
            trades = data
        else:
            trades = []
        
        results: List[TransactionData] = []
        for trade in trades:
            if not isinstance(trade, dict):
                continue
            transaction = self._parse_transaction_data(trade, mint_address)
            if transaction:
                results.append(transaction)
        return results
    
    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        """Safely convert a value to float without raising exceptions."""
        if value is None:
            return default
        try:
            if isinstance(value, str):
                cleaned = value.strip()
                if not cleaned:
                    return default
                cleaned = cleaned.replace(",", "")
                if cleaned.endswith("%"):
                    cleaned = cleaned[:-1]
                return float(cleaned)
            return float(value)
        except (TypeError, ValueError):
            return default
    
    def _parse_timestamp(self, value: Any) -> Optional[datetime]:
        """Parse timestamps from multiple possible formats."""
        if value is None:
            return None
        
        if isinstance(value, datetime):
            return value
        
        try:
            if isinstance(value, (int, float)):
                timestamp = value / 1000 if value > 1_000_000_000_000 else value
                return datetime.fromtimestamp(timestamp)
            if isinstance(value, str):
                cleaned = value.strip()
                if not cleaned:
                    return None
                if cleaned.isdigit():
                    numeric = float(cleaned)
                    numeric = numeric / 1000 if numeric > 1_000_000_000_000 else numeric
                    return datetime.fromtimestamp(numeric)
                if cleaned.endswith("Z"):
                    cleaned = cleaned[:-1] + "+00:00"
                try:
                    return datetime.fromisoformat(cleaned)
                except ValueError:
                    for fmt in (
                        "%Y-%m-%dT%H:%M:%S.%f%z",
                        "%Y-%m-%dT%H:%M:%S%z",
                        "%Y-%m-%d %H:%M:%S",
                    ):
                        try:
                            return datetime.strptime(cleaned, fmt)
                        except ValueError:
                            continue
            return None
        except Exception:
            return None
    
    async def get_tokens_api(
        self,
        offset: int = 0,
        limit: int = 50,
        *,
        use_browser_fallback: bool = True
    ) -> List[TokenInfo]:
        """
        Fetch token information using API calls with retry and fallback support.
        """
        if not self.session:
            raise RuntimeError("HTTP session not initialized. Did you call initialize()?")
        
        url = f"{self.config.api_base_url}/coins"
        requested_limit = max(limit, 0)
        if requested_limit == 0:
            self.logger.debug("Token API requested with limit=0; returning empty list")
            return []
        
        next_offset = max(offset, 0)
        collected: Dict[str, TokenInfo] = {}
        
        while len(collected) < requested_limit:
            remaining = requested_limit - len(collected)
            page_limit = min(self.config.api_page_size, remaining) if remaining > 0 else self.config.api_page_size
            params = {
                "offset": next_offset,
                "limit": page_limit,
                "sort": "created_timestamp",
                "order": "DESC",
            }
            
            response = await self._request_with_retries("GET", url, params=params)
            if response is None:
                break
            
            try:
                data = response.json()
            except ValueError as exc:
                self.logger.error(f"Failed to decode token API response: {exc}")
                break
            
            page_tokens = self._parse_tokens_from_data(data)
            if not page_tokens:
                self.logger.warning("Token API returned no results for current page")
                break
            
            added = 0
            for token in page_tokens:
                if token.market_cap < self.config.min_market_cap:
                    continue
                if token.volume_24h < self.config.min_volume:
                    continue
                key = token.mint_address or f"{token.name}:{token.symbol}:{len(collected)}"
                if key not in collected:
                    collected[key] = token
                    added += 1
            
            next_offset += page_limit
            
            if len(page_tokens) < page_limit and added == 0:
                # No more data coming from API
                break
            
            if self.config.request_delay > 0 and len(collected) < requested_limit:
                await asyncio.sleep(self.config.request_delay)
        
        tokens = list(collected.values())
        if not tokens and use_browser_fallback and self.config.use_browser_fallback:
            self.logger.warning("API returned no tokens, attempting browser fallback")
            tokens = await self.get_tokens_web_scraping(requested_limit)
        
        if tokens:
            self.logger.info(f"Successfully fetched {len(tokens)} tokens via API")
        else:
            self.logger.error("Token API failed to return data after retries")
        
        return tokens[:requested_limit]
    
    async def get_tokens_web_scraping(self, max_tokens: int = 100) -> List[TokenInfo]:
        """
        Fetch token information using browser-based API calls as fallback.
        """
        if not self.config.use_browser_fallback:
            self.logger.error("Browser fallback requested but disabled in configuration")
            return []
        
        await self._ensure_browser()
        requested_limit = max(max_tokens, 0)
        if requested_limit == 0:
            return []
        
        url = f"{self.config.api_base_url}/coins"
        tokens: Dict[str, TokenInfo] = {}
        next_offset = 0
        
        try:
            while len(tokens) < requested_limit:
                remaining = requested_limit - len(tokens)
                page_limit = min(self.config.api_page_size, remaining)
                params = {
                    "offset": next_offset,
                    "limit": page_limit,
                    "sort": "created_timestamp",
                    "order": "DESC",
                }
                
                await self.rate_limiter.wait_if_needed()
                data = await self._browser_fetch_json(url, params=params)
                if not data:
                    break
                
                page_tokens = self._parse_tokens_from_data(data)
                if not page_tokens:
                    break
                
                for token in page_tokens:
                    if token.market_cap < self.config.min_market_cap:
                        continue
                    if token.volume_24h < self.config.min_volume:
                        continue
                    key = token.mint_address or f"{token.name}:{token.symbol}:{len(tokens)}"
                    if key not in tokens:
                        tokens[key] = token
                
                next_offset += page_limit
                
                if len(page_tokens) < page_limit:
                    break
                
                if self.config.request_delay > 0 and len(tokens) < requested_limit:
                    await asyncio.sleep(self.config.request_delay)
        except Exception as exc:
            self.logger.error(f"Browser fallback failed: {exc}")
            return []
        
        result = list(tokens.values())
        if result:
            self.logger.info(f"Successfully scraped {len(result)} tokens via browser fallback")
        else:
            self.logger.warning("Browser fallback did not return any tokens")
        
        return result[:requested_limit]
    
    async def get_token_transactions(self, mint_address: str, limit: int = 100) -> List[TransactionData]:
        """
        Fetch transaction data for a specific token
        """
        if not self.session:
            raise RuntimeError("HTTP session not initialized. Did you call initialize()?")
        
        if not mint_address:
            self.logger.error("Cannot fetch transactions without a mint address")
            return []
        
        url = f"{self.config.api_base_url}/trades/{mint_address}"
        requested_limit = max(limit, 0)
        params = {"limit": requested_limit}
        
        transactions: List[TransactionData] = []
        try:
            response = await self._request_with_retries("GET", url, params=params)
            data = response.json() if response else None
            transactions = self._parse_transactions_from_data(data, mint_address)
        except Exception as exc:
            self.logger.error(f"Error fetching transactions for {mint_address}: {exc}")
        
        if not transactions and self.config.use_browser_fallback:
            self.logger.warning(
                f"Transaction API returned no data for {mint_address}, attempting browser fallback"
            )
            try:
                await self._ensure_browser()
                browser_data = await self._browser_fetch_json(url, params=params)
                transactions = self._parse_transactions_from_data(browser_data, mint_address)
            except Exception as exc:
                self.logger.error(f"Browser fallback failed for transactions: {exc}")
                transactions = []
        
        if transactions:
            self.logger.info(f"Fetched {len(transactions)} transactions for token {mint_address}")
        else:
            self.logger.warning(f"No transactions found for token {mint_address}")
        
        return transactions[:requested_limit] if requested_limit else transactions
    
    async def get_new_launches(self, hours: int = 24) -> List[TokenInfo]:
        """
        Get newly launched tokens within specified hours
        """
        lookback_hours = hours or self.config.new_launches_hours
        try:
            token_limit = max(200, self.config.max_tokens)
            all_tokens = await self.get_tokens_api(limit=token_limit)
            if not all_tokens and self.config.use_browser_fallback:
                all_tokens = await self.get_tokens_web_scraping(token_limit)
            
            cutoff_time = datetime.now().timestamp() - (lookback_hours * 3600)
            new_launches = [
                token for token in all_tokens
                if token.created_timestamp and token.created_timestamp.timestamp() > cutoff_time
            ]
            
            self.logger.info(
                f"Found {len(new_launches)} new launches in last {lookback_hours} hours"
            )
            return new_launches
        except Exception as e:
            self.logger.error(f"Error fetching new launches: {e}")
            return []
    
    def _parse_token_data(self, coin_data: Dict[str, Any]) -> Optional[TokenInfo]:
        """Parse raw coin data into TokenInfo model"""
        if not isinstance(coin_data, dict):
            return None
        
        try:
            name = (coin_data.get("name")
                    or coin_data.get("token_name")
                    or coin_data.get("coin_name")
                    or "").strip()
            symbol = (coin_data.get("symbol")
                      or coin_data.get("ticker")
                      or coin_data.get("token_symbol")
                      or "").strip()
            market_cap = self._safe_float(
                coin_data.get("usd_market_cap")
                or coin_data.get("market_cap")
                or coin_data.get("market_cap_usd")
                or coin_data.get("marketCap")
            )
            price = self._safe_float(
                coin_data.get("usd_price")
                or coin_data.get("price_usd")
                or coin_data.get("price")
                or coin_data.get("priceUsd")
            )
            supply = self._safe_float(
                coin_data.get("supply")
                or coin_data.get("total_supply")
                or coin_data.get("totalSupply")
            )
            if price == 0 and market_cap and supply:
                price = market_cap / supply if supply else 0.0
            if price == 0:
                price = self._safe_float(
                    (coin_data.get("bonding_curve") or {}).get("current_price_usd")
                )
            volume_24h = self._safe_float(
                coin_data.get("volume_24h")
                or coin_data.get("usd_volume_24h")
                or coin_data.get("volume24h")
                or coin_data.get("volume")
            )
            created_timestamp = self._parse_timestamp(
                coin_data.get("created_timestamp")
                or coin_data.get("createdAt")
                or coin_data.get("created_at")
                or coin_data.get("createdTime")
            )
            mint_address = (
                coin_data.get("mint")
                or coin_data.get("mint_address")
                or coin_data.get("address")
                or coin_data.get("public_key")
                or ""
            ).strip()
            description = (
                coin_data.get("description")
                or coin_data.get("about")
                or ""
            )
            image_uri = (
                coin_data.get("image_uri")
                or coin_data.get("imageUrl")
                or coin_data.get("image_url")
                or ""
            )
            twitter = (
                coin_data.get("twitter")
                or coin_data.get("twitter_url")
                or coin_data.get("twitter_handle")
                or ""
            )
            telegram = (
                coin_data.get("telegram")
                or coin_data.get("telegram_url")
                or ""
            )
            website = (
                coin_data.get("website")
                or coin_data.get("website_url")
                or coin_data.get("site")
                or ""
            )
            
            if not name and symbol:
                name = symbol
            if not name:
                return None
            if not symbol:
                symbol = name[:5].upper()
            
            return TokenInfo(
                name=name,
                symbol=symbol,
                price=price,
                market_cap=market_cap,
                volume_24h=volume_24h,
                created_timestamp=created_timestamp,
                mint_address=mint_address,
                description=description,
                image_uri=image_uri,
                twitter=twitter,
                telegram=telegram,
                website=website,
            )
        except Exception as e:
            self.logger.error(f"Error parsing token data: {e}")
            return None
    
    def _parse_transaction_data(self, trade_data: Dict[str, Any], mint_address: str) -> Optional[TransactionData]:
        """Parse raw transaction data into TransactionData model"""
        if not isinstance(trade_data, dict):
            return None
        
        try:
            signature = (
                trade_data.get("signature")
                or trade_data.get("txSignature")
                or trade_data.get("tx_signature")
                or trade_data.get("transaction_hash")
                or ""
            )
            action_value = (
                trade_data.get("action")
                or trade_data.get("side")
                or trade_data.get("type")
            )
            is_buy_value = trade_data.get("is_buy")
            if isinstance(action_value, str):
                action = "buy" if action_value.lower() in {"buy", "purchase", "swap:buy"} else "sell"
            elif isinstance(is_buy_value, str):
                action = "buy" if is_buy_value.lower() in {"true", "1", "buy"} else "sell"
            else:
                action = "buy" if bool(is_buy_value) else "sell"
            amount = self._safe_float(
                trade_data.get("token_amount")
                or trade_data.get("amount")
                or trade_data.get("tokenAmount")
            )
            price = self._safe_float(
                trade_data.get("usd_price")
                or trade_data.get("price_usd")
                or trade_data.get("price")
            )
            if price == 0:
                sol_amount = self._safe_float(
                    trade_data.get("sol_amount") or trade_data.get("solAmount")
                )
                if amount:
                    price = sol_amount / amount if amount else sol_amount
                else:
                    price = sol_amount
            user = (
                trade_data.get("user")
                or trade_data.get("wallet")
                or trade_data.get("user_address")
                or trade_data.get("wallet_address")
                or ""
            )
            timestamp = self._parse_timestamp(
                trade_data.get("timestamp")
                or trade_data.get("created_at")
                or trade_data.get("createdAt")
            )
            if not signature:
                fallback_ts = timestamp.timestamp() if timestamp else datetime.now().timestamp()
                signature = f"{mint_address}:{fallback_ts}:{amount}"
            
            return TransactionData(
                signature=signature,
                token_mint=mint_address,
                action=action,
                amount=amount,
                price=price,
                user=user,
                timestamp=timestamp or datetime.now(),
            )
        except Exception as e:
            self.logger.error(f"Error parsing transaction data: {e}")
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
                    if self.config.request_delay > 0:
                        await asyncio.sleep(self.config.request_delay)
            
            results["transactions"] = all_transactions
            
            # 3. Get new launches
            new_launches = await self.get_new_launches(self.config.new_launches_hours)
            results["new_launches"] = new_launches
            
            # 4. Save all data
            await self.data_storage.save_tokens(tokens, self.config.output_format)
            await self.data_storage.save_transactions(all_transactions, self.config.output_format)
            await self.data_storage.save_new_launches(new_launches, self.config.output_format)
            
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
            await scraper.data_storage.save_tokens(tokens, config.output_format)
            print(f"Scraped {len(tokens)} tokens")
        
        elif args.transactions_only:
            # This would need token addresses as input
            print("Transaction-only mode requires specific token addresses")
        
        elif args.new_launches:
            new_launches = await scraper.get_new_launches(config.new_launches_hours)
            await scraper.data_storage.save_new_launches(new_launches, config.output_format)
            print(f"Found {len(new_launches)} new launches")
        
        else:
            results = await scraper.run_full_scrape()
            print(f"Full scrape completed:")
            print(f"  Tokens: {len(results['tokens'])}")
            print(f"  Transactions: {len(results['transactions'])}")
            print(f"  New Launches: {len(results['new_launches'])}")


if __name__ == "__main__":
    asyncio.run(main())