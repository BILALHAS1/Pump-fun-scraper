#!/usr/bin/env python3
"""
Moralis Web3 Data API Client for Solana/Pump.fun
https://docs.moralis.com/web3-data-api/solana/pump-fun-tutorials
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx
from httpx import AsyncClient, HTTPStatusError, RequestError

from models import TokenInfo, TransactionData


class MoralisClient:
    """Client for Moralis Solana/Pump.fun API"""
    
    BASE_URL = "https://solana-gateway.moralis.io"
    
    def __init__(self, api_key: str, timeout: float = 30.0, logger: Optional[logging.Logger] = None):
        """
        Initialize Moralis API client
        
        Args:
            api_key: Moralis API key
            timeout: Request timeout in seconds
            logger: Optional logger instance
        """
        if not api_key:
            raise ValueError("Moralis API key is required")
        
        self.api_key = api_key
        self.timeout = timeout
        self.logger = logger or logging.getLogger(__name__)
        
        self.headers = {
            "X-API-Key": api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        
        self.client: Optional[AsyncClient] = None
        self._rate_limit_remaining = None
        self._rate_limit_reset = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.client = AsyncClient(
            base_url=self.BASE_URL,
            headers=self.headers,
            timeout=self.timeout,
            follow_redirects=True,
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.client:
            await self.client.aclose()
    
    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make HTTP request to Moralis API with error handling
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            **kwargs: Additional request parameters
            
        Returns:
            JSON response data
            
        Raises:
            HTTPStatusError: On HTTP error responses
            RequestError: On network/request errors
        """
        if not self.client:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")
        
        try:
            response = await self.client.request(method, endpoint, **kwargs)
            
            # Update rate limit info from headers
            self._rate_limit_remaining = response.headers.get("x-rate-limit-remaining")
            self._rate_limit_reset = response.headers.get("x-rate-limit-reset")
            
            # Log rate limit info
            if self._rate_limit_remaining:
                self.logger.debug(f"Rate limit remaining: {self._rate_limit_remaining}")
            
            response.raise_for_status()
            return response.json()
            
        except HTTPStatusError as e:
            self.logger.error(f"HTTP error {e.response.status_code} for {endpoint}: {e.response.text}")
            raise
        except RequestError as e:
            self.logger.error(f"Request error for {endpoint}: {str(e)}")
            raise
    
    async def get_pump_fun_tokens(
        self,
        limit: int = 100,
        offset: int = 0,
        sort_by: str = "created_at",
        order: str = "desc",
    ) -> List[Dict[str, Any]]:
        """
        Get pump.fun tokens from Moralis API
        
        Args:
            limit: Number of tokens to retrieve (max 100)
            offset: Pagination offset
            sort_by: Sort field (created_at, market_cap, volume)
            order: Sort order (asc, desc)
            
        Returns:
            List of token data dictionaries
        """
        params = {
            "limit": min(limit, 100),
            "offset": offset,
            "sort_by": sort_by,
            "order": order,
        }
        
        try:
            # Moralis API endpoint for pump.fun tokens
            # Note: This endpoint structure is based on typical Moralis patterns
            # and may need adjustment based on actual API documentation
            data = await self._request("GET", "/pumpfun/tokens", params=params)
            
            # Handle both list response and paginated response formats
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and "result" in data:
                return data.get("result", [])
            elif isinstance(data, dict) and "data" in data:
                return data.get("data", [])
            else:
                return []
                
        except Exception as e:
            self.logger.error(f"Error fetching pump.fun tokens: {e}")
            return []
    
    async def get_token_details(self, mint_address: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information for a specific token
        
        Args:
            mint_address: Token mint address
            
        Returns:
            Token details dictionary or None
        """
        try:
            data = await self._request("GET", f"/pumpfun/token/{mint_address}")
            return data
        except Exception as e:
            self.logger.error(f"Error fetching token details for {mint_address}: {e}")
            return None
    
    async def get_token_trades(
        self,
        mint_address: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get trades/transactions for pump.fun tokens
        
        Args:
            mint_address: Optional token mint address to filter by
            limit: Number of trades to retrieve
            offset: Pagination offset
            from_date: Start date for trades
            to_date: End date for trades
            
        Returns:
            List of trade data dictionaries
        """
        params = {
            "limit": min(limit, 100),
            "offset": offset,
        }
        
        if mint_address:
            params["token"] = mint_address
        
        if from_date:
            params["from_date"] = int(from_date.timestamp())
        
        if to_date:
            params["to_date"] = int(to_date.timestamp())
        
        try:
            data = await self._request("GET", "/pumpfun/trades", params=params)
            
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and "result" in data:
                return data.get("result", [])
            elif isinstance(data, dict) and "data" in data:
                return data.get("data", [])
            else:
                return []
                
        except Exception as e:
            self.logger.error(f"Error fetching trades: {e}")
            return []
    
    async def get_new_tokens(
        self,
        hours_back: int = 24,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get newly created tokens within specified timeframe
        
        Args:
            hours_back: How many hours back to look for new tokens
            limit: Maximum number of tokens to retrieve
            
        Returns:
            List of new token data dictionaries
        """
        from_date = datetime.now() - timedelta(hours=hours_back)
        
        params = {
            "limit": min(limit, 100),
            "from_date": int(from_date.timestamp()),
            "sort_by": "created_at",
            "order": "desc",
        }
        
        try:
            data = await self._request("GET", "/pumpfun/tokens/new", params=params)
            
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and "result" in data:
                return data.get("result", [])
            elif isinstance(data, dict) and "data" in data:
                return data.get("data", [])
            else:
                return []
                
        except Exception as e:
            self.logger.error(f"Error fetching new tokens: {e}")
            return []
    
    def parse_token(self, data: Dict[str, Any]) -> Optional[TokenInfo]:
        """
        Parse Moralis API response data into TokenInfo model
        
        Args:
            data: Raw token data from Moralis API
            
        Returns:
            TokenInfo instance or None if parsing fails
        """
        try:
            # Extract mint address (required field)
            mint_address = (
                data.get("mint") or
                data.get("address") or
                data.get("mint_address") or
                data.get("token_address")
            )
            
            if not mint_address:
                self.logger.debug("Skipping token without mint address")
                return None
            
            # Parse timestamp
            created_timestamp = None
            timestamp_value = (
                data.get("created_at") or
                data.get("created_timestamp") or
                data.get("creation_time") or
                data.get("launch_time")
            )
            
            if timestamp_value:
                if isinstance(timestamp_value, (int, float)):
                    created_timestamp = datetime.fromtimestamp(timestamp_value)
                elif isinstance(timestamp_value, str):
                    try:
                        created_timestamp = datetime.fromisoformat(timestamp_value.replace("Z", "+00:00"))
                    except (ValueError, AttributeError):
                        pass
            
            # Get metadata if nested
            metadata = data.get("metadata") or data.get("token_metadata") or {}
            
            # Extract token information
            token = TokenInfo(
                name=data.get("name") or metadata.get("name") or "",
                symbol=data.get("symbol") or metadata.get("symbol") or "",
                price=float(data.get("price_usd") or data.get("price") or 0),
                market_cap=float(data.get("market_cap") or data.get("market_cap_usd") or 0),
                volume_24h=float(data.get("volume_24h") or data.get("volume_24h_usd") or 0),
                created_timestamp=created_timestamp,
                mint_address=mint_address,
                description=data.get("description") or metadata.get("description") or "",
                image_uri=data.get("image") or data.get("image_uri") or metadata.get("image") or "",
                twitter=data.get("twitter") or data.get("twitter_url") or "",
                telegram=data.get("telegram") or data.get("telegram_url") or "",
                website=data.get("website") or data.get("website_url") or "",
            )
            
            return token
            
        except Exception as e:
            self.logger.error(f"Error parsing token data: {e}")
            return None
    
    def parse_transaction(self, data: Dict[str, Any]) -> Optional[TransactionData]:
        """
        Parse Moralis API response data into TransactionData model
        
        Args:
            data: Raw transaction/trade data from Moralis API
            
        Returns:
            TransactionData instance or None if parsing fails
        """
        try:
            # Extract signature (required field)
            signature = (
                data.get("signature") or
                data.get("transaction_hash") or
                data.get("tx_hash") or
                data.get("id")
            )
            
            token_mint = (
                data.get("token") or
                data.get("token_address") or
                data.get("mint") or
                data.get("mint_address")
            )
            
            if not signature or not token_mint:
                self.logger.debug("Skipping transaction without signature or token")
                return None
            
            # Parse timestamp
            timestamp = datetime.now()
            timestamp_value = (
                data.get("timestamp") or
                data.get("block_time") or
                data.get("time") or
                data.get("created_at")
            )
            
            if timestamp_value:
                if isinstance(timestamp_value, (int, float)):
                    timestamp = datetime.fromtimestamp(timestamp_value)
                elif isinstance(timestamp_value, str):
                    try:
                        timestamp = datetime.fromisoformat(timestamp_value.replace("Z", "+00:00"))
                    except (ValueError, AttributeError):
                        pass
            
            # Determine action
            action = (data.get("type") or data.get("side") or data.get("action") or "").lower()
            if not action or action not in {"buy", "sell", "create"}:
                if "buy" in str(action):
                    action = "buy"
                elif "sell" in str(action):
                    action = "sell"
                else:
                    action = "trade"
            
            transaction = TransactionData(
                signature=signature,
                token_mint=token_mint,
                action=action,
                amount=float(data.get("amount") or data.get("token_amount") or 0),
                price=float(data.get("price") or data.get("price_usd") or 0),
                user=data.get("user") or data.get("trader") or data.get("wallet") or "",
                timestamp=timestamp,
            )
            
            return transaction
            
        except Exception as e:
            self.logger.error(f"Error parsing transaction data: {e}")
            return None
