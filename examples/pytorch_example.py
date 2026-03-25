import torch
import torch.nn as nn
from neurosleepnet import wrap

# 1. Define a standard model
class SimpleNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc = nn.Linear(10, 2)
        
    def forward(self, x):
        return self.fc(x)
        
model = SimpleNet()

# 2. Wrap it with NeuroSleepNet
# 3 lines of integration
agent = wrap(model, task_boundary="auto")

# 3. Train and predict as normal
x_dummy = torch.randn(1, 10)
agent.learn(task_id="task_1", input_data=x_dummy.numpy(), label=1)
out = agent.predict(x_dummy)

print("Prediction:", out)
print("Memory buffer size:", len(agent.buffer.sample(100)))
