import hashlib
import logging
import time
from functools import wraps
from typing import Callable, Any

logger = logging.getLogger(__name__)

def retry_with_backoff(max_retries: int, delay: float, backoff: float):
    """Decorator for retry logic with exponential backoff."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt == max_retries:
                        break
                    
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries + 1} failed for {func.__name__}: {e}. "
                        f"Retrying in {current_delay:.2f}s..."
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff
            
            raise last_exception
        return wrapper
    return decorator

def generate_file_checksum(content: bytes) -> str:
    """Generate MD5 checksum for file content."""
    return hashlib.md5(content).hexdigest()

def sanitize_gcs_object_name(s3_key: str) -> str:
    """Sanitize S3 key for GCS object naming conventions."""
    # Remove leading slashes and normalize path
    return s3_key.lstrip('/')
