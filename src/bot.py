"""
Main Telegram bot application
"""
import os
import logging
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Set

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from telegram.error import TelegramError

from src.api_client import APIClient, test_connection
from src.database_ops import UserManager, NumberManager, OTPManager, PollingManager
from src.formatter import MessageFormatter
from src.logger import logger

# Active polling tasks tracking
active_tasks: Dict[str, asyncio.Task] = {}
task_locks: Dict[str, asyncio.Lock] = {}


class TelegramOTPBot:
    """Main Telegram OTP Bot Application"""
    
    def __init__(self, token: str):
        self.token = token
        self.app = Application.builder().token(token).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        """Setup command and callback handlers"""
        # Command handlers
        self.app.add_handler(CommandHandler("start", self.handle_start))
        self.app.add_handler(CommandHandler("help", self.handle_help))
        self.app.add_handler(CommandHandler("settings", self.handle_settings))
        self.app.add_handler(CommandHandler("setapikey", self.handle_setapikey))
        self.app.add_handler(CommandHandler("single", self.handle_single))
        self.app.add_handler(CommandHandler("multiple", self.handle_multiple))
        self.app.add_handler(CommandHandler("cancel", self.handle_cancel))
        
        # Message handlers
        self.app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, 
            self.handle_message
        ))
        
        # Callback handlers
        self.app.add_handler(CallbackQueryHandler(self.handle_callback))
    
    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        try:
            user = update.effective_user
            UserManager.create_or_update_user(user.id, user.username or "Unknown")
            
            await update.message.reply_html(
                MessageFormatter.welcome_message()
            )
            logger.info(f"User {user.id} started bot")
        except Exception as e:
            logger.error(f"Error in handle_start: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")
    
    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        try:
            await update.message.reply_html(MessageFormatter.help_message())
        except Exception as e:
            logger.error(f"Error in handle_help: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")
    
    async def handle_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /settings command"""
        try:
            user = update.effective_user
            has_key = UserManager.has_api_key(user.id)
            
            message = MessageFormatter.settings_message(
                user.username or "Unknown",
                has_key
            )
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔑 Set API Key", callback_data="set_api_key")],
                [InlineKeyboardButton("❌ Remove API Key", callback_data="remove_api_key")] if has_key else [],
                [InlineKeyboardButton("📜 OTP History", callback_data="view_history")]
            ])
            
            await update.message.reply_html(message, reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Error in handle_settings: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")
    
    async def handle_setapikey(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /setapikey command"""
        try:
            context.user_data["waiting_for_api_key"] = True
            await update.message.reply_text(
                "🔑 <b>Set Your API Key</b>\n\n"
                "Please send your API key. This will be stored securely.",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Error in handle_setapikey: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")
    
    async def handle_single(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /single command"""
        try:
            user = update.effective_user
            
            if not UserManager.has_api_key(user.id):
                await update.message.reply_text(
                    "❌ Please set your API key first using /setapikey"
                )
                return
            
            context.user_data["waiting_for_range"] = True
            await update.message.reply_text(
                "📱 <b>Get Single Number</b>\n\n"
                "Enter phone number range pattern:\n"
                "Example: <code>99298XXX</code>\n\n"
                "X represents any digit.",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Error in handle_single: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")
    
    async def handle_multiple(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /multiple command"""
        try:
            user = update.effective_user
            
            if not UserManager.has_api_key(user.id):
                await update.message.reply_text(
                    "❌ Please set your API key first using /setapikey"
                )
                return
            
            context.user_data["waiting_for_count"] = True
            await update.message.reply_text(
                "📱 <b>Get Multiple Numbers</b>\n\n"
                "How many numbers do you need? (1-5)",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Error in handle_multiple: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")
    
    async def handle_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /cancel command"""
        try:
            user = update.effective_user
            
            # Clear user state
            context.user_data.clear()
            
            # Cancel any active polling tasks for this user
            tasks_to_cancel = [
                task_id for task_id in list(active_tasks.keys())
                if str(user.id) in task_id
            ]
            
            for task_id in tasks_to_cancel:
                if task_id in active_tasks:
                    active_tasks[task_id].cancel()
                    del active_tasks[task_id]
            
            await update.message.reply_text(
                "✅ Operation cancelled.",
                parse_mode="HTML"
            )
            logger.info(f"User {user.id} cancelled operation")
        except Exception as e:
            logger.error(f"Error in handle_cancel: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages"""
        try:
            user = update.effective_user
            text = update.message.text
            
            # Handle API key input
            if context.user_data.get("waiting_for_api_key"):
                context.user_data["waiting_for_api_key"] = False
                
                # Validate API key
                if await test_connection(text):
                    UserManager.set_api_key(user.id, text)
                    await update.message.reply_text(
                        "✅ API key saved successfully!",
                        parse_mode="HTML"
                    )
                    logger.info(f"API key set for user {user.id}")
                else:
                    await update.message.reply_text(
                        "❌ Invalid API key. Please try again.",
                        parse_mode="HTML"
                    )
                return
            
            # Handle phone range input for single number
            if context.user_data.get("waiting_for_range"):
                context.user_data["waiting_for_range"] = False
                await self.get_single_number(update, context, text)
                return
            
            # Handle count input for multiple numbers
            if context.user_data.get("waiting_for_count"):
                context.user_data["waiting_for_count"] = False
                try:
                    count = int(text)
                    if 1 <= count <= 5:
                        context.user_data["number_range"] = None
                        context.user_data["waiting_for_range"] = True
                        await update.message.reply_text(
                            f"📱 <b>Get {count} Numbers</b>\n\n"
                            "Enter phone number range pattern:\n"
                            "Example: <code>99298XXX</code>",
                            parse_mode="HTML"
                        )
                    else:
                        await update.message.reply_text(
                            "❌ Please enter a number between 1 and 5."
                        )
                except ValueError:
                    await update.message.reply_text(
                        "❌ Please enter a valid number."
                    )
                return
        
        except Exception as e:
            logger.error(f"Error in handle_message: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")
    
    async def get_single_number(self, update: Update, context: ContextTypes.DEFAULT_TYPE, phone_range: str):
        """Get single number from API"""
        try:
            user = update.effective_user
            user_data = UserManager.get_user(user.id)
            
            if not user_data or not user_data.get("api_key"):
                await update.message.reply_text("❌ API key not configured.")
                return
            
            status_msg = await update.message.reply_text("🔄 Requesting number...")
            
            api_client = APIClient(user_data["api_key"])
            result = await api_client.get_number(phone_range, "national")
            
            if result and result.get("success"):
                phone_number = result.get("number")
                number_id = result.get("number_id")
                expires_in = result.get("expires_in", 1200)
                
                # Save to database
                NumberManager.save_number(
                    user.id,
                    phone_number,
                    number_id,
                    update.effective_chat.id,
                    expires_in
                )
                
                # Send number message
                await update.message.reply_html(
                    MessageFormatter.number_received(phone_number, expires_in),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔍 Look For Code", callback_data=f"check_otp_{number_id}")]
                    ])
                )
                
                await status_msg.delete()
                logger.info(f"Number {phone_number} provided to user {user.id}")
            else:
                await status_msg.edit_text(
                    "❌ Failed to get number. Please try again."
                )
        except Exception as e:
            logger.error(f"Error in get_single_number: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline button callbacks"""
        try:
            query = update.callback_query
            await query.answer()
            
            user = update.effective_user
            callback_data = query.data
            
            if callback_data.startswith("check_otp_"):
                number_id = callback_data.replace("check_otp_", "")
                await self.start_otp_polling(query, context, number_id)
            
            elif callback_data == "set_api_key":
                context.user_data["waiting_for_api_key"] = True
                await query.edit_message_text(
                    "🔑 Please send your API key."
                )
            
            elif callback_data == "remove_api_key":
                UserManager.remove_api_key(user.id)
                await query.edit_message_text(
                    "✅ API key removed."
                )
            
            elif callback_data == "view_history":
                otps = OTPManager.get_otp_history(user.id)
                await query.edit_message_text(
                    MessageFormatter.otp_history(otps),
                    parse_mode="HTML"
                )
        
        except Exception as e:
            logger.error(f"Error in handle_callback: {e}")
            await query.edit_message_text("❌ An error occurred.")
    
    async def start_otp_polling(
        self, 
        query, 
        context: ContextTypes.DEFAULT_TYPE, 
        number_id: str
    ):
        """Start polling for OTP on background"""
        try:
            user = update.effective_user if hasattr(query, 'from_user') else query.from_user
            
            # Check if task already exists
            existing_task = PollingManager.get_active_task(number_id)
            if existing_task:
                await query.edit_message_text(
                    "⏳ Already monitoring this number..."
                )
                return
            
            # Get user API key
            user_data = UserManager.get_user(user.id)
            if not user_data or not user_data.get("api_key"):
                await query.edit_message_text("❌ API key not found.")
                return
            
            # Get number info
            number_info = NumberManager.get_active_number(number_id)
            if not number_info:
                await query.edit_message_text("❌ Number not found.")
                return
            
            phone_number = number_info["phone_number"]
            
            # Create polling task
            task_id = f"{user.id}_{number_id}_{uuid.uuid4()}"
            task_lock = asyncio.Lock()
            task_locks[task_id] = task_lock
            
            PollingManager.create_polling_task(user.id, number_id, task_id)
            
            # Update message
            await query.edit_message_text(
                MessageFormatter.waiting_for_otp(phone_number),
                parse_mode="HTML"
            )
            
            # Create and start polling task
            poll_task = asyncio.create_task(
                self._poll_otp(
                    user.id,
                    number_id,
                    task_id,
                    user_data["api_key"],
                    phone_number,
                    query.message.chat_id
                )
            )
            
            active_tasks[task_id] = poll_task
            logger.info(f"Started polling for {number_id}")
            
        except Exception as e:
            logger.error(f"Error in start_otp_polling: {e}")
            await query.edit_message_text("❌ An error occurred.")
    
    async def _poll_otp(
        self,
        user_id: int,
        number_id: str,
        task_id: str,
        api_key: str,
        phone_number: str,
        chat_id: int
    ):
        """Poll OTP with background task"""
        try:
            api_client = APIClient(api_key)
            start_time = datetime.utcnow()
            poll_timeout = 1200  # 20 minutes
            
            while True:
                # Check timeout
                if (datetime.utcnow() - start_time).total_seconds() > poll_timeout:
                    await self.app.bot.send_message(
                        chat_id,
                        MessageFormatter.number_expired(phone_number),
                        parse_mode="HTML"
                    )
                    NumberManager.update_number_status(number_id, "expired")
                    break
                
                # Check OTP
                result = await api_client.check_otp(number_id)
                
                if result and result.get("success"):
                    if result.get("otp"):
                        # OTP received
                        otp_code = result.get("otp")
                        message = result.get("message", "")
                        service = result.get("service", "Unknown")
                        
                        # Save to history
                        OTPManager.save_otp(user_id, phone_number, otp_code, message, service)
                        
                        # Update status
                        NumberManager.update_number_status(number_id, "received")
                        
                        # Send OTP message
                        await self.app.bot.send_message(
                            chat_id,
                            MessageFormatter.otp_received(otp_code, message, service, phone_number),
                            parse_mode="HTML"
                        )
                        
                        logger.info(f"OTP received for user {user_id}: {otp_code}")
                        break
                
                # Wait before next poll
                await asyncio.sleep(2)
        
        except asyncio.CancelledError:
            logger.info(f"Polling task {task_id} cancelled")
        except Exception as e:
            logger.error(f"Error in _poll_otp: {e}")
        finally:
            # Cleanup
            PollingManager.update_polling_task(task_id, "completed")
            if task_id in active_tasks:
                del active_tasks[task_id]
            if task_id in task_locks:
                del task_locks[task_id]
    
    async def run(self):
        """Start the bot"""
        logger.info("Starting Telegram OTP Bot...")
        await self.app.run_polling()


async def main():
    """Main entry point"""
    from src.database import init_database
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Initialize database
    init_database()
    
    # Get bot token
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        logger.error("BOT_TOKEN not found in environment variables")
        return
    
    # Create and run bot
    bot = TelegramOTPBot(bot_token)
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
