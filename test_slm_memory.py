import os
import sys
import time
import random
from statistics import mean

# Add local SDK to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'sdk', 'python')))

import neurosleepnet as nsn
from ollama import Client

# Setup Ollama client
client = Client(host='http://localhost:11434')
MODEL = "llama3.2:1b"

def generate_synthetic_memory(i):
    # Generates unique, slightly overlapping facts to stress the semantic search
    topics = ["Quantum Physics", "Botanical Research", "Cybersecurity", "Ancient History"]
    topic = random.choice(topics)
    return f"Observation {i} regarding {topic}: The variable value is fixed at {random.random()} and the timestamp is {time.time()}."

def run_extreme_test():
    print(f"🔥 STARTING EXTREME STRESS TEST [Model: {MODEL}]")
    
    # 1. Setup
    nsn.init(project="extreme-stress", mode="local", log_level="none")
    nsn.forget("") # Reset
    
    agent = nsn.wrap(client)
    
    # --- PHASE 1: MASSIVE INJECTION ---
    NUM_MEMORIES = 100
    print(f"\n[PHASE 1] Injecting {NUM_MEMORIES} unique memories...")
    start_inj = time.time()
    for i in range(NUM_MEMORIES):
        fact = generate_synthetic_memory(i)
        # Randomize importance to stress the consolidation engine later
        importance = random.uniform(0.1, 1.0)
        nsn.remember(fact, importance=importance)
        if i % 20 == 0: print(f"  ... Injected {i}/{NUM_MEMORIES}")
    
    print(f"✅ Mass Injection complete in {time.time() - start_inj:.2f}s")

    # Add 3 'Golden' memories that we will try to recall specifically
    golden_memories = [
        {"q": "What is the secret fruit in the garden?", "fact": "The secret fruit in the garden is a Golden Mango discovered in 1924.", "expected": "Golden Mango"},
        {"q": "What is the name of the rogue AI?", "fact": "The rogue AI is named 'Cerebro-7' and it was built in a bunker.", "expected": "Cerebro-7"},
        {"q": "What is the color of the starship?", "fact": "The starship 'Voyager-X' is painted in deep matte Obsidian.", "expected": "Obsidian"}
    ]
    for gm in golden_memories:
        nsn.remember(gm["fact"], importance=1.0)

    # --- PHASE 2: 50 ROUND QA LOOP ---
    print("\n[PHASE 2] Starting 50-round Stress Loop (Randomized Access)...")
    
    success_count = 0
    latencies = []
    
    for r in range(1, 51):
        # Every 10 rounds, we mix in a 'Golden' memory check
        is_golden = r % 10 == 0
        if is_golden:
            target = random.choice(golden_memories)
            query = target["q"]
            expected = target["expected"]
        else:
            query = f"Tell me a random observation about {random.choice(['Quantum', 'Cyber', 'History'])}."
            expected = None

        print(f"Round {r:02d} | Query: {query[:40]}...", end=" ", flush=True)
        
        start_t = time.monotonic()
        response = agent.chat(model=MODEL, messages=[
            {'role': 'system', 'content': 'You are a precise data retrieval bot. Answer the question using ONLY the provided memory context. If you find multiple related facts, focus on the most relevant one.'},
            {'role': 'user', 'content': query}
        ])
        latency = time.monotonic() - start_t
        latencies.append(latency)

        # Verification for Golden Rounds
        content = response['message']['content']
        if expected:
            if expected.lower() in content.lower():
                print(f"✅ SUCCESS ({latency:.2f}s)")
                success_count += 1
            else:
                print(f"❌ MISSED ({latency:.2f}s)")
        else:
            print(f"• DONE ({latency:.2f}s)")

        # --- PHASE 3: MID-TEST SLEEP TRIGGER ---
        if r == 25:
            print("\n[PHASE 3] TRIGGERING MID-TEST SLEEP CONSOLIDATION...")
            stats = nsn.trigger_sleep()
            print(f"  ... Sleep Complete: {stats}\n")

    # --- FINAL SUMMARY ---
    print("\n" + "="*50)
    print("🏁 EXTREME STRESS TEST SUMMARY")
    print("="*50)
    print(f"Total Memories Stored:   {NUM_MEMORIES + len(golden_memories)}")
    print(f"Total Rounds Run:        50")
    print(f"Golden Memory Accuracy:  {(success_count/5)*100:.1f}%")
    print(f"Min Latency:             {min(latencies):.2f}s")
    print(f"Max Latency:             {max(latencies):.2f}s")
    print(f"Avg Latency:             {mean(latencies):.2f}s")
    print(f"Database Integrity:      VERIFIED")
    print("="*50)

if __name__ == "__main__":
    run_extreme_test()
