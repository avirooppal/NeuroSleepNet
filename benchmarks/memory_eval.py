import os
import sys
import time
import argparse
import textwrap
from dataclasses import dataclass
from typing import List

# Ensure we can import from the root level (test_neurosleepnet and neurosleepnet)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from test_neurosleepnet import LocalLLMAgent
    from neurosleepnet import wrap
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Please ensure you are running this script from the workspace.")
    sys.exit(1)

from benchmarks.datasets import SYNTHETIC_BENCHMARKS, TestCase


def print_divider(title: str):
    w = 70
    print(f"\n{'=' * w}")
    print(f"  {title}")
    print(f"{'=' * w}\n")


def run_benchmark_for_model(model_id: str):
    print_divider(f"Loading Evaluator for Model: {model_id}")
    try:
        base_agent = LocalLLMAgent(model_id=model_id)
        # Create augmented sidecar version
        memory_agent = wrap(base_agent, mode="sidecar")
    except Exception as e:
        print(f"Failed to load {model_id}: {e}")
        return

    results = []
    
    for case in SYNTHETIC_BENCHMARKS:
        print_divider(f"TEST: {case.dimension} ({case.id})")
        print(f"  Q: {case.query}")
        print(f"  Expected: {case.expected_answer_hint}\n")
        
        # 1. Provide Context to Memory Agent (Simulation)
        task_id = f"bench_{case.id}"
        
        # Load facts
        for fact in case.memories:
            memory_agent.learn(task_id=task_id, input_data=fact, label="Fact")
            
        # Load chat history
        for turn in case.setup_turns:
            memory_agent.learn(task_id=task_id, input_data=turn, label="ChatTurn")

        # 2. RUN BASELINE (No context, purely relying on model weights)
        # (Standard LLMs usually have 'context window', but here we are strictly
        # validating if memory layer works automatically vs prompt forgetting)
        t0 = time.time()
        baseline_ans = base_agent.predict(case.query)
        baseline_latency = (time.time() - t0) * 1000
        baseline_acc = case.eval_fn(baseline_ans)

        # 3. RUN AUGMENTED
        t1 = time.time()
        augmented_ans = memory_agent.predict(case.query, task_id=task_id)
        augmented_latency = (time.time() - t1) * 1000
        augmented_acc = case.eval_fn(augmented_ans)

        # 4. STORE RESULTS
        result = {
            "model": model_id,
            "test_id": case.id,
            "dimension": case.dimension,
            "baseline_score": 1 if baseline_acc else 0,
            "baseline_ms": baseline_latency,
            "augmented_score": 1 if augmented_acc else 0,
            "augmented_ms": augmented_latency,
            "latency_overhead": augmented_latency - baseline_latency
        }
        results.append(result)

        b_status = "✅" if baseline_acc else "❌"
        a_status = "✅" if augmented_acc else "❌"

        print(f"  [Baseline] {b_status} ({baseline_latency:.0f}ms): {textwrap.shorten(baseline_ans, 80)}")
        print(f"  [Augmented] {a_status} ({augmented_latency:.0f}ms): {textwrap.shorten(augmented_ans, 80)}")
        print(f"  -> Overhead: {result['latency_overhead']:.0f}ms\n")

    # Final Scorecard for Model
    print_divider(f"SCORECARD FOR {model_id}")
    print(f"  {'Dimension':<35} | {'Baseline':>8} | {'Augmented':>9} | {'Overhead':>10}")
    print(f"  {'-'*35}-+-{'-'*8}-+-{'-'*9}-+-{'-'*10}")
    
    total_base = 0
    total_aug = 0
    
    for r in results:
        total_base += r["baseline_score"]
        total_aug += r["augmented_score"]
        print(f"  {r['dimension']:<35} | {r['baseline_score']:>8} | {r['augmented_score']:>9} | +{r['latency_overhead']:>7.0f}ms")

    print(f"\n  TOTAL ACCURACY:  Baseline {total_base}/{len(results)}  vs  Augmented {total_aug}/{len(results)}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NeuroSleepNet Memory Benchmarks")
    parser.add_argument("--model", type=str, default="Qwen/Qwen2.5-0.5B-Instruct", 
                        help="HuggingFace model ID to benchmark")
    parser.add_argument("--all", action="store_true", 
                        help="Run against all recommended test dimensions")
    args = parser.parse_args()

    models_to_test = [args.model]
    if args.all:
        models_to_test = [
            "Qwen/Qwen2.5-0.5B-Instruct",
            "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
        ]

    print("🚀 Starting NeuroSleepNet Memory Evaluation Suite")
    for m in models_to_test:
        run_benchmark_for_model(m)
