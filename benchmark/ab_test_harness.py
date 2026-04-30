import asyncio
import uuid
import time
import requests
import json
import os
from typing import List, Dict

# Settings
API_URL = os.getenv("NSN_API_URL", "http://localhost:8000/api/v1")
API_KEY = os.getenv("NSN_API_KEY", "nsn_live_L6OKF1UipXrYJwgEe7I8HuXWPA-9pADbHhlGPMIdVUc")
PROJECT_NAME = "ab-test-harness"

# Test Data: Ground Truth Dataset (Query, Expected Substring, Distractor Substring)
GROUND_TRUTH = [
    ("What is the project deadline?", "June 15th", "May 10th"),
    ("Who is the lead architect?", "Sarah Chen", "Mark Lee"),
    ("What is the database password?", "redacted", "admin"),
    ("How do I reset the server?", "scripts/reset.sh", "reboot"),
    ("What is the API endpoint?", "api.nsn.io", "staging.nsn.io"),
    ("What is the main codebase language?", "Python and Javascript", "Java"),
    ("How many nodes are in the graph?", "200 nodes", "50 nodes"),
    ("What is the feedback mechanism?", "EMA-based implicit feedback", "Manual feedback"),
    ("What is the master key format?", "32-char hex", "Base64"),
    ("Where are logs stored?", "/logs/overview.txt", "/tmp/logs"),
]

class ABTestHarness:
    def __init__(self, api_key: str, project_id: str):
        self.api_key = api_key
        self.project_id = project_id
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

    def store_memories(self, memories: List[str]):
        print(f"Storing {len(memories)} test memories...")
        for m in memories:
            resp = requests.post(
                f"{API_URL}/memories/remember",
                headers=self.headers,
                json={"content": m, "project_id": self.project_id}
            )
            if resp.status_code >= 400:
                print(f"Error storing memory: {resp.text}")
            time.sleep(0.1) # Avoid slamming rate limit too hard even if pro
        
        # Give the backend a moment to finish any background tasks
        time.sleep(2)

    def run_recall_test(self, query: str) -> List[Dict]:
        resp = requests.get(
            f"{API_URL}/memories/retrieve",
            headers=self.headers,
            params={"query": query, "project_id": self.project_id, "top_k": 5}
        )
        if resp.status_code >= 400:
             print(f"Error retrieving: {resp.text}")
             return []
        return resp.json().get("memories", [])

    def send_implicit_feedback(self, text: str, memory_ids: List[str]):
        resp = requests.post(
            f"{API_URL}/feedback/implicit",
            headers=self.headers,
            json={"text": text, "memory_ids": memory_ids}
        )
        if resp.status_code >= 400:
            print(f"Error sending feedback: {resp.text}")

    def evaluate(self, signals: List[tuple]) -> Dict[str, float]:
        hits_at_1 = 0
        reciprocal_ranks = []
        
        for query, expected, distractor in signals:
            results = self.run_recall_test(query)
            
            # Find rank of first hit
            rank = 0
            for i, r in enumerate(results):
                content = r['memory']['content'].lower()
                if expected.lower() in content:
                    rank = i + 1
                    break
            
            if rank == 1:
                hits_at_1 += 1
            
            if rank > 0:
                reciprocal_ranks.append(1.0 / rank)
            else:
                reciprocal_ranks.append(0.0)
                
        return {
            "p@1": hits_at_1 / len(signals),
            "mrr": sum(reciprocal_ranks) / len(signals)
        }

def main():
    if not API_KEY:
        print("Error: NSN_API_KEY must be set.")
        return

    harness = ABTestHarness(API_KEY, PROJECT_NAME)
    
    # Pre-populate some noise memories
    harness.store_memories([
        f"Random noise memory fragment #{i}" for i in range(10)
    ])

    # 1. Baseline - Store BOTH correct and distractor memories
    print("--- Phase 1: Baseline (Cold Start) ---")
    memories_to_store = []
    for query, expected, distractor in GROUND_TRUTH:
        memories_to_store.append(f"The correct answer for '{query}' is {expected}")
        memories_to_store.append(f"An incorrect or old answer for '{query}' is {distractor}")
    
    harness.store_memories(memories_to_store)
    
    baseline = harness.evaluate(GROUND_TRUTH)
    print(f"Baseline P@1: {baseline['p@1']*100:.1f}% | MRR: {baseline['mrr']:.3f}")

    # 2. Inject feedback loop - 50 total signals (5 per ground truth pair)
    print("\n--- Phase 2: Implicit Feedback Learning (50 Signals) ---")
    signals_sent = 0
    for _ in range(5): # 5 iterations over the truth set
        for query, expected, distractor in GROUND_TRUTH:
            results = harness.run_recall_test(query)
            # Identify the distractor and the correct memory in results
            correct_id = None
            distractor_id = None
            for r in results:
                content = r['memory']['content'].lower()
                if expected.lower() in content:
                    correct_id = r['memory']['id']
                if distractor.lower() in content:
                    distractor_id = r['memory']['id']
            
            if distractor_id:
                # Negative feedback for distractor
                harness.send_implicit_feedback("No, that's incorrect information.", [distractor_id])
                signals_sent += 1
                time.sleep(0.05)
            
            if correct_id:
                # Positive feedback for correct
                harness.send_implicit_feedback("Yes, that's exactly right!", [correct_id])
                signals_sent += 1
                time.sleep(0.05)
            
            if signals_sent >= 50:
                break
        if signals_sent >= 50:
            break
            
    print(f"Sent {signals_sent} feedback signals.")
    time.sleep(2) # Wait for background tasks to settle

    # 3. Final Measurement
    print("\n--- Phase 3: Final Verification (Post-Learning) ---")
    final = harness.evaluate(GROUND_TRUTH)
    print(f"Final P@1: {final['p@1']*100:.1f}% | MRR: {final['mrr']:.3f}")
    
    p_delta = final['p@1'] - baseline['p@1']
    mrr_delta = final['mrr'] - baseline['mrr']
    print(f"Net P@1 Delta: {p_delta*100:+.1f}% | MRR Delta: {mrr_delta:+.3f}")

if __name__ == "__main__":
    main()
