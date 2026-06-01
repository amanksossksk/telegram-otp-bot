"""
API Client for external OTP service integration
"""
import aiohttp
import os
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

API_BASE_URL = os.getenv("API_BASE_URL", "http://63.141.255.227/api/v1/")
API_TIMEOUT = 10


class APIClient:
    """Client for interacting with OTP API service"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = API_BASE_URL.rstrip("/")
    
    async def get_number(
        self, 
        phone_range: str, 
        format_type: str = "national"
    ) -> Optional[Dict[str, Any]]:
        """
        Request a temporary phone number from the API
        
        Args:
            phone_range: Phone number pattern (e.g., '99298XXX')
            format_type: Format type - 'national', 'normal', or 'noplus'
        
        Returns:
            Dict with number, number_id, and expires_in, or None on failure
        """
        try:
            payload = {
                "range": phone_range,
                "format": format_type
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/numbers/get",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=aiohttp.ClientTimeout(total=API_TIMEOUT)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("success"):
                            logger.info(f"Successfully retrieved number: {data.get('number')}")
                            return data
                    logger.error(f"API error: {resp.status} - {await resp.text()}")
        except aiohttp.ClientError as e:
            logger.error(f"Network error while getting number: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in get_number: {e}")
        
        return None
    
    async def check_otp(self, number_id: str) -> Optional[Dict[str, Any]]:
        """
        Check for incoming OTP messages for a given number
        
        Args:
            number_id: The number ID from get_number response
        
        Returns:
            Dict with OTP status and message, or None on failure
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/numbers/{number_id}/sms",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=aiohttp.ClientTimeout(total=API_TIMEOUT)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("success"):
                            if data.get("otp"):
                                logger.info(f"OTP received for {number_id}: {data.get('otp')}")
                            return data
                    logger.error(f"API error: {resp.status} - {await resp.text()}")
        except aiohttp.ClientError as e:
            logger.error(f"Network error while checking OTP: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in check_otp: {e}")
        
        return None
    
    async def validate_api_key(self) -> bool:
        """
        Validate API key by making a test request
        
        Returns:
            True if API key is valid, False otherwise
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/health",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=aiohttp.ClientTimeout(total=API_TIMEOUT)
                ) as resp:
                    return resp.status in [200, 401, 403]
        except Exception as e:
            logger.error(f"Error validating API key: {e}")
            return False


async def test_connection(api_key: str) -> bool:
    """Test connection to API service"""
    client = APIClient(api_key)
    return await client.validate_api_key()
