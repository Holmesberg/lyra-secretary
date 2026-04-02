"""Direct Telegram Bot API delivery for reminders and alerts."""
import logging
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


async def send_telegram_message(text: str) -> bool:
    """Send message directly via Telegram Bot API. Returns True if sent."""
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        logger.warning("Telegram not configured — skipping direct delivery")
        return False
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": settings.TELEGRAM_CHAT_ID,
                    "text": text,
                    "parse_mode": "Markdown"
                },
                timeout=5.0
            )
            resp.raise_for_status()
            return True
    except Exception as e:
        logger.error(f"Telegram direct send failed: {e}")
        return False


def send_telegram_message_sync(text: str) -> bool:
    """Sync wrapper for use from APScheduler thread-based jobs."""
    import asyncio
    try:
        return asyncio.run(send_telegram_message(text))
    except Exception as e:
        logger.error(f"Telegram sync wrapper failed: {e}")
        return False
