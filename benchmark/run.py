import json
import httpx
import time
import os
import sys
import argparse
from typing import List, Dict

# Add SDK to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "sdk", "python")))
import nsn

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2:1b"

def call_llm(prompt: str, context: str = "") -> str:
    # Use the model-specific template if needed, but here we just prepend context
    # Llama 3 usually likes a specific format, but for a simple benchmark, we can do:
    if context:
        full_prompt = f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\nYou are a professional coding assistant. You MUST strictly adhere to the following project context, style preferences, and past decisions found in your memory:\n\n{context}\n\nIf the user asks for suggestions, ensure they align with the above constraints.<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"
    else:
        full_prompt = f"<|begin_of_text|><|start_header_id|>user<|end_header_id|>\n\n{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"
    
    try:
        response = httpx.post(OLLAMA_URL, json={
            "model": MODEL,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": 0.1, # Keep it deterministic
                "num_predict": 256
            }
        }, timeout=60.0)
        return response.json().get("response", "").strip()
    except Exception as e:
        return f"Error: {e}"

def evaluate_response(response: str, expected_subs: List[str], forbidden_subs: List[str] = None) -> float:
    if not response: return 0.0
    score = 0
    for sub in expected_subs:
        if sub.lower() in response.lower():
            score += 1
    
    final_score = (score / len(expected_subs)) * 100 if expected_subs else 100.0
    
    if forbidden_subs:
        for sub in forbidden_subs:
            if sub.lower() in response.lower():
                final_score -= 50 # Penalty
    
    return max(0.0, final_score)

def run_benchmark(mode: str = "nsn"):
    with open("benchmark/scenarios.json", "r") as f:
        scenarios = json.load(f)
    
    if mode == "nsn":
        nsn.init(project="benchmark-run", mode="local", data_dir="./benchmark_data", recall_threshold=0.3)
        nsn.forget_project()
    
    results = []
    print(f"\n--- Running Benchmark Mode: {mode.upper()} ---")
    
    for scenario in scenarios:
        user_id = scenario["user_id"]
        print(f"\nUser: {user_id}")
        
        for session in scenario["sessions"]:
            turn = session["turn"]
            user_input = session["input"]
            
            context = ""
            if mode == "nsn":
                # Use nsn.context for proper formatting
                context = nsn.context(user_input, user_id=user_id, model_family="llama3", min_score=0.2)
                if context:
                    print(f"  [DEBUG] Context injected ({len(context)} chars)")
                else:
                    print(f"  [DEBUG] No context found for this turn.")
            
            response = call_llm(user_input, context)
            
            score = 0.0
            if "evaluation_query" in session:
                score = evaluate_response(response, session.get("expected_substrings", []), session.get("forbidden_substrings", []))
                print(f"  Turn {turn}: Score {score}%")
                if score < 100:
                    print(f"    [FAIL] Response: {response[:150]}...")
            else:
                print(f"  Turn {turn}: (Learning phase)")
            
            if mode == "nsn":
                # Store interaction for future turns
                nsn.remember(user_input, user_id=user_id, type="episodic")
                # Also store the "fact" if explicitly provided in scenario for simulation
                if "expected_fact" in session:
                    nsn.remember(session["expected_fact"], user_id=user_id, type="semantic")
            
            results.append({
                "user": user_id,
                "turn": turn,
                "input": user_input,
                "response": response,
                "context": context,
                "score": score
            })
            
    return results

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["raw", "nsn"], default="nsn")
    args = parser.parse_args()
    
    start_time = time.time()
    results = run_benchmark(args.mode)
    duration = time.time() - start_time
    
    score_turns = [r["score"] for r in results if r["turn"] % 2 == 0]
    avg_score = sum(score_turns) / len(score_turns) if score_turns else 0.0
    
    print(f"\n" + "="*40)
    print(f"RESULTS ({args.mode.upper()})")
    print(f"="*40)
    print(f"Average Memory Score: {avg_score:.1f}%")
    print(f"Total Time: {duration:.1f}s")
    print("="*40)
    
    # Save results
    with open(f"benchmark/results_{args.mode}.json", "w") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    main()
