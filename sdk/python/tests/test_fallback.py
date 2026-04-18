import pytest
import httpx
from neurosleepnet.fallback import execute_with_fallback, safe_wrap

def test_execute_with_fallback_success():
    def dummy():
        return "success"
        
    res, from_cache = execute_with_fallback(dummy)
    assert res == "success"
    assert not from_cache

def test_execute_with_fallback_timeout():
    def dummy():
        raise httpx.ReadTimeout("API slow")
        
    def cache_retrieve():
        return "cache_data"
        
    res, from_cache = execute_with_fallback(dummy, cache_retrieve_fn=cache_retrieve)
    assert res == "cache_data"
    assert from_cache

def test_execute_with_fallback_connection_error():
    def dummy():
        raise httpx.ConnectError("API down")
        
    res, from_cache = execute_with_fallback(dummy)
    assert res is None
    assert not from_cache

def test_safe_wrap_protects_agent():
    def original():
        return "original_value"
        
    def bad_wrapper():
        raise ValueError("SDK internal failure")
        
    # safe_wrap wraps the whole adapter logic essentially ensuring we never break the caller
    wrapped = safe_wrap(bad_wrapper, fallback_mode="silent")
    
    # In a real scenario safe_wrap protects the original, the simplified test verifies it doesn't crash on silent mode
    try:
        wrapped()
    except ValueError:
        pytest.fail("safe_wrap raised exception unexpectedly")
    
    raised = False
    wrapped_raise = safe_wrap(bad_wrapper, fallback_mode="raise")
    try:
        wrapped_raise()
    except ValueError:
        raised = True
    assert raised
