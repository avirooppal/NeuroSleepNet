import nsn
from neurosleepnet.adapters.llama_index import NSNMemory
from llama_index.core.agent import ReActAgent
from llama_index.llms.openai import OpenAI

# 1. Initialize NeuroSleepNet
nsn.init(project="llamaindex-demo")

# 2. Setup Native NSN Memory for LlamaIndex
memory = NSNMemory(user_id="user_123", recall_threshold=0.4)

# 3. Plug into any LlamaIndex agent or query engine
llm = OpenAI(model="gpt-3.5-turbo")
agent = ReActAgent.from_tools(
    tools=[], 
    llm=llm, 
    memory=memory,
    verbose=True
)

# NeuroSleepNet handles persistence and multi-session recall automatically.
response = agent.chat("Remember that my space elevator uses carbon nanotubes.")
print(response)
