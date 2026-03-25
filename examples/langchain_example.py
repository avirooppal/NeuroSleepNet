from neurosleepnet import wrap

# Dummy example for LangChain integration
class MockLLMChain:
    def predict(self, text):
        return f"AI Response to: {text}"
        
chain = MockLLMChain()

# Wrap it in sidecar mode to auto-inject soft prompts
agent = wrap(chain, mode="sidecar")

agent.learn(task_id="customer_support", input_data="How do I reset my password?", label="Click 'Forgot Password' on login screen.")

response = agent.predict("I can't log in, password reset needed", task_id="customer_support")
print("LangChain Response:\n", response)
