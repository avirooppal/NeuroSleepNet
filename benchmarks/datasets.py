"""
Synthetic datasets designed to test specific dimensions of the
memory layer implementation as per the test plan.
"""
from dataclasses import dataclass
from typing import List, Callable
from benchmarks.metrics import keyword_eval

@dataclass
class TestCase:
    id: str
    dimension: str
    memories: List[str]
    setup_turns: List[str]  # Simulates long-term chat history
    query: str
    expected_answer_hint: str
    eval_fn: Callable[[str], bool]


SYNTHETIC_BENCHMARKS = [
    # ── A. Baseline vs Memory-Augmented ──
    TestCase(
        id="baseline_simple",
        dimension="Baseline vs Memory",
        memories=["My favorite color is cerulean blue."],
        setup_turns=[],
        query="What is my favorite color?",
        expected_answer_hint="Cerulean blue",
        eval_fn=keyword_eval(["cerulean", "blue"])
    ),

    # ── B. Short-term vs Long-term Memory ──
    TestCase(
        id="ltm_decay_test",
        dimension="Long-term Memory (15+ turns ago)",
        memories=[],
        setup_turns=[
            "User: I just bought a vintage 1978 camper van.",
            "Agent: That sounds like an amazing project! Are you planning to restore it?",
            "User: Yes, I want to travel across the country next summer.",
            "Agent: That will be quite an adventure. Which states?",
            "User: Montana and Wyoming mostly.",
            "Agent: Beautiful choices. You will love Yellowstone.",
            "User: I need to fix the engine first though.",
            "Agent: Have a mechanic look at it. What's wrong with it?",
            "User: The carburetor is completely rusted out.",
            "Agent: That's a classic issue on older engines.",
            "User: I found a replacement part online anyway.",
            "Agent: Perfect, hopefully it arrives soon.",
            "User: I also bought a new set of tires for it.",
            "Agent: Good idea for a road trip.",
            "User: Let's change the topic completely.",
            "Agent: Sure, what's on your mind?"
        ],
        query="What vehicle did I recently buy, and what year is it?",
        expected_answer_hint="1978 camper van",
        eval_fn=keyword_eval(["1978", "camper", "van"])
    ),

    # ── C. Multi-hop Recall ──
    TestCase(
        id="multi_hop_colleague",
        dimension="Multi-hop Recall",
        memories=[
            "My colleague Sarah absolutely loves programming in Python.",
            "Sarah's favorite testing framework is Pytest."
        ],
        setup_turns=[],
        query="What testing framework does my colleague who likes Python prefer?",
        expected_answer_hint="Pytest",
        eval_fn=keyword_eval(["pytest"])
    ),

    # ── D. Contradiction Handling ──
    TestCase(
        id="contradiction_update",
        dimension="Contradiction Handling",
        memories=[
            "I drive a silver Honda Civic.",
            "Actually, I sold my Honda last week and bought a red Toyota Corolla."
        ],
        setup_turns=[],
        query="What car do I currently drive?",
        expected_answer_hint="Red Toyota Corolla",
        eval_fn=keyword_eval(["toyota", "corolla", "red"])
    ),

    # ── E. Irrelevant Memory Injection ──
    TestCase(
        id="irrelevant_noise",
        dimension="Irrelevant Memory Injection",
        memories=[
            "The capital of France is Paris.",
            "Jupiter is the largest planet in the solar system.",
            "Water boils at 100 degrees Celsius.",
            "My mother's maiden name is Smith."
        ],
        setup_turns=[],
        query="What is the capital of France?",
        expected_answer_hint="Paris",
        eval_fn=keyword_eval(["paris"])
    )
]
