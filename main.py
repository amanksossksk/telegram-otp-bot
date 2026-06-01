#!/usr/bin/env python3
"""
Entry point for Telegram OTP Bot
Run this file to start the bot
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.bot import main


if __name__ == "__main__":
    asyncio.run(main())
