#!/usr/bin/env python3
"""
Pump.fun Data Scraper

This script collects token information, transaction data, and trading activity
from pump.fun using either:
- Moralis Web3 Data API (recommended, default)
- PumpPortal.fun WebSocket API (legacy)
"""

import asyncio
import json
import logging
import signal
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse, parse_qs

import websockets
from websockets.client import WebSocketClientProtocol
from websockets.exceptions import ConnectionClosed, WebSocketException

from config import ScraperConfig
from models import TokenInfo, TransactionData
from utils.data_storage import DataStorage
from utils.logger import setup_logger
from utils.rate_limiter import AdaptiveRateLimiter

# Import Moralis scraper (used when use_moralis=True)
try:
    from moralis_scraper import MoralisScraper
except ImportError:
    MoralisScraper = None


class PumpPortalScraper:
    """Official PumpPortal.fun API scraper using WebSocket connections"""
    
    NEW_TOKEN_MESSAGE_TYPES = {
        "newtoken",
        "tokencreated",
        "new_token",
        "subscribenewtoken",
    }
    TRADE_MESSAGE_TYPES = {
        "tokentrade",
        "accounttrade",
        "wallettrade",
        "tradetoken",
        "tradestream",
        "subscribetokentrade",
        "subscribeaccounttrade",
        "trade",
    }
    MIGRATION_MESSAGE_TYPES = {
        "migration",
        "tokenmigration",
        "subscribemigration",
    }
    
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
        self._seen_transaction_signatures: Set[str] = set()
        self._seen_launch_mints: Set[str] = set()
        self._seen_migration_events: Set[str] = set()
        
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
            if self.logger.isEnabledFor(logging.DEBUG):
                truncated = message if len(message) <= 2000 else f"{message[:2000]}... (truncated)"
                self.logger.debug(f"Raw message received: {truncated}")
            
            data = json.loads(message)
            self.messages_received += 1
            
            message_type, payload = self._normalize_message(data)
            normalized_type = (message_type or "unknown").lower()
            
            if self.logger.isEnabledFor(logging.DEBUG):
                if isinstance(payload, dict):
                    self.logger.debug(
                        f"Normalized message type '{normalized_type}' with payload keys: {list(payload.keys())}"
                    )
                else:
                    self.logger.debug(
                        f"Normalized message type '{normalized_type}' with payload: {type(payload).__name__}"
                    )
            
            if normalized_type in self.NEW_TOKEN_MESSAGE_TYPES or (
                isinstance(payload, dict) and self._looks_like_new_token(payload)
            ):
                await self._process_new_token(payload)
            elif normalized_type in self.TRADE_MESSAGE_TYPES or (
                isinstance(payload, dict) and self._looks_like_trade(payload)
            ):
                await self._process_token_trade(payload)
            elif normalized_type in self.MIGRATION_MESSAGE_TYPES or (
                isinstance(payload, dict) and self._looks_like_migration(payload)
            ):
                await self._process_migration(payload)
            else:
                if self.logger.isEnabledFor(logging.DEBUG):
                    payload_preview = json.dumps(data, default=str)
                    if len(payload_preview) > 2000:
                        payload_preview = f"{payload_preview[:2000]}... (truncated)"
                    self.logger.debug(f"Unhandled message '{normalized_type}': {payload_preview}")
        
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to decode message as JSON: {e}")
        except Exception:
            self.logger.exception("Error processing message")
    
    async def _process_new_token(self, payload: Dict[str, Any]):
        """Process new token creation event"""
        try:
            if not isinstance(payload, dict):
                self.logger.debug("New token payload is not a dict; skipping")
                return
            
            metadata = payload.get("metadata") or payload.get("tokenMetadata") or {}
            if not isinstance(metadata, dict):
                metadata = {}
            
            segments: List[Dict[str, Any]] = [payload]
            for key in ("tokenInfo", "token", "tokenData", "info", "data"):
                segment = payload.get(key)
                if isinstance(segment, dict):
                    segments.append(segment)
            segments.append(metadata)
            
            token_data: Dict[str, Any] = {}
            for segment in segments:
                token_data.update(segment)
            
            mint_address = self._first_non_empty_str(
                token_data.get("mint"),
                token_data.get("mintAddress"),
                token_data.get("tokenMint"),
                token_data.get("mint_address"),
                token_data.get("address"),
                metadata.get("mint"),
            )
            if not mint_address:
                self.logger.debug("Skipping new token payload without mint address")
                return
            
            name = self._first_non_empty_str(
                token_data.get("name"),
                token_data.get("tokenName"),
                metadata.get("name"),
            )
            symbol = self._first_non_empty_str(
                token_data.get("symbol"),
                token_data.get("tokenSymbol"),
                token_data.get("ticker"),
                metadata.get("symbol"),
            )
            
            price = self._extract_float(
                token_data.get("priceUsd"),
                token_data.get("usdPrice"),
                token_data.get("price_usd"),
                token_data.get("priceUSD"),
                token_data.get("price"),
                metadata.get("priceUsd"),
            )
            market_cap = self._extract_float(
                token_data.get("marketCapUsd"),
                token_data.get("marketCap"),
                token_data.get("usdMarketCap"),
                token_data.get("fullyDilutedMarketCapUsd"),
                token_data.get("fdvUsd"),
                token_data.get("market_cap"),
            )
            volume_24h = self._extract_float(
                token_data.get("volume24h"),
                token_data.get("volumeUsd24h"),
                token_data.get("usdVolume24h"),
                token_data.get("volume24HUsd"),
                token_data.get("volume24hUsd"),
                token_data.get("volume"),
            )
            
            timestamp_value = (
                token_data.get("timestamp")
                or token_data.get("createdTimestamp")
                or token_data.get("createdAt")
                or token_data.get("launchTime")
                or token_data.get("launchTimestamp")
                or payload.get("timestamp")
            )
            created_timestamp = self._parse_timestamp(timestamp_value)
            
            description = self._first_non_empty_str(
                token_data.get("description"),
                token_data.get("bio"),
                metadata.get("description"),
            )
            image_uri = self._first_non_empty_str(
                token_data.get("imageUrl"),
                token_data.get("image"),
                token_data.get("image_uri"),
                metadata.get("imageUrl"),
                metadata.get("image"),
            )
            
            social_sources = [
                token_data,
                payload.get("socials"),
                payload.get("links"),
                payload.get("community"),
                metadata,
            ]
            
            twitter = self._first_non_empty_str(
                *[
                    source.get(key)
                    for source in social_sources
                    if isinstance(source, dict)
                    for key in ("twitter", "twitterUrl", "twitter_handle", "twitterHandle", "x")
                ]
            )
            telegram = self._first_non_empty_str(
                *[
                    source.get(key)
                    for source in social_sources
                    if isinstance(source, dict)
                    for key in ("telegram", "telegramUrl", "telegram_handle", "tg")
                ]
            )
            website = self._first_non_empty_str(
                *[
                    source.get(key)
                    for source in social_sources
                    if isinstance(source, dict)
                    for key in ("website", "websiteUrl", "site", "url", "link")
                ]
            )
            
            existing_token = self.collected_tokens.get(mint_address)
            token: TokenInfo
            if existing_token:
                token = existing_token.model_copy(
                    update={
                        "name": name or existing_token.name,
                        "symbol": symbol or existing_token.symbol,
                        "price": price if price > 0 else existing_token.price,
                        "market_cap": market_cap if market_cap > 0 else existing_token.market_cap,
                        "volume_24h": volume_24h if volume_24h > 0 else existing_token.volume_24h,
                        "created_timestamp": created_timestamp or existing_token.created_timestamp,
                        "description": description or existing_token.description,
                        "image_uri": image_uri or existing_token.image_uri,
                        "twitter": twitter or existing_token.twitter,
                        "telegram": telegram or existing_token.telegram,
                        "website": website or existing_token.website,
                    }
                )
                self.logger.debug(f"Updated token details for {token.name or mint_address[:8]}")
            else:
                token = TokenInfo(
                    name=name or "",
                    symbol=symbol or "",
                    price=price,
                    market_cap=market_cap,
                    volume_24h=volume_24h,
                    created_timestamp=created_timestamp,
                    mint_address=mint_address,
                    description=description or "",
                    image_uri=image_uri or "",
                    twitter=twitter or "",
                    telegram=telegram or "",
                    website=website or "",
                )
            
            self.collected_tokens[mint_address] = token
            
            for idx, launch in enumerate(self.new_launches):
                if launch.mint_address == mint_address:
                    self.new_launches[idx] = token
                    break
            
            if mint_address not in self._seen_launch_mints:
                self.new_launches.append(token)
                self._seen_launch_mints.add(mint_address)
                self.logger.info(
                    f"New token: {token.name or 'Unknown'} ({token.symbol}) - "
                    f"${token.price:.6f} | MC: ${token.market_cap:,.0f}"
                )
        
        except Exception:
            self.logger.exception("Error processing new token")
    
    async def _process_token_trade(self, payload: Dict[str, Any]):
        """Process token trade event"""
        try:
            if not isinstance(payload, dict):
                self.logger.debug("Trade payload is not a dict; skipping")
                return
            
            segments: List[Dict[str, Any]] = [payload]
            for key in ("trade", "data", "details", "info"):
                segment = payload.get(key)
                if isinstance(segment, dict):
                    segments.append(segment)
            
            trade_data: Dict[str, Any] = {}
            for segment in segments:
                trade_data.update(segment)
            
            signature = self._first_non_empty_str(
                trade_data.get("signature"),
                trade_data.get("txSignature"),
                trade_data.get("transactionSignature"),
                trade_data.get("transactionHash"),
                trade_data.get("id"),
                payload.get("signature"),
            )
            token_mint = self._first_non_empty_str(
                trade_data.get("mint"),
                trade_data.get("tokenMint"),
                trade_data.get("mintAddress"),
                trade_data.get("tokenAddress"),
            )
            
            if not signature or not token_mint:
                self.logger.debug("Skipping trade without signature or token mint")
                return
            
            action = self._first_non_empty_str(
                trade_data.get("tradeType"),
                trade_data.get("side"),
                trade_data.get("action"),
                trade_data.get("type"),
            ).lower()
            if action not in {"buy", "sell", "create"}:
                if "buy" in action:
                    action = "buy"
                elif "sell" in action:
                    action = "sell"
                elif not action:
                    action = "trade"
            
            amount = self._extract_float(
                trade_data.get("tokenAmount"),
                trade_data.get("token_amount"),
                trade_data.get("amount"),
                trade_data.get("quantity"),
                trade_data.get("size"),
            )
            price = self._extract_float(
                trade_data.get("priceUsd"),
                trade_data.get("usdPrice"),
                trade_data.get("price_usd"),
                trade_data.get("price"),
                trade_data.get("valueUsd"),
                trade_data.get("usdValue"),
            )
            user = self._first_non_empty_str(
                trade_data.get("trader"),
                trade_data.get("wallet"),
                trade_data.get("user"),
                trade_data.get("owner"),
                trade_data.get("buyer"),
                trade_data.get("seller"),
            )
            timestamp_value = (
                trade_data.get("timestamp")
                or trade_data.get("blockTime")
                or trade_data.get("time")
                or trade_data.get("createdAt")
                or trade_data.get("slotTime")
            )
            timestamp = self._parse_timestamp(timestamp_value) or datetime.now()
            
            transaction = TransactionData(
                signature=signature,
                token_mint=token_mint,
                action=action or "trade",
                amount=amount,
                price=price,
                user=user,
                timestamp=timestamp,
            )
            
            if signature in self._seen_transaction_signatures:
                return
            
            self._seen_transaction_signatures.add(signature)
            self.collected_transactions.append(transaction)
            
            market_cap_update = self._extract_float(
                trade_data.get("marketCapUsd"),
                trade_data.get("marketCap"),
                trade_data.get("usdMarketCap"),
            )
            volume_increment = amount * price if amount and price else 0.0
            
            existing_token = self.collected_tokens.get(token_mint)
            if existing_token:
                updated_token = existing_token.model_copy(
                    update={
                        "price": price if price > 0 else existing_token.price,
                        "market_cap": market_cap_update if market_cap_update > 0 else existing_token.market_cap,
                        "volume_24h": existing_token.volume_24h + volume_increment,
                        "created_timestamp": existing_token.created_timestamp or timestamp,
                    }
                )
                self.collected_tokens[token_mint] = updated_token
            else:
                token_name = self._first_non_empty_str(
                    trade_data.get("tokenName"),
                    trade_data.get("name"),
                )
                token_symbol = self._first_non_empty_str(
                    trade_data.get("symbol"),
                    trade_data.get("tokenSymbol"),
                    trade_data.get("ticker"),
                )
                placeholder_token = TokenInfo(
                    name=token_name or "",
                    symbol=token_symbol or "",
                    price=price,
                    market_cap=market_cap_update,
                    volume_24h=volume_increment,
                    created_timestamp=self._parse_timestamp(trade_data.get("createdAt")) or timestamp,
                    mint_address=token_mint,
                    description="",
                    image_uri="",
                    twitter="",
                    telegram="",
                    website="",
                )
                self.collected_tokens[token_mint] = placeholder_token
            
            self.logger.debug(
                f"Trade: {transaction.action.upper()} {transaction.amount:,.0f} @ ${transaction.price:.6f} "
                f"({transaction.signature[:8]}...)"
            )
        
        except Exception:
            self.logger.exception("Error processing token trade")
    
    async def _process_account_trade(self, payload: Dict[str, Any]):
        """Process account trade event"""
        await self._process_token_trade(payload)
    
    async def _process_migration(self, payload: Dict[str, Any]):
        """Process token migration event"""
        try:
            if not isinstance(payload, dict):
                self.logger.debug("Migration payload is not a dict; skipping")
                return
            
            migration_data = dict(payload)
            timestamp_value = (
                migration_data.get("timestamp")
                or migration_data.get("time")
                or migration_data.get("blockTime")
            )
            parsed_timestamp = self._parse_timestamp(timestamp_value)
            if parsed_timestamp:
                migration_data["parsed_timestamp"] = parsed_timestamp.isoformat()
            
            mint_address = self._first_non_empty_str(
                migration_data.get("mint"),
                migration_data.get("tokenMint"),
                migration_data.get("oldMint"),
            )
            event_key = self._first_non_empty_str(
                migration_data.get("signature"),
                migration_data.get("txSignature"),
                migration_data.get("transactionHash"),
            ) or f"{mint_address}|{migration_data.get('parsed_timestamp') or timestamp_value or ''}"
            
            if event_key in self._seen_migration_events:
                return
            
            self._seen_migration_events.add(event_key)
            self.migration_events.append(migration_data)
            
            token_name = self._first_non_empty_str(
                migration_data.get("name"),
                migration_data.get("tokenName"),
            ) or "Unknown"
            mint_preview = mint_address[:8] + "..." if mint_address else "unknown"
            self.logger.info(f"Migration event: {token_name} ({mint_preview})")
        
        except Exception:
            self.logger.exception("Error processing migration")
    
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
    
    def _first_non_empty_str(self, *values: Any) -> str:
        """Return the first non-empty string from provided values."""
        for value in values:
            if value is None:
                continue
            if isinstance(value, str):
                candidate = value.strip()
                if candidate:
                    return candidate
            elif isinstance(value, bool):
                continue
            elif isinstance(value, (int, float)):
                candidate = str(value).strip()
                if candidate:
                    return candidate
            elif isinstance(value, (bytes, bytearray)):
                try:
                    candidate = value.decode().strip()
                except Exception:
                    continue
                if candidate:
                    return candidate
        return ""
    
    def _coerce_float(self, value: Any, visited: Optional[Set[int]] = None) -> Optional[float]:
        if visited is None:
            visited = set()
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, bool):
            return float(value)
        if isinstance(value, str):
            cleaned = value.strip().replace(",", "")
            if not cleaned:
                return None
            try:
                return float(cleaned)
            except ValueError:
                return None
        if isinstance(value, dict):
            obj_id = id(value)
            if obj_id in visited:
                return None
            visited.add(obj_id)
            preferred_keys = (
                "usd",
                "usdValue",
                "priceUsd",
                "price_usd",
                "priceUSD",
                "valueUsd",
                "usdPrice",
                "price",
                "marketCapUsd",
                "marketCap",
                "usdMarketCap",
                "volume",
                "amount",
                "tokenAmount",
                "token_amount",
            )
            for key in preferred_keys:
                if key in value:
                    result = self._coerce_float(value.get(key), visited)
                    if result is not None:
                        return result
            for nested_value in value.values():
                result = self._coerce_float(nested_value, visited)
                if result is not None:
                    return result
            return None
        if isinstance(value, (list, tuple, set)):
            for item in value:
                result = self._coerce_float(item, visited)
                if result is not None:
                    return result
            return None
        return None
    
    def _extract_float(self, *values: Any, default: float = 0.0) -> float:
        for value in values:
            result = self._coerce_float(value)
            if result is not None:
                return result
        return default
    
    def _extract_message_type(self, data: Dict[str, Any]) -> Optional[str]:
        if not isinstance(data, dict):
            return None
        for key in ("type", "event", "messageType", "method", "channel", "subscription", "topic"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        for nested_key in ("data", "payload", "message"):
            nested = data.get(nested_key)
            if isinstance(nested, dict):
                nested_type = self._extract_message_type(nested)
                if nested_type:
                    return nested_type
        return None
    
    def _extract_payload(self, data: Dict[str, Any]) -> Any:
        if not isinstance(data, dict):
            return data
        for key in ("data", "payload", "message", "detail", "eventData", "value", "record"):
            candidate = data.get(key)
            if isinstance(candidate, dict):
                return candidate
            if isinstance(candidate, list) and candidate:
                first_item = candidate[0]
                if isinstance(first_item, dict):
                    return first_item
        return data
    
    def _normalize_message(self, data: Dict[str, Any]) -> Tuple[Optional[str], Dict[str, Any]]:
        if not isinstance(data, dict):
            return None, {}
        message_type = self._extract_message_type(data)
        payload = self._extract_payload(data)
        if isinstance(payload, dict):
            return message_type, payload
        return message_type, {}
    
    def _looks_like_new_token(self, payload: Dict[str, Any]) -> bool:
        if not isinstance(payload, dict):
            return False
        mint = self._first_non_empty_str(
            payload.get("mint"),
            payload.get("mintAddress"),
            payload.get("tokenMint"),
            payload.get("mint_address"),
            payload.get("address"),
        )
        if not mint:
            return False
        metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
        name = self._first_non_empty_str(
            payload.get("name"),
            payload.get("tokenName"),
            metadata.get("name"),
        )
        symbol = self._first_non_empty_str(
            payload.get("symbol"),
            payload.get("tokenSymbol"),
            payload.get("ticker"),
            metadata.get("symbol"),
        )
        if name or symbol:
            return True
        float_fields = (
            payload.get("priceUsd"),
            payload.get("marketCapUsd"),
            payload.get("fullyDilutedMarketCapUsd"),
            payload.get("marketCap"),
        )
        return any(self._coerce_float(value) is not None for value in float_fields)
    
    def _looks_like_trade(self, payload: Dict[str, Any]) -> bool:
        if not isinstance(payload, dict):
            return False
        signature = self._first_non_empty_str(
            payload.get("signature"),
            payload.get("txSignature"),
            payload.get("transactionSignature"),
            payload.get("transactionHash"),
            payload.get("id"),
        )
        token_mint = self._first_non_empty_str(
            payload.get("mint"),
            payload.get("tokenMint"),
            payload.get("mintAddress"),
            payload.get("tokenAddress"),
        )
        if signature and token_mint:
            return True
        indicators = {"tradeType", "tokenAmount", "priceUsd", "usdPrice", "side"}
        return bool(token_mint and indicators.intersection(payload.keys()))
    
    def _looks_like_migration(self, payload: Dict[str, Any]) -> bool:
        if not isinstance(payload, dict):
            return False
        payload_type = payload.get("type")
        if isinstance(payload_type, str) and "migration" in payload_type.lower():
            return True
        return any(
            key in payload
            for key in ("newMint", "oldMint", "raydiumPool", "destinationMint", "migrationType")
        )
    
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
                
                # For continuous operation, allow infinite reconnection attempts
                delay = min(
                    self.config.websocket_reconnect_delay * (2 ** min(self.reconnection_attempts - 1, 4)),
                    60.0  # Max 60 seconds delay
                )
                
                self.logger.info(
                    f"Reconnection attempt {self.reconnection_attempts} in {delay:.1f}s"
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
    
    async def collect_data(self, duration_seconds: Optional[int] = None) -> Dict[str, Any]:
        """Collect data for specified duration or continuously if duration is None"""
        if duration_seconds is None:
            self.logger.info("Starting continuous data collection (no time limit)...")
        else:
            self.logger.info(f"Starting data collection for {duration_seconds} seconds...")
        
        # Start connection maintenance
        connection_task = asyncio.create_task(self.maintain_connection())
        
        # Start periodic data saving and stats logging
        save_task = asyncio.create_task(self._periodic_data_save())
        stats_task = asyncio.create_task(self._periodic_stats_logging())
        
        try:
            if duration_seconds is None:
                # Run indefinitely until shutdown signal
                await self._shutdown_event.wait()
            else:
                # Wait for specified duration or shutdown signal
                await asyncio.wait_for(
                    self._shutdown_event.wait(),
                    timeout=duration_seconds
                )
        except asyncio.TimeoutError:
            # Normal completion after timeout
            self.logger.info("Data collection duration completed")
        
        # Stop all background tasks
        self.should_reconnect = False
        for task in [connection_task, save_task, stats_task]:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Final save before returning
        await self._save_current_data()
        
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
    
    async def _periodic_data_save(self):
        """Periodically save data to disk for real-time dashboard updates"""
        save_interval = 20  # Save every 20 seconds for real-time updates
        
        while self.should_reconnect and not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(save_interval)
                if self._shutdown_event.is_set():
                    break
                
                await self._save_current_data()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error during periodic data save: {e}")
    
    async def _save_current_data(self):
        """Save current data to disk using consistent filenames for real-time updates"""
        try:
            # Use consistent filenames so dashboard always reads latest data
            tokens_list = list(self.collected_tokens.values())
            
            if tokens_list:
                await self.data_storage.save_tokens(
                    tokens_list,
                    format_type=self.config.output_format,
                )
                self.logger.debug(f"Saved {len(tokens_list)} tokens to disk")
            
            if self.collected_transactions:
                await self.data_storage.save_transactions(
                    self.collected_transactions,
                    format_type=self.config.output_format,
                )
                self.logger.debug(f"Saved {len(self.collected_transactions)} transactions to disk")
            
            if self.new_launches:
                await self.data_storage.save_new_launches(
                    self.new_launches,
                    format_type=self.config.output_format,
                )
                self.logger.debug(f"Saved {len(self.new_launches)} new launches to disk")
            
        except Exception as e:
            self.logger.error(f"Error saving current data: {e}")
    
    async def _periodic_stats_logging(self):
        """Periodically log statistics to show scraper is active"""
        log_interval = 30  # Log stats every 30 seconds
        
        while self.should_reconnect and not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(log_interval)
                if self._shutdown_event.is_set():
                    break
                
                stats = self._get_session_statistics()
                uptime = timedelta(seconds=int(stats['session_duration']))
                
                self.logger.info(
                    f"🔄 LIVE STATS | Uptime: {uptime} | "
                    f"Tokens: {stats['tokens_collected']} | "
                    f"Transactions: {stats['transactions_collected']} | "
                    f"New Launches: {stats['new_launches']} | "
                    f"Messages: {stats['messages_received']} | "
                    f"Connection: {'✓ Connected' if self.is_connected else '✗ Disconnected'}"
                )
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error during periodic stats logging: {e}")
    
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
    
    async def run_full_scrape(self, duration_seconds: Optional[int] = None) -> Dict[str, Any]:
        """Run complete data collection process
        
        Args:
            duration_seconds: Duration to collect data. If None, runs continuously until stopped.
        """
        try:
            # Collect real-time data (continuously if duration is None)
            results = await self.collect_data(duration_seconds=duration_seconds)
            
            # Data is already being saved periodically during collection
            # Just save final session statistics
            stats_file = f"{self.config.output_directory}/session_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(stats_file, 'w') as f:
                json.dump(results['statistics'], f, indent=2, default=str)
            
            self.logger.info("Scraper stopped. Final statistics saved.")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error during scrape: {e}")
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
    
    parser = argparse.ArgumentParser(description="Pump.fun Data Scraper - Continuous Real-Time Mode")
    parser.add_argument("--config", "-c", default="config.yaml", help="Configuration file")
    parser.add_argument("--duration", "-d", type=int, help="Data collection duration in seconds (default: continuous/infinite)")
    parser.add_argument("--moralis-key", help="Moralis API key")
    parser.add_argument("--api-key", help="PumpPortal API key (legacy)")
    parser.add_argument("--use-pumpportal", action="store_true", help="Use PumpPortal API instead of Moralis")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    # Load configuration
    config = ScraperConfig.load(args.config)
    
    # Apply CLI overrides
    if args.moralis_key:
        config.moralis_api_key = args.moralis_key
        config.use_moralis = True
    if args.api_key:
        config.api_key = args.api_key
    if args.use_pumpportal:
        config.use_moralis = False
    if args.verbose:
        config.log_level = "DEBUG"
    
    # Determine which scraper to use
    use_moralis = config.use_moralis and config.moralis_api_key and MoralisScraper is not None
    
    # Run scraper
    async def main():
        print("=" * 70)
        if use_moralis:
            print("Pump.fun Scraper - Using Moralis Web3 Data API")
        else:
            print("Pump.fun Scraper - Using PumpPortal WebSocket API (Legacy)")
        print("=" * 70)
        if args.duration:
            print(f"Running for {args.duration} seconds...")
        else:
            print("Running continuously until stopped (Ctrl+C to exit)...")
        print("Dashboard will show coins in real-time as they are scraped.")
        print("=" * 70)
        print()
        
        if use_moralis:
            # Use Moralis scraper
            async with MoralisScraper(config) as scraper:
                results = await scraper.collect_data(duration_seconds=args.duration)
                print()
                print("=" * 70)
                print(f"✓ Scraper stopped gracefully")
                print(f"✓ Total collected: {len(results['tokens'])} tokens, {len(results['transactions'])} transactions, {len(results['new_launches'])} new launches")
                print("=" * 70)
        else:
            # Use PumpPortal scraper (legacy)
            if not config.moralis_api_key:
                print("⚠ Warning: Moralis API key not configured. Using legacy PumpPortal API.")
                print("   Get a Moralis API key at https://moralis.io for better reliability.")
                print()
            async with PumpPortalScraper(config) as scraper:
                results = await scraper.run_full_scrape(duration_seconds=args.duration)
                print()
                print("=" * 70)
                print(f"✓ Scraper stopped gracefully")
                print(f"✓ Total collected: {len(results['tokens'])} tokens, {len(results['transactions'])} transactions, {len(results['new_launches'])} new launches")
                print("=" * 70)
    
    asyncio.run(main())