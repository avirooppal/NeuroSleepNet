"""
Extreme stress test for NeuroSleepNet local mode.
Requires ollama running with llama3.2:1b pulled.
"""
import os, sys, time, random
from statistics import mean

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'sdk', 'python')))

import nsn
from ollama import Client

client = Client(host='http://localhost:11434')
MODEL = "llama3.2:1b"


def generate_synthetic_memory(i):
    topics = ["Quantum Physics", "Botanical Research", "Cybersecurity", "Ancient History"]
    topic = random.choice(topics)
    return f"Observation {i} regarding {topic}: The variable value is fixed at {random.random():.6f} and the timestamp is {time.time():.3f}."


def run_extreme_test():
    print(f"🔥 STARTING EXTREME STRESS TEST [Model: {MODEL}]")

    nsn.init(project="stress-test", mode="local", debug=False, recall_threshold=0.3)
    nsn.forget_project()  # Reset

    def ollama_fn(messages: list) -> str:
        resp = client.chat(model=MODEL, messages=messages)
        return resp['message']['content']

    agent = nsn.wrap(ollama_fn)

    # --- PHASE 1: MASSIVE INJECTION ---
    NUM_MEMORIES = 100
    print(f"\n[PHASE 1] Injecting {NUM_MEMORIES} unique memories...")
    start_inj = time.time()
    for i in range(NUM_MEMORIES):
        fact = generate_synthetic_memory(i)
        importance = random.uniform(0.1, 1.0)
        nsn.remember(fact, type="episodic", importance=importance)
        if i % 20 == 0:
            print(f"  ... Injected {i}/{NUM_MEMORIES}")

    print(f"✅ Mass Injection complete in {time.time() - start_inj:.2f}s")

    golden_memories = [
        {"q": "What is the secret fruit in the garden?", "fact": "The secret fruit in the garden is a Golden Mango discovered in 1924.", "expected": "Golden Mango"},
        {"q": "What is the name of the rogue AI?", "fact": "The rogue AI is named 'Cerebro-7' and it was built in a bunker.", "expected": "Cerebro-7"},
        {"q": "What is the color of the starship?", "fact": "The starship 'Voyager-X' is painted in deep matte Obsidian.", "expected": "Obsidian"},
    ]
    for gm in golden_memories:
        nsn.remember(gm["fact"], type="semantic", importance=1.0)

    # --- PHASE 2: 50 ROUND QA LOOP ---
    print("\n[PHASE 2] Starting 50-round Stress Loop (Randomized Access)...")
    success_count, latencies = 0, []

    for r in range(1, 51):
        is_golden = r % 10 == 0
        if is_golden:
            target = random.choice(golden_memories)
            query, expected = target["q"], target["expected"]
        else:
            query = f"Tell me a random observation about {random.choice(['Quantum', 'Cyber', 'History'])}."
            expected = None

        print(f"Round {r:02d} | Query: {query[:40]}...", end=" ", flush=True)
        start_t = time.monotonic()
        response = agent(messages=[
            {'role': 'system', 'content': 'You are a precise data retrieval bot. Answer using ONLY the provided memory context.'},
            {'role': 'user', 'content': query},
        ])
        latency = time.monotonic() - start_t
        latencies.append(latency)

        if expected:
            if expected.lower() in response.lower():
                print(f"✅ SUCCESS ({latency:.2f}s)")
                success_count += 1
            else:
                print(f"❌ MISSED ({latency:.2f}s)")
        else:
            print(f"• DONE ({latency:.2f}s)")

        # --- PHASE 3: MID-TEST SLEEP ---
        if r == 25:
            print("\n[PHASE 3] TRIGGERING MID-TEST SLEEP CONSOLIDATION...")
            stats = nsn.sleep()
            print(f"  ... Sleep Complete: {stats}\n")

    # --- SUMMARY ---
    golden_rounds = 5
    print("\n" + "=" * 50)
    print("🏁 EXTREME STRESS TEST SUMMARY")
    print("=" * 50)
    print(f"Total Memories Stored:   {NUM_MEMORIES + len(golden_memories)}")
    print(f"Total Rounds Run:        50")
    print(f"Golden Memory Accuracy:  {(success_count / golden_rounds) * 100:.1f}%")
    print(f"Min Latency:             {min(latencies):.2f}s")
    print(f"Max Latency:             {max(latencies):.2f}s")
    print(f"Avg Latency:             {mean(latencies):.2f}s")
    final_stats = nsn.stats()
    print(f"Final Memory Stats:      {final_stats}")
    print("=" * 50)


if __name__ == "__main__":
    run_extreme_test()
