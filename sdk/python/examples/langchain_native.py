import nsn
from neurosleepnet.adapters.langchain import NSNMemory
from langchain.chains import ConversationChain
from langchain_openai import ChatOpenAI

# 1. Initialize NeuroSleepNet
nsn.init(project="langchain-demo")

# 2. Setup Native NSN Memory for LangChain
memory = NSNMemory(user_id="user_123", recall_threshold=0.4)

# 3. Plug into any LangChain chain
llm = ChatOpenAI(temperature=0)
conversation = ConversationChain(
    llm=llm, 
    memory=memory,
    verbose=True
)

# That's it! Every interaction is now sleep-consolidated and persistent.
response = conversation.predict(input="I'm building a space elevator in Tokyo.")
print(response)
