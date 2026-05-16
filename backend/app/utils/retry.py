"""Retry logic."""
import time
import logging
from functools import wraps

logger = logging.getLogger(__name__)

def retry_with_backoff(max_retries=3, base_delay=1.0):
    """Retry decorator with exponential backoff."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = base_delay
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_class = type(e).__name__
                    if attempt == max_retries:
                        logger.error(
                            "Failed after %s retries: %s",
                            max_retries,
                            error_class,
                        )
                        raise
                    logger.warning(
                        "Attempt %s failed: %s. Retrying in %.1fs...",
                        attempt + 1,
                        error_class,
                        delay,
                    )
                    time.sleep(delay)
                    delay *= 2
        return wrapper
    return decorator
