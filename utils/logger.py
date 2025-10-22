"""
Logging utilities for the pump.fun scraper
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


def setup_logger(
    name: str,
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    format_string: Optional[str] = None
) -> logging.Logger:
    """
    Set up a logger with console and optional file output
    """
    
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear any existing handlers to avoid duplicate logs
    logger.handlers.clear()
    
    # Default format
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    formatter = logging.Formatter(format_string)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(exist_ok=True)
        
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(getattr(logging, log_level.upper()))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


class ScrapeLogger:
    """
    Enhanced logger for scraping operations with statistics tracking
    """
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.stats = {
            "start_time": None,
            "requests_made": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "tokens_scraped": 0,
            "transactions_scraped": 0,
            "errors": []
        }
    
    def start_session(self):
        """Start a new scraping session"""
        self.stats["start_time"] = datetime.now()
        self.logger.info("Starting new scraping session")
    
    def log_request(self, url: str, success: bool = True, error: str = None):
        """Log an API/web request"""
        self.stats["requests_made"] += 1
        
        if success:
            self.stats["successful_requests"] += 1
            self.logger.debug(f"Successful request to: {url}")
        else:
            self.stats["failed_requests"] += 1
            if error:
                self.stats["errors"].append(f"{datetime.now().isoformat()}: {error}")
            self.logger.warning(f"Failed request to: {url} - Error: {error}")
    
    def log_tokens_scraped(self, count: int):
        """Log number of tokens scraped"""
        self.stats["tokens_scraped"] += count
        self.logger.info(f"Scraped {count} tokens (Total: {self.stats['tokens_scraped']})")
    
    def log_transactions_scraped(self, count: int):
        """Log number of transactions scraped"""
        self.stats["transactions_scraped"] += count
        self.logger.info(f"Scraped {count} transactions (Total: {self.stats['transactions_scraped']})")
    
    def log_rate_limit_hit(self, wait_time: float):
        """Log when rate limit is hit"""
        self.logger.warning(f"Rate limit hit, waiting {wait_time:.2f} seconds")
    
    def log_session_summary(self):
        """Log session summary statistics"""
        if self.stats["start_time"]:
            duration = datetime.now() - self.stats["start_time"]
            success_rate = (
                self.stats["successful_requests"] / self.stats["requests_made"] * 100
                if self.stats["requests_made"] > 0 else 0
            )
            
            summary = f"""
Scraping Session Summary:
Duration: {duration}
Requests: {self.stats['requests_made']} (Success: {success_rate:.1f}%)
Tokens Scraped: {self.stats['tokens_scraped']}
Transactions Scraped: {self.stats['transactions_scraped']}
Errors: {len(self.stats['errors'])}
            """
            
            self.logger.info(summary)
            
            if self.stats["errors"]:
                self.logger.error("Recent errors:")
                for error in self.stats["errors"][-5:]:  # Show last 5 errors
                    self.logger.error(f"  {error}")
    
    def get_stats(self) -> dict:
        """Get current session statistics"""
        stats = self.stats.copy()
        if stats["start_time"]:
            stats["duration"] = datetime.now() - stats["start_time"]
        return stats


class RotatingFileHandler(logging.Handler):
    """
    Custom rotating file handler for log files
    """
    
    def __init__(self, base_filename: str, max_bytes: int = 10*1024*1024, backup_count: int = 5):
        super().__init__()
        self.base_filename = base_filename
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.current_size = 0
        
        # Create log directory if it doesn't exist
        Path(base_filename).parent.mkdir(exist_ok=True)
        
        # Initialize current log file
        self.current_file = self._open_log_file()
    
    def _open_log_file(self):
        """Open the current log file"""
        log_path = Path(self.base_filename)
        if log_path.exists():
            self.current_size = log_path.stat().st_size
        else:
            self.current_size = 0
        
        return open(self.base_filename, 'a', encoding='utf-8')
    
    def _rotate_logs(self):
        """Rotate log files when size limit is reached"""
        self.current_file.close()
        
        base_path = Path(self.base_filename)
        
        # Rotate existing backup files
        for i in range(self.backup_count - 1, 0, -1):
            old_file = base_path.with_suffix(f'.{i}{base_path.suffix}')
            new_file = base_path.with_suffix(f'.{i+1}{base_path.suffix}')
            
            if old_file.exists():
                if new_file.exists():
                    new_file.unlink()
                old_file.rename(new_file)
        
        # Move current file to .1
        if base_path.exists():
            backup_file = base_path.with_suffix(f'.1{base_path.suffix}')
            if backup_file.exists():
                backup_file.unlink()
            base_path.rename(backup_file)
        
        # Open new current file
        self.current_file = self._open_log_file()
    
    def emit(self, record):
        """Emit a log record"""
        try:
            msg = self.format(record) + '\n'
            self.current_file.write(msg)
            self.current_file.flush()
            
            self.current_size += len(msg.encode('utf-8'))
            
            if self.current_size >= self.max_bytes:
                self._rotate_logs()
        
        except Exception:
            self.handleError(record)
    
    def close(self):
        """Close the handler"""
        if self.current_file:
            self.current_file.close()
        super().close()