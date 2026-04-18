# Integration Guides

Five framework-specific guides for integrating NeuroSleepNet.

---

## 1. LangChain (`AgentExecutor`)

```bash
pip install neurosleepnet langchain langchain-openai
```

```python
import neurosleepnet as nsn
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.tools import tool
from langchain import hub

nsn.init(api_key="YOUR_NSN_KEY", project="langchain-demo")

llm = ChatOpenAI(model="gpt-4o-mini")
prompt = hub.pull("hwchase17/openai-functions-agent")

@tool
def search_web(query: str) -> str:
    """Search the web for current information."""
    return f"Result for: {query}"

agent = create_openai_functions_agent(llm, [search_web], prompt)
executor = AgentExecutor(agent=agent, tools=[search_web])

# One line — wraps invoke() AND hooks on_tool_end() for trace capture
executor = nsn.wrap(executor)

result = executor.invoke({"input": "What did we discuss last session?"})
print(result["output"])
```

**What NSN captures:** Final responses AND intermediate tool observations via `NSNCallbackHandler.on_tool_end()`.

> **LangGraph note:** LangGraph uses a different architecture. Use `nsn.wrap(node_fn)` on individual graph nodes — full LangGraph support is planned for v1.1.

---

## 2. OpenAI SDK

```bash
pip install neurosleepnet openai
```

```python
import neurosleepnet as nsn
from openai import OpenAI

nsn.init(api_key="YOUR_NSN_KEY", project="openai-demo")

client = OpenAI(api_key="YOUR_OPENAI_KEY")
client = nsn.wrap(client)

# Unchanged call pattern — NSN injects context transparently
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "What's my favourite language?"}]
)
print(response.choices[0].message.content)
```

**Streaming:**
```python
stream = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Tell me about myself."}],
    stream=True
)
# NSN buffers silently — your loop is unchanged
for chunk in stream:
    print(chunk.choices[0].delta.content or "", end="", flush=True)
```

---

## 3. HuggingFace Transformers

```bash
pip install "neurosleepnet[local_llm]"
```

```python
import neurosleepnet as nsn
from transformers import pipeline

nsn.init(api_key="YOUR_NSN_KEY", project="hf-demo")

# Wrap before use — works with any chat-template pipeline
pipe = pipeline("text-generation", model="Qwen/Qwen1.5-0.5B-Chat", device_map="auto")
pipe = nsn.wrap(pipe, model_context_limit=2048)

messages = [{"role": "user", "content": "What is my preferred programming language?"}]
result = pipe(messages, max_new_tokens=200)
print(result[0]["generated_text"][-1]["content"])
```

**Memory is injected** as a `system` message prepended to the conversation automatically.

**Run a before/after benchmark:**
```bash
nsn-bench run --model Qwen/Qwen1.5-0.5B-Chat --scenarios all
```

---

## 4. Ollama

```bash
pip install neurosleepnet ollama
```

```python
import neurosleepnet as nsn
import ollama

nsn.init(api_key="YOUR_NSN_KEY", project="ollama-demo", offline_cache=True)

# Wrap the callable directly
def my_agent(prompt: str) -> str:
    response = ollama.generate(model="llama3.2", prompt=prompt)
    return response["response"]

my_agent = nsn.wrap(my_agent)

# NSN prepends retrieved memories to the prompt automatically
print(my_agent("What do I usually ask about?"))
```

**Chat interface:**
```python
def chat_agent(messages: list) -> str:
    response = ollama.chat(model="llama3.2", messages=messages)
    return response["message"]["content"]

chat_agent = nsn.wrap(chat_agent)
```

---

## 5. Anthropic Claude

```bash
pip install neurosleepnet anthropic
```

```python
import neurosleepnet as nsn
from anthropic import Anthropic

nsn.init(api_key="YOUR_NSN_KEY", project="claude-demo")

client = Anthropic(api_key="YOUR_ANTHROPIC_KEY")

# NSN wraps the callable — GenericAdapter intercepts the call
def ask_claude(prompt: str) -> str:
    message = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text

ask_claude = nsn.wrap(ask_claude)

response = ask_claude("What projects have we worked on?")
print(response)
```

**For async usage (Claude streaming):**
```python
import asyncio

async def ask_claude_async(prompt: str) -> str:
    async with client.messages.stream(
        model="claude-3-haiku-20240307",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    ) as stream:
        return await stream.get_final_text()

ask_claude_async = nsn.wrap(ask_claude_async)  # Detected as async, routed correctly
result = asyncio.run(ask_claude_async("Summarise our previous discussions."))
```

---

## Common Patterns Across All Integrations

### Storing memories manually
```python
nsn.remember("User prefers Python and hates verbose APIs.", tags=["preferences"])
nsn.remember("User is building a medical AI assistant.", tags=["context"], importance=0.9)
```

### Export and restore memory state
```python
# Backup
nsn.snapshot(path="backup.json")

# Restore on another machine / fresh instance
nsn.restore([], from_file="backup.json")
```

### Control group for benchmarking
```python
# Disable memory injection — identical agent, pure baseline
baseline_agent = nsn.wrap(agent)         # disabled=False (default)

nsn.init(api_key="...", disabled=True)
control_agent = nsn.wrap(agent)          # no-op wrap — original returned unchanged
```
