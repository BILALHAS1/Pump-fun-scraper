"""
Rate limiting utilities for the pump.fun scraper
"""

import asyncio
import time
from collections import deque
from typing import Optional


class RateLimiter:
    """
    Async rate limiter to prevent API abuse and being blocked
    """
    
    def __init__(
        self,
        requests_per_minute: int = 30,
        requests_per_hour: int = 1000,
        burst_limit: Optional[int] = None
    ):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.burst_limit = burst_limit or min(10, requests_per_minute // 2)
        
        # Track request timestamps
        self.minute_requests = deque()
        self.hour_requests = deque()
        
        # Lock for thread safety
        self._lock = asyncio.Lock()
    
    async def wait_if_needed(self):
        """
        Wait if necessary to respect rate limits
        """
        async with self._lock:
            current_time = time.time()
            
            # Clean old requests from tracking
            self._clean_old_requests(current_time)
            
            # Check minute limit
            minute_wait = self._calculate_wait_time(
                self.minute_requests,
                current_time,
                60,  # 60 seconds
                self.requests_per_minute
            )
            
            # Check hour limit
            hour_wait = self._calculate_wait_time(
                self.hour_requests,
                current_time,
                3600,  # 3600 seconds
                self.requests_per_hour
            )
            
            # Wait for the longer of the two
            wait_time = max(minute_wait, hour_wait)
            
            if wait_time > 0:
                await asyncio.sleep(wait_time)
                current_time = time.time()
            
            # Record this request
            self.minute_requests.append(current_time)
            self.hour_requests.append(current_time)
    
    def _clean_old_requests(self, current_time: float):
        """Remove old request timestamps from tracking"""
        # Clean minute requests (older than 60 seconds)
        while self.minute_requests and current_time - self.minute_requests[0] > 60:
            self.minute_requests.popleft()
        
        # Clean hour requests (older than 3600 seconds)
        while self.hour_requests and current_time - self.hour_requests[0] > 3600:
            self.hour_requests.popleft()
    
    def _calculate_wait_time(
        self,
        request_queue: deque,
        current_time: float,
        window_seconds: int,
        max_requests: int
    ) -> float:
        """Calculate how long to wait based on request history"""
        if len(request_queue) < max_requests:
            return 0
        
        # If we're at the limit, wait until the oldest request expires
        oldest_request = request_queue[0]
        time_since_oldest = current_time - oldest_request
        
        if time_since_oldest < window_seconds:
            return window_seconds - time_since_oldest + 0.1  # Small buffer
        
        return 0
    
    def get_stats(self) -> dict:
        """Get current rate limiting statistics"""
        current_time = time.time()
        self._clean_old_requests(current_time)
        
        return {
            "requests_last_minute": len(self.minute_requests),
            "requests_last_hour": len(self.hour_requests),
            "minute_limit": self.requests_per_minute,
            "hour_limit": self.requests_per_hour,
            "minute_utilization": len(self.minute_requests) / self.requests_per_minute * 100,
            "hour_utilization": len(self.hour_requests) / self.requests_per_hour * 100
        }


class AdaptiveRateLimiter(RateLimiter):
    """
    Rate limiter that adapts based on response codes and errors
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.consecutive_errors = 0
        self.base_delay = 1.0
        self.current_delay = self.base_delay
        self.max_delay = 300.0  # 5 minutes max
    
    async def record_response(self, status_code: int, error: bool = False):
        """Record response to adapt rate limiting"""
        if error or status_code == 429:  # Too Many Requests
            self.consecutive_errors += 1
            # Exponential backoff
            self.current_delay = min(
                self.base_delay * (2 ** self.consecutive_errors),
                self.max_delay
            )
        elif status_code == 200:
            # Success - gradually reduce delay
            self.consecutive_errors = max(0, self.consecutive_errors - 1)
            if self.consecutive_errors == 0:
                self.current_delay = max(
                    self.base_delay,
                    self.current_delay * 0.9
                )
    
    async def wait_if_needed(self):
        """Wait with adaptive delay"""
        await super().wait_if_needed()
        
        # Additional adaptive delay
        if self.current_delay > self.base_delay:
            await asyncio.sleep(self.current_delay - self.base_delay)