"""
Database operations for user management
"""
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, List

from src.database import get_connection

import logging
logger = logging.getLogger(__name__)


class UserManager:
    """Manage user data in database"""
    
    @staticmethod
    def create_or_update_user(user_id: int, username: str, api_key: Optional[str] = None) -> bool:
        """Create or update user record"""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO users (user_id, username, api_key)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = ?,
                    api_key = COALESCE(?, api_key),
                    updated_at = CURRENT_TIMESTAMP
            """, (user_id, username, api_key, username, api_key))
            
            conn.commit()
            conn.close()
            logger.info(f"User {user_id} created/updated successfully")
            return True
        except Exception as e:
            logger.error(f"Error creating/updating user: {e}")
            return False
    
    @staticmethod
    def get_user(user_id: int) -> Optional[dict]:
        """Retrieve user by ID"""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            conn.close()
            
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error retrieving user: {e}")
            return None
    
    @staticmethod
    def set_api_key(user_id: int, api_key: str) -> bool:
        """Set or update API key for user"""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE users 
                SET api_key = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (api_key, user_id))
            
            conn.commit()
            conn.close()
            logger.info(f"API key updated for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error setting API key: {e}")
            return False
    
    @staticmethod
    def remove_api_key(user_id: int) -> bool:
        """Remove API key for user"""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE users 
                SET api_key = NULL, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (user_id,))
            
            conn.commit()
            conn.close()
            logger.info(f"API key removed for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error removing API key: {e}")
            return False
    
    @staticmethod
    def has_api_key(user_id: int) -> bool:
        """Check if user has API key set"""
        user = UserManager.get_user(user_id)
        return user and user.get("api_key") is not None


class NumberManager:
    """Manage phone numbers in database"""
    
    @staticmethod
    def save_number(
        user_id: int,
        phone_number: str,
        number_id: str,
        chat_id: int,
        expires_in: int
    ) -> bool:
        """Save active phone number"""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            
            cursor.execute("""
                INSERT INTO active_numbers 
                (user_id, phone_number, number_id, chat_id, expires_at, status)
                VALUES (?, ?, ?, ?, ?, 'waiting')
            """, (user_id, phone_number, number_id, chat_id, expires_at))
            
            conn.commit()
            conn.close()
            logger.info(f"Number saved: {phone_number} for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error saving number: {e}")
            return False
    
    @staticmethod
    def get_active_number(number_id: str) -> Optional[dict]:
        """Retrieve active number by number_id"""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT * FROM active_numbers WHERE number_id = ?", 
                (number_id,)
            )
            row = cursor.fetchone()
            conn.close()
            
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error retrieving number: {e}")
            return None
    
    @staticmethod
    def update_number_status(number_id: str, status: str, message_id: Optional[int] = None) -> bool:
        """Update status of active number"""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            if message_id:
                cursor.execute("""
                    UPDATE active_numbers 
                    SET status = ?, message_id = ?
                    WHERE number_id = ?
                """, (status, message_id, number_id))
            else:
                cursor.execute("""
                    UPDATE active_numbers 
                    SET status = ?
                    WHERE number_id = ?
                """, (status, number_id))
            
            conn.commit()
            conn.close()
            logger.info(f"Number {number_id} status updated to {status}")
            return True
        except Exception as e:
            logger.error(f"Error updating number status: {e}")
            return False
    
    @staticmethod
    def get_user_active_numbers(user_id: int) -> List[dict]:
        """Get all active numbers for user"""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM active_numbers 
                WHERE user_id = ? AND status != 'expired'
                ORDER BY created_at DESC
            """, (user_id,))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error retrieving user numbers: {e}")
            return []


class OTPManager:
    """Manage OTP history in database"""
    
    @staticmethod
    def save_otp(
        user_id: int,
        phone_number: str,
        otp_code: str,
        message: str,
        service: str
    ) -> bool:
        """Save received OTP to history"""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO otp_history 
                (user_id, phone_number, otp_code, message, service)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, phone_number, otp_code, message, service))
            
            conn.commit()
            conn.close()
            logger.info(f"OTP saved for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error saving OTP: {e}")
            return False
    
    @staticmethod
    def get_otp_history(user_id: int, limit: int = 10) -> List[dict]:
        """Get OTP history for user"""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM otp_history 
                WHERE user_id = ?
                ORDER BY received_at DESC
                LIMIT ?
            """, (user_id, limit))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error retrieving OTP history: {e}")
            return []


class PollingManager:
    """Manage polling tasks tracking"""
    
    @staticmethod
    def create_polling_task(user_id: int, number_id: str, task_id: str) -> bool:
        """Create polling task record"""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO polling_tasks 
                (user_id, number_id, task_id, status)
                VALUES (?, ?, ?, 'active')
            """, (user_id, number_id, task_id))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error creating polling task: {e}")
            return False
    
    @staticmethod
    def update_polling_task(task_id: str, status: str) -> bool:
        """Update polling task status"""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE polling_tasks 
                SET status = ?
                WHERE task_id = ?
            """, (status, task_id))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error updating polling task: {e}")
            return False
    
    @staticmethod
    def get_active_task(number_id: str) -> Optional[dict]:
        """Get active polling task for number"""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM polling_tasks 
                WHERE number_id = ? AND status = 'active'
            """, (number_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error retrieving polling task: {e}")
            return None
