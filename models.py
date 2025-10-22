"""
Data models for the pump.fun scraper
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class TokenInfo(BaseModel):
    """Token information data model"""
    name: str
    symbol: str
    price: float = 0.0
    market_cap: float = 0.0
    volume_24h: float = 0.0
    created_timestamp: Optional[datetime] = None
    mint_address: str = ""
    description: str = ""
    image_uri: str = ""
    twitter: str = ""
    telegram: str = ""
    website: str = ""
    scraped_at: datetime = Field(default_factory=datetime.now)
    
    def __eq__(self, other):
        """Custom equality comparison based on mint_address"""
        if not isinstance(other, TokenInfo):
            return False
        return self.mint_address == other.mint_address
    
    def __hash__(self):
        """Custom hash for deduplication"""
        return hash(self.mint_address)


class TransactionData(BaseModel):
    """Transaction data model"""
    signature: str
    token_mint: str
    action: str  # buy, sell, create
    amount: float
    price: float
    user: str
    timestamp: datetime
    scraped_at: datetime = Field(default_factory=datetime.now)
    
    def __eq__(self, other):
        """Custom equality comparison based on signature"""
        if not isinstance(other, TransactionData):
            return False
        return self.signature == other.signature
    
    def __hash__(self):
        """Custom hash for deduplication"""
        return hash(self.signature)


class ScrapingStats(BaseModel):
    """Statistics for scraping sessions"""
    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    tokens_scraped: int = 0
    transactions_scraped: int = 0
    requests_made: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    errors: list = Field(default_factory=list)
    
    @property
    def duration(self) -> Optional[float]:
        """Calculate session duration in seconds"""
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage"""
        if self.requests_made == 0:
            return 0.0
        return (self.successful_requests / self.requests_made) * 100


class ApiEndpoint(BaseModel):
    """API endpoint configuration"""
    url: str
    method: str = "GET"
    headers: dict = Field(default_factory=dict)
    params: dict = Field(default_factory=dict)
    timeout: int = 30
    retry_count: int = 3


class ScrapingTarget(BaseModel):
    """Scraping target configuration"""
    name: str
    endpoint: ApiEndpoint
    fallback_selector: Optional[str] = None  # CSS selector for web scraping
    rate_limit: int = 30  # requests per minute
    data_type: str = "tokens"  # tokens, transactions, etc.