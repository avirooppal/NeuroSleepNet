import neurosleepnet as nsn
import time

# 1. Initialize (Zero-config)
nsn.init(project="test-run", data_dir="./test_data")

# 2. Store a memory
nsn.remember("The project deadline is Friday at 5 PM.", importance=1.0)
print("✓ Memory stored.")

# 3. Recall the memory
results = nsn.recall("When is the deadline?")
if results:
    print(f"✓ Recalled: {results[0]['content']}")

# 4. Trigger a manual Sleep Cycle
print("Consolidating memories...")
stats = nsn.sleep()
print(f"✓ Sleep Stats: {stats}")

# 5. Check the Dashboard (Local)
# This will print the URL to your local dashboard
nsn.dashboard(open_browser=False)
print('[NeuroSleepNet] Dashboard server is running – press Ctrl+C to stop')
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print('\n[NeuroSleepNet] Dashboard server stopped by user')
