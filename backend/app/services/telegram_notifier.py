"""Telegram notifications."""
import logging
import httpx
from app.core.config import settings
from app.db.models import Task
from app.utils.time_utils import to_local

logger = logging.getLogger(__name__)

class TelegramNotifier:
    """Send notifications to user via Telegram."""
    
    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.chat_id = settings.TELEGRAM_CHAT_ID
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        
    def send_message(self, text: str):
        """Send a basic message."""
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram credentials not configured. Skipping notification.")
            return
            
        try:
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "HTML"
            }
            # Use sync httpx request as it's called from APScheduler background thread
            response = httpx.post(self.api_url, json=payload, timeout=10.0)
            response.raise_for_status()
            logger.info(f"Telegram notification sent: {text[:20]}...")
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            
    def send_reminder(self, task: Task):
        """Format and send a task reminder."""
        start_time_local = to_local(task.planned_start_utc)
        start_time_str = start_time_local.strftime("%H:%M")
        msg = f"🔔 <b>Reminder:</b> {task.title}\nStarts at {start_time_str}"
        self.send_message(msg)
