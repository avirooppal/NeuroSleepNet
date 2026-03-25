from neurosleepnet import wrap

# Dummy example for HuggingFace integration
class MockHFModel:
    def __call__(self, text):
        return {"label": "POSITIVE", "score": 0.99}
        
model = MockHFModel()

# Wrap the model
agent = wrap(model, mode="sidecar")

# Learn
agent.learn(task_id="sentiment_1", input_data="I love this product", label="POSITIVE")

# Predict
out = agent.predict("I really love it")
print("HF Prediction:", out)
