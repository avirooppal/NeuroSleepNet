"""
benchmarks/metrics.py
Utilities for scoring evaluations, calculating overhead, and 
structuring the delta between baseline and augmented runs.
"""
from typing import List, Callable

def calculate_accuracy_score(prediction: str, ground_truth: str) -> float:
    """
    A placeholder for more advanced LLM-as-a-judge scoring.
    Currently uses simple exact match or substring heuristics if passed directly.
    """
    return 1.0 if ground_truth.lower() in prediction.lower() else 0.0

def keyword_eval(keywords: List[str], must_contain_all: bool = True) -> Callable[[str], bool]:
    """
    Returns an evaluation function that checks if specific keywords 
    exist in the final answer.
    """
    def evaluator(ans: str) -> bool:
        lower_ans = ans.lower()
        if must_contain_all:
            return all(kw.lower() in lower_ans for kw in keywords)
        else:
            return any(kw.lower() in lower_ans for kw in keywords)
    return evaluator
