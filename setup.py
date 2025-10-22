#!/usr/bin/env python3
"""
Setup script for pump.fun scraper
"""

import subprocess
import sys
from pathlib import Path


def run_command(command, description):
    """Run a shell command and handle errors"""
    print(f"📋 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, 
                              capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        print(f"Error output: {e.stderr}")
        return False


def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8 or higher is required")
        print(f"Current version: {version.major}.{version.minor}.{version.micro}")
        return False
    
    print(f"✅ Python version {version.major}.{version.minor}.{version.micro} is compatible")
    return True


def create_directories():
    """Create necessary directories"""
    directories = ["data", "logs", "data/tokens", "data/transactions", "data/launches", "data/daily"]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    print("✅ Created necessary directories")
    return True


def install_requirements():
    """Install Python requirements"""
    return run_command(
        f"{sys.executable} -m pip install -r requirements.txt",
        "Installing Python packages"
    )


def install_playwright():
    """Install Playwright browsers"""
    return run_command(
        f"{sys.executable} -m playwright install chromium",
        "Installing Playwright browsers"
    )


def create_config():
    """Create default configuration if it doesn't exist"""
    config_path = Path("config.yaml")
    
    if config_path.exists():
        print("✅ Configuration file already exists")
        return True
    
    try:
        from config import ScraperConfig
        config = ScraperConfig()
        config.save("config.yaml")
        print("✅ Created default configuration file")
        return True
    except Exception as e:
        print(f"❌ Failed to create configuration: {e}")
        return False


def test_installation():
    """Test if the scraper can be imported and basic functionality works"""
    print("🧪 Testing installation...")
    
    try:
        # Test imports
        from config import ScraperConfig
        from models import TokenInfo, TransactionData
        from utils.rate_limiter import RateLimiter
        from utils.data_storage import DataStorage
        from utils.logger import setup_logger
        
        # Test basic functionality
        config = ScraperConfig()
        rate_limiter = RateLimiter()
        data_storage = DataStorage("data")
        logger = setup_logger("test")
        
        print("✅ All imports and basic functionality work correctly")
        return True
    
    except Exception as e:
        print(f"❌ Installation test failed: {e}")
        return False


def main():
    """Main setup function"""
    print("🚀 Setting up Pump.fun Scraper")
    print("=" * 50)
    
    steps = [
        ("Checking Python version", check_python_version),
        ("Creating directories", create_directories),
        ("Installing Python packages", install_requirements),
        ("Installing Playwright browsers", install_playwright),
        ("Creating configuration", create_config),
        ("Testing installation", test_installation)
    ]
    
    failed_steps = []
    
    for description, function in steps:
        print()
        if not function():
            failed_steps.append(description)
    
    print("\n" + "=" * 50)
    
    if failed_steps:
        print("❌ Setup completed with errors:")
        for step in failed_steps:
            print(f"  • {step}")
        print("\nPlease resolve these issues and run setup again.")
        sys.exit(1)
    else:
        print("🎉 Setup completed successfully!")
        print("\nNext steps:")
        print("1. Review and modify config.yaml if needed")
        print("2. Run: python scrape.py --help")
        print("3. Start scraping: python scrape.py --quick")
        print("\nFor more information, see README.md")


if __name__ == "__main__":
    main()