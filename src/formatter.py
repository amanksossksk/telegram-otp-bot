"""
UI formatting and message templates for Telegram bot
"""
from datetime import datetime

class MessageFormatter:
    """Format messages for Telegram UI"""
    
    @staticmethod
    def welcome_message() -> str:
        """Welcome message for /start command"""
        return """
🤖 <b>Welcome to Telegram OTP Bot!</b>

This bot helps you manage temporary phone numbers and receive OTP codes.

<b>Quick Start:</b>
• First, set your API key using /setapikey
• Then request numbers with /single or /multiple
• Monitor incoming OTPs in real-time

<b>Available Commands:</b>
/help - Show help
/settings - View settings
/setapikey - Set/update API key
/single - Get single number
/multiple - Get multiple numbers
/cancel - Cancel current operation

Let's get started! 🚀
        """
    
    @staticmethod
    def help_message() -> str:
        """Help message for /help command"""
        return """
<b>🆘 Help & Documentation</b>

<b>Commands:</b>
/start - Start the bot
/help - Show this message
/settings - View your settings
/setapikey - Set/update your API key
/single - Request a single phone number
/multiple - Request multiple numbers
/cancel - Cancel ongoing operation

<b>Features:</b>
✅ Save and manage API keys
✅ Request temporary phone numbers
✅ Monitor OTP messages automatically
✅ View OTP history
✅ Support for multiple numbers

<b>How to Use:</b>
1. Set your API key: /setapikey
2. Request a number: /single or /multiple
3. Wait for OTP messages
4. Copy OTP codes with one click

Need help? Contact support or check documentation.
        """
    
    @staticmethod
    def number_received(phone_number: str, expires_in: int) -> str:
        """Format number received message"""
        minutes = expires_in // 60
        return f"""
<b>📱 Phone Number Ready!</b>

<code>{phone_number}</code>

⏳ <i>Expires in {minutes} minutes</i>

Ready to receive OTP codes. Click the button below to start monitoring.
        """
    
    @staticmethod
    def waiting_for_otp(phone_number: str) -> str:
        """Format waiting for OTP message"""
        return f"""
<b>⏳ Waiting for OTP...</b>

<code>{phone_number}</code>

🔍 Monitoring for incoming messages...
        """
    
    @staticmethod
    def otp_received(
        otp_code: str,
        message: str,
        service: str,
        phone_number: str
    ) -> str:
        """Format OTP received message"""
        return f"""
<b>✅ OTP Received!</b>

<b>Phone:</b> <code>{phone_number}</code>
<b>OTP Code:</b> <code>{otp_code}</code>

<b>Full Message:</b>
<pre>{message}</pre>

<b>Service:</b> {service}
<b>Received:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
    
    @staticmethod
    def number_expired(phone_number: str) -> str:
        """Format number expired message"""
        return f"""
<b>❌ Number Expired</b>

<code>{phone_number}</code>

The number has expired and is no longer available.
Request a new number to continue.
        """
    
    @staticmethod
    def settings_message(username: str, has_api_key: bool) -> str:
        """Format settings message"""
        api_status = "✅ Configured" if has_api_key else "❌ Not Set"
        return f"""
<b>⚙️ Your Settings</b>

<b>Username:</b> @{username}
<b>API Key Status:</b> {api_status}

Use /setapikey to configure your API key.
        """
    
    @staticmethod
    def error_message(error: str) -> str:
        """Format error message"""
        return f"""
<b>❌ Error</b>

{error}

Please try again or contact support.
        """
    
    @staticmethod
    def success_message(message: str) -> str:
        """Format success message"""
        return f"""
<b>✅ Success!</b>

{message}
        """
    
    @staticmethod
    def otp_history(otps: list) -> str:
        """Format OTP history message"""
        if not otps:
            return "<b>📜 OTP History</b>\n\nNo OTP codes received yet."
        
        history_text = "<b>📜 OTP History</b>\n\n"
        for i, otp in enumerate(otps[:10], 1):
            history_text += f"{i}. <code>{otp['otp_code']}</code> - {otp['phone_number']}\n"
        
        return history_text
