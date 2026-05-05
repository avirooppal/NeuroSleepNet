import pytest
from neurosleepnet.adapters import get_adapter
from neurosleepnet.adapters.generic import GenericAdapter
from neurosleepnet.adapters.langchain import LangChainAdapter

# Mock objects
class MockLangChainAgent:
    def invoke(self, input_text, config=None, **kwargs):
        return f"Invoked: {input_text}"
        
    def stream(self, input_text, config=None, **kwargs):
        yield f"Invoked: {input_text}"

class MockGenericCallable:
    def __call__(self, arg):
        return f"Called: {arg}"

def test_get_adapter_langchain():
    agent = MockLangChainAgent()
    adapter = get_adapter(agent)
    assert isinstance(adapter, LangChainAdapter)

def test_get_adapter_generic():
    agent = MockGenericCallable()
    adapter = get_adapter(agent)
    assert isinstance(adapter, GenericAdapter)

def test_langchain_wrapper():
    agent = MockLangChainAgent()
    adapter = get_adapter(agent)
    
    # Mock retrieve and log fns
    def dummy_retrieve(query):
        return [{"content": "Important fact."}]
        
    def dummy_log(q, m, r):
        pass

    wrapped = adapter.wrap_call(agent, dummy_retrieve, dummy_log)
    res = wrapped.invoke("Hello")
    assert "Important fact." in res
    assert "Hello" in res

def test_generic_wrapper():
    agent = MockGenericCallable()
    adapter = get_adapter(agent)
    
    def dummy_retrieve(query):
        return [{"content": "Remember this."}]
        
    def dummy_log(q, m, r):
        pass

    wrapped = adapter.wrap_call(agent, dummy_retrieve, dummy_log)
    res = wrapped("Hi")
    assert "Remember this." in res
    assert "Hi" in res
