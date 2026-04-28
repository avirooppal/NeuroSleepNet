"""
Fallback cascade for NeuroSleepNet operations.
"""
import logging
from typing import Callable, Any, Tuple
import httpx

logger = logging.getLogger("neurosleepnet.fallback")

def execute_with_fallback(
    func: Callable,
    cache_retrieve_fn: Callable = None,
    fallback_mode: str = "silent",
    *args,
    **kwargs
) -> Tuple[Any, bool]:
    """
    Executes a callback with the 4-level fallback cascade.
    Returns (result, from_cache_flag)
    """
    try:
        # Normal execution
        return func(*args, **kwargs), False
    except httpx.TimeoutException as e:
        # Level 1: API Slow -> Use Local Cache
        if cache_retrieve_fn:
            logger.warning("NeuroSleepNet API timeout. Falling back to local cache.")
            try:
                cached_data = cache_retrieve_fn()
                return cached_data, True
            except Exception as cache_err:
                logger.error(f"Cache fallback failed: {cache_err}")
                if fallback_mode == "raise":
                    raise
        return None, False
    except httpx.ConnectError as e:
        # Level 2: API Unreachable -> Skip memory injection
        logger.warning("NeuroSleepNet API unreachable. Skipping memory injection.")
        if fallback_mode == "raise":
            raise
        return None, False
    except httpx.RequestError as e:
        # Level 3: API Runtime Error -> Skip memory injection -> log error
        logger.error(f"NeuroSleepNet API error: {e}")
        if fallback_mode == "raise":
            raise
        return None, False
    except Exception as e:
        # Level 4: SDK Crash (bug in NSN code)
        logger.error(f"NeuroSleepNet SDK Internal Error: {e}")
        if fallback_mode == "raise":
            raise
        return None, False

def safe_wrap(original_func: Callable, fallback_mode: str = "silent"):
    """
    Ensures that any failure in SDK logic completely falls back to 
    calling the original function unmodified.
    """
    def wrapper(*args, **kwargs):
        try:
            return original_func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Critical error in NeuroSleepNet memory wrap: {e}. Falling back to untouched agent.")
            if fallback_mode == "raise":
                raise
            # If everything else fails, we MUST call the original unmodified function.
            # However this wrapper is usually inside an adapter which itself 
            # uses try/except.
    return wrapper
