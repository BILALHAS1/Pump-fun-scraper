"""
Configuration management for pump.fun scraper
"""

from pathlib import Path
from typing import Dict, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field


class ScraperConfig(BaseModel):
    """Configuration model for the pump.fun scraper."""

    model_config = ConfigDict(extra="ignore")

    # API Configuration
    base_url: str = "https://pump.fun"
    
    # Moralis API Configuration (Primary)
    moralis_api_key: Optional[str] = Field(default=None, description="Moralis API key (required)")
    moralis_base_url: str = "https://solana-gateway.moralis.io"
    use_moralis: bool = Field(default=True, description="Use Moralis API (recommended)")
    
    # Legacy PumpPortal API Configuration (Deprecated)
    api_base_url: str = "https://pumpportal.fun"  # Official PumpPortal API
    websocket_url: str = "wss://pumpportal.fun/api/data"  # Official WebSocket API
    api_key: Optional[str] = Field(default=None, description="Optional PumpPortal API key (deprecated)")
    
    # General API Settings
    timeout_seconds: float = Field(default=30.0, description="HTTP request timeout in seconds")
    api_page_size: int = Field(default=100, description="Number of tokens to request per API page")
    api_extra_headers: Dict[str, str] = Field(default_factory=dict, description="Additional headers for API calls")

    # Rate Limiting
    rate_limit_rpm: int = Field(default=30, description="Requests per minute")
    rate_limit_rph: int = Field(default=1000, description="Requests per hour")
    request_delay: float = Field(default=2.0, description="Delay between requests in seconds")

    # Proxy Configuration
    proxy_url: Optional[str] = Field(default=None, description="Optional proxy URL for API requests")
    playwright_proxy: Optional[str] = Field(default=None, description="Optional proxy URL for Playwright browser context")

    # Scraping Limits
    max_tokens: int = Field(default=500, description="Maximum tokens to scrape")
    max_tokens_for_transactions: int = Field(default=50, description="Max tokens to get transactions for")
    transactions_per_token: int = Field(default=100, description="Transactions per token")
    new_launches_hours: int = Field(default=24, description="Hours to look back for new launches")

    # Moralis Polling Configuration
    moralis_poll_interval: int = Field(default=20, description="Polling interval for Moralis API in seconds")
    
    # WebSocket Configuration (Legacy PumpPortal)
    websocket_reconnect_attempts: int = Field(default=5, description="Max WebSocket reconnection attempts")
    websocket_reconnect_delay: float = Field(default=5.0, description="Delay between WebSocket reconnection attempts")
    websocket_ping_interval: float = Field(default=30.0, description="WebSocket ping interval in seconds")
    websocket_timeout: float = Field(default=60.0, description="WebSocket connection timeout in seconds")
    data_collection_duration: int = Field(default=300, description="Duration to collect real-time data in seconds")
    
    # Browser Configuration (legacy fallback - deprecated)
    use_browser_fallback: bool = Field(default=False, description="Use browser scraping if API fails (deprecated)")
    headless_browser: bool = Field(default=True, description="Run browser in headless mode")
    user_agent: str = Field(
        default="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        description="User agent string",
    )
    preload_browser_cookies: bool = Field(
        default=False,
        description="Warm up browser session and sync cookies before API calls (deprecated)",
    )
    browser_page_settle_delay: float = Field(
        default=1.5,
        description="Seconds to wait after loading pump.fun in browser before syncing cookies",
    )
    browser_request_timeout_ms: int = Field(
        default=30000,
        description="Timeout for browser-based fetch requests in milliseconds",
    )
    cookie_sync_interval: int = Field(
        default=300,
        description="Seconds before refreshing cookies from the browser",
    )

    # Output Configuration
    output_directory: str = Field(default="data", description="Directory to save scraped data")
    output_format: str = Field(default="json", description="Output format: json, csv, or both")
    include_timestamps: bool = Field(default=True, description="Include timestamps in output")

    # Logging Configuration
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: Optional[str] = Field(default="scraper.log", description="Log file path")

    # Retry Configuration
    max_retries: int = Field(default=5, description="Maximum retries for failed requests")
    retry_delay: float = Field(default=5.0, description="Delay between retries in seconds")
    max_retry_backoff: float = Field(default=45.0, description="Maximum delay between retry attempts in seconds")

    # Data Filtering
    min_market_cap: float = Field(default=0.0, description="Minimum market cap to include")
    min_volume: float = Field(default=0.0, description="Minimum volume to include")
    exclude_rugged: bool = Field(default=True, description="Exclude rugged/scam tokens")

    @classmethod
    def load(cls, config_path: str = "config.yaml") -> "ScraperConfig":
        """Load configuration from YAML file or create default."""
        config_file = Path(config_path)

        if config_file.exists():
            with open(config_file, "r", encoding="utf-8") as file:
                config_data = yaml.safe_load(file) or {}
                return cls(**config_data)

        default_config = cls()
        default_config.save(config_path)
        return default_config

    def save(self, config_path: str = "config.yaml") -> None:
        """Save configuration to YAML file."""
        config_dict = self.model_dump()

        with open(config_path, "w", encoding="utf-8") as file:
            yaml.dump(config_dict, file, default_flow_style=False, indent=2)

    def validate_config(self) -> bool:
        """Validate configuration settings."""
        if self.rate_limit_rpm <= 0 or self.rate_limit_rph <= 0:
            raise ValueError("Rate limits must be positive")

        if self.max_tokens <= 0:
            raise ValueError("Max tokens must be positive")

        if self.timeout_seconds <= 0:
            raise ValueError("Timeout seconds must be positive")

        if self.api_page_size <= 0:
            raise ValueError("API page size must be positive")

        if self.request_delay < 0:
            raise ValueError("Request delay cannot be negative")

        if self.retry_delay <= 0:
            raise ValueError("Retry delay must be positive")

        if self.max_retry_backoff < self.retry_delay:
            raise ValueError("Max retry backoff must be greater than or equal to retry delay")

        if self.browser_request_timeout_ms <= 0:
            raise ValueError("Browser request timeout must be positive")

        if self.browser_page_settle_delay < 0:
            raise ValueError("Browser page settle delay cannot be negative")

        if self.cookie_sync_interval <= 0:
            raise ValueError("Cookie sync interval must be positive")

        if self.output_format not in {"json", "csv", "both"}:
            raise ValueError("Output format must be 'json', 'csv', or 'both'")

        if self.log_level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("Invalid log level")

        return True
