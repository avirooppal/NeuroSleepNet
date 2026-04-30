import json
import os
import sys
import time
from typing import List, Dict

# Import conditions
sys.path.append(os.path.join(os.getcwd(), "benchmarks"))
from conditions import phi3_nsn, phi3_raw, gpt4_raw

def evaluate_response(response: str, expected_subs: List[str], forbidden_subs: List[str] = None) -> bool:
    if not response: return False
    
    # All expected substrings must be present
    for sub in expected_subs:
        if sub.lower() not in response.lower():
            return False
            
    # No forbidden substrings must be present
    if forbidden_subs:
        for sub in forbidden_subs:
            if sub.lower() in response.lower():
                return False
                
    return True

def run_condition(condition_name: str, condition_module, dataset: List[Dict]):
    print(f"\n>>> Running Condition: {condition_name}")
    results = []
    
    for task in dataset:
        task_id = task["task_id"]
        print(f"  Task: {task_id}")
        
        # Reset memory for nsn if needed
        # In this harness, each condition module handles its own init/reset if required
        
        for session in task["sessions"]:
            turn = session["turn"]
            user_input = session["input"]
            
            # Record start time
            start = time.time()
            response = condition_module.run(user_input, user_id=f"user_{task_id}")
            latency = time.time() - start
            
            passed = False
            if "evaluation_query" in session:
                passed = evaluate_response(
                    response, 
                    session.get("expected_substrings", []), 
                    session.get("forbidden_substrings", [])
                )
                status = "PASS" if passed else "FAIL"
                print(f"    Turn {turn}: {status} ({latency:.2f}s)")
            else:
                # Learning turn
                print(f"    Turn {turn}: (Learned)")
                
            results.append({
                "condition": condition_name,
                "task_id": task_id,
                "turn": turn,
                "passed": passed,
                "latency": latency,
                "eval": "evaluation_query" in session
            })
            
    return results

def main():
    if not os.path.exists("benchmarks/datasets/coding_tasks.json"):
        print("Error: benchmarks/datasets/coding_tasks.json not found")
        return

    with open("benchmarks/datasets/coding_tasks.json", "r") as f:
        dataset = json.load(f)
        
    all_results = {}
    
    # 1. Llama-3.2 Raw (Control)
    all_results["llama3_raw"] = run_condition("Llama-3.2 Raw", phi3_raw, dataset)
    
    # 2. GPT-4 Raw (Baseline)
    if os.getenv("OPENAI_API_KEY"):
        all_results["gpt4_raw"] = run_condition("GPT-4 Raw", gpt4_raw, dataset)
    else:
        print("\n[SKIP] GPT-4 Raw (OPENAI_API_KEY not set)")
        
    # 3. Llama-3.2 + NSN (Our Solution)
    all_results["llama3_nsn"] = run_condition("Llama-3.2 + NeuroSleepNet", phi3_nsn, dataset)
    
    # Summary Table
    print("\n" + "="*60)
    print(f"{'Condition':<25} | {'Score':<10} | {'Avg Latency':<12}")
    print("-" * 60)
    
    for name, results in all_results.items():
        eval_turns = [r for r in results if r["eval"]]
        passes = sum(1 for r in eval_turns if r["passed"])
        score = (passes / len(eval_turns)) * 100 if eval_turns else 0
        avg_latency = sum(r["latency"] for r in results) / len(results)
        
        print(f"{name:<25} | {score:>5.1f}%     | {avg_latency:>7.2f}s")
    print("="*60)

if __name__ == "__main__":
    main()
