"""
Telegram Notifier Module
Handles sending alerts to Telegram
"""


import requests
from typing import Optional
from models import Signal
from config import TELEGRAM_CONFIG, ALERT_TEMPLATES
import logging

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Sends alerts to Telegram"""
    
    def __init__(
        self, 
        bot_token: str = None, 
        chat_id: str = None,
        enabled: bool = None
    ):
        """
        Initialize Telegram notifier
        
        Args:
            bot_token: Telegram bot token
            chat_id: Telegram chat ID
            enabled: Enable/disable notifications
        """
        self.bot_token = bot_token or TELEGRAM_CONFIG['bot_token']
        self.chat_id = chat_id or TELEGRAM_CONFIG['chat_id']
        self.enabled = enabled if enabled is not None else TELEGRAM_CONFIG['enable_notifications']
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        
    def send_message(self, message: str, parse_mode: str = 'HTML') -> bool:
        """
        Send a message to Telegram
        
        Args:
            message: Message text
            parse_mode: Parse mode (HTML or Markdown)
            
        Returns:
            True if sent successfully
        """
        if not self.enabled:
            logger.info("Telegram notifications disabled")
            return False
        
        if self.bot_token == 'YOUR_BOT_TOKEN_HERE':
            logger.warning("Telegram bot token not configured. Skipping notification.")
            logger.info(f"Would have sent:\n{message}")
            return False
        
        url = f"{self.base_url}/sendMessage"
        payload = {
            'chat_id': self.chat_id,
            'text': message,
            'parse_mode': parse_mode
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            logger.info("Telegram message sent successfully")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False
    
    def send_confirmed_alert(self, signal: Signal) -> bool:
        """
        Send confirmed alert for a signal
        
        Args:
            signal: Signal object
            
        Returns:
            True if sent successfully
        """
        message = self._format_confirmed_alert(signal)
        return self.send_message(message)
    
    def send_alert(self, signal: Signal, alert_type: str) -> bool:
        """
        Send alert (only confirmed type now, early alerts removed)
        
        Args:
            signal: Signal object
            alert_type: 'confirmed' (early removed)
            
        Returns:
            True if sent successfully
        """
        if alert_type == 'confirmed':
            return self.send_confirmed_alert(signal)
        else:
            logger.warning(f"Unknown alert type: {alert_type}")
            return False
    
    def _format_confirmed_alert(self, signal: Signal) -> str:
        """Format confirmed alert message with all compulsory criteria"""
        features = signal.features
        template = ALERT_TEMPLATES['confirmed']
        
        message = template.format(
            symbol=signal.symbol,
            timeframe=signal.timeframe,
            price=getattr(signal, 'current_price', 0.0),
            ema200=getattr(signal, 'current_ema200', 0.0),
            expansion=features.expansion_spread,
            slope_change=features.slope_ratio,
            adx_15m=features.adx_value_15m,
            adx_1h=features.adx_value_1h,
            rsi_15m=features.rsi_value_15m,
            rsi_1h=features.rsi_value_1h,
            volume_ratio=features.volume_ratio
        )
        
        return message
    
    def send_custom_message(self, title: str, content: dict) -> bool:
        """
        Send custom formatted message
        
        Args:
            title: Message title
            content: Dictionary of key-value pairs
            
        Returns:
            True if sent successfully
        """
        message = f"<b>{title}</b>\n\n"
        
        for key, value in content.items():
            message += f"{key}: {value}\n"
        
        return self.send_message(message)
    
    def send_error(self, error_message: str, context: dict = None) -> bool:
        """
        Send error notification
        
        Args:
            error_message: Error description
            context: Additional context
            
        Returns:
            True if sent successfully
        """
        message = f"🚨 <b>ERROR</b>\n\n{error_message}"
        
        if context:
            message += "\n\n<b>Context:</b>\n"
            for key, value in context.items():
                message += f"{key}: {value}\n"
        
        return self.send_message(message)
    
    def send_status_update(self, status: dict) -> bool:
        """
        Send bot status update
        
        Args:
            status: Status dictionary
            
        Returns:
            True if sent successfully
        """
        message = "📊 <b>Bot Status Update</b>\n\n"
        
        for key, value in status.items():
            message += f"<b>{key}:</b> {value}\n"
        
        return self.send_message(message)
    
    def test_connection(self) -> bool:
        """
        Test Telegram connection
        
        Returns:
            True if connection successful
        """
        test_message = "🤖 Trading Bot - Connection Test\n\nIf you see this, the bot is configured correctly!"
        return self.send_message(test_message)
