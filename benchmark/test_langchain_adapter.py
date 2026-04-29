import os
import sys
from typing import Any, List, Optional

# Mock LangChain to avoid dependency issues in the runner
class MockLLM:
    def invoke(self, input_data, config=None, **kwargs):
        return {"output": "I remembered the space elevator!"}
    
    def __call__(self, *args, **kwargs):
        return self.invoke(*args, **kwargs)

# Add SDK to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "sdk", "python")))
import nsn
from neurosleepnet.adapters.langchain import NSNMemory

def test_langchain_memory_native():
    print("--- Testing Native LangChain NSNMemory Bridge ---")
    
    # 1. Init NSN
    nsn.init(project="lc-bridge-test", mode="local", data_dir="./test_lc_data")
    nsn.forget_project()
    
    # 2. Store a memory manually first
    user_id = "tester"
    nsn.remember("The secret code is 12345.", user_id=user_id)
    
    # 3. Setup NSNMemory
    memory = NSNMemory(user_id=user_id, recall_threshold=0.1)
    
    # 4. Simulate LangChain's 'load_memory_variables'
    # This is what a Chain calls before sending to LLM
    vars = memory.load_memory_variables({"input": "What is the secret code?"})
    print(f"Loaded memory variables: {vars}")
    
    # 5. Verify the memory was loaded
    if "12345" in vars.get("history", ""):
        print("✅ SUCCESS: LangChain memory bridge correctly retrieved the secret code!")
    else:
        print("❌ FAILURE: LangChain memory bridge failed to retrieve the secret code.")
    
    # 6. Simulate 'save_context'
    # This is what a Chain calls after LLM returns
    memory.save_context({"input": "Thanks!"}, {"output": "You are welcome."})
    
    # Verify the interaction was stored
    mems = nsn.recall("Thanks!", user_id=user_id)
    if any("Thanks!" in m["content"] for m in mems):
        print("✅ SUCCESS: LangChain memory bridge correctly saved the conversation context!")
    else:
        print("❌ FAILURE: LangChain memory bridge failed to save the conversation context.")

if __name__ == "__main__":
    test_langchain_memory_native()
