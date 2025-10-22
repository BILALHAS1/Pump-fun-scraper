"""
Configuration management for pump.fun scraper
"""

import yaml
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field


class ScraperConfig(BaseModel):
    """Configuration model for the pump.fun scraper"""
    
    # API Configuration
    base_url: str = "https://pump.fun"
    api_base_url: str = "https://frontend-api.pump.fun"
    
    # Rate Limiting
    rate_limit_rpm: int = Field(default=30, description="Requests per minute")
    rate_limit_rph: int = Field(default=1000, description="Requests per hour")
    request_delay: float = Field(default=2.0, description="Delay between requests in seconds")
    
    # Scraping Limits
    max_tokens: int = Field(default=500, description="Maximum tokens to scrape")
    max_tokens_for_transactions: int = Field(default=50, description="Max tokens to get transactions for")
    transactions_per_token: int = Field(default=100, description="Transactions per token")
    new_launches_hours: int = Field(default=24, description="Hours to look back for new launches")
    
    # Browser Configuration (for web scraping fallback)
    use_browser_fallback: bool = Field(default=True, description="Use browser scraping if API fails")
    headless_browser: bool = Field(default=True, description="Run browser in headless mode")
    user_agent: str = Field(
        default="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        description="User agent string"
    )
    
    # Output Configuration
    output_directory: str = Field(default="data", description="Directory to save scraped data")
    output_format: str = Field(default="json", description="Output format: json, csv, or both")
    include_timestamps: bool = Field(default=True, description="Include timestamps in output")
    
    # Logging Configuration
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: Optional[str] = Field(default="scraper.log", description="Log file path")
    
    # Retry Configuration
    max_retries: int = Field(default=3, description="Maximum retries for failed requests")
    retry_delay: float = Field(default=5.0, description="Delay between retries in seconds")
    
    # Data Filtering
    min_market_cap: float = Field(default=0.0, description="Minimum market cap to include")
    min_volume: float = Field(default=0.0, description="Minimum volume to include")
    exclude_rugged: bool = Field(default=True, description="Exclude rugged/scam tokens")
    
    @classmethod
    def load(cls, config_path: str = "config.yaml") -> "ScraperConfig":
        """Load configuration from YAML file or create default"""
        config_file = Path(config_path)
        
        if config_file.exists():
            with open(config_file, "r") as f:
                config_data = yaml.safe_load(f)
                return cls(**config_data)
        else:
            # Create default config file
            default_config = cls()
            default_config.save(config_path)
            return default_config
    
    def save(self, config_path: str = "config.yaml"):
        """Save configuration to YAML file"""
        config_dict = self.model_dump()
        
        with open(config_path, "w") as f:
            yaml.dump(config_dict, f, default_flow_style=False, indent=2)
    
    def validate_config(self) -> bool:
        """Validate configuration settings"""
        if self.rate_limit_rpm <= 0 or self.rate_limit_rph <= 0:
            raise ValueError("Rate limits must be positive")
        
        if self.max_tokens <= 0:
            raise ValueError("Max tokens must be positive")
        
        if self.output_format not in ["json", "csv", "both"]:
            raise ValueError("Output format must be 'json', 'csv', or 'both'")
        
        if self.log_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            raise ValueError("Invalid log level")
        
        return True