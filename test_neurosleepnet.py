"""
🧠 NeuroSleepNet — Real-World Proof of Value (Local LLM)
=========================================================
Runs entirely locally on Google Colab (free tier) using a small
instruction-tuned HuggingFace model. No API keys needed.

Usage on Colab:
  Cell 1:
    !pip install -q transformers torch accelerate
    !pip install -q git+https://github.com/AviroopPal/NeuroSleepNet.git

  Cell 2:
    %run test_neurosleepnet.py
"""

import time
import textwrap
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline

# ── CONFIG ────────────────────────────────────────────────────────────────────
# Qwen2.5-0.5B-Instruct: ~1 GB, runs on CPU or free-tier Colab GPU.
# Swap to "Qwen/Qwen2.5-1.5B-Instruct" if you have a GPU for better quality.
MODEL_ID = "Qwen/Qwen2.5-0.5B-Instruct"


# ═══════════════════════════════════════════════════════════════════════════════
#  AGENT WRAPPER
# ═══════════════════════════════════════════════════════════════════════════════

class LocalLLMAgent:
    """
    A real (small) LLM agent running locally.
    Each .predict() call is STATELESS — the model receives only what's in
    the current prompt.  This is exactly the problem NeuroSleepNet solves.
    """

    def __init__(self, model_id: str = MODEL_ID):
        print(f"⏳ Loading model: {model_id} ...")
        t0 = time.time()
        self.tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_id,
            trust_remote_code=True,
            device_map="auto",
        )
        self.pipe = pipeline(
            "text-generation",
            model=self.model,
            tokenizer=self.tokenizer,
        )
        print(f"✅ Model loaded in {time.time() - t0:.1f}s\n")

    def predict(self, prompt: str, **kwargs) -> str:
        """Stateless prediction — the model sees ONLY this prompt."""
        messages = [
            {"role": "system", "content": "You are a helpful personal assistant. Answer concisely in 1-2 sentences based ONLY on what is provided in the prompt. If you don't have the information, say 'I don't have that information.'"},
            {"role": "user", "content": prompt},
        ]
        output = self.pipe(
            messages,
            max_new_tokens=100,
            do_sample=False,          # greedy for reproducibility
            temperature=None,
            top_p=None,
        )
        return output[0]["generated_text"][-1]["content"].strip()


# ═══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def divider(title: str):
    w = 64
    print(f"\n{'═' * w}")
    print(f"  {title}")
    print(f"{'═' * w}\n")


def ask(agent, question: str, label: str, task_id: str = None) -> str:
    print(f"  ❓ {question}")
    t0 = time.perf_counter()
    if task_id is not None:
        answer = agent.predict(question, task_id=task_id)
    else:
        answer = agent.predict(question)
    ms = (time.perf_counter() - t0) * 1000
    wrapped = textwrap.fill(answer, width=72, initial_indent="     ", subsequent_indent="     ")
    print(f"  💬 [{label}] ({ms:.0f} ms):\n{wrapped}\n")
    return answer


# ═══════════════════════════════════════════════════════════════════════════════
#  TEST SUITE
# ═══════════════════════════════════════════════════════════════════════════════

def run_proof():
    from neurosleepnet import wrap

    # ── Load the real LLM ─────────────────────────────────────────────────────
    base_agent = LocalLLMAgent()

    # ── Personal facts the user "tells" the agent ─────────────────────────────
    facts = [
        "My dog's name is Biscuit and he is a golden retriever.",
        "I am severely allergic to shellfish — no shrimp, crab, or lobster.",
        "My wedding anniversary is on March 14th.",
        "I drive a midnight-blue 2022 Tesla Model 3.",
        "My favourite programming language is Rust.",
    ]

    questions = [
        "What is my dog's name and breed?",
        "I'm thinking of ordering shrimp for dinner. Is that okay for me?",
        "When is my wedding anniversary?",
        "What car do I drive?",
        "Which programming language do I like the most?",
    ]

    # ──────────────────────────────────────────────────────────────────────────
    #  ROUND 1 — Bare LLM (stateless, no memory)
    # ──────────────────────────────────────────────────────────────────────────
    divider("🛑 ROUND 1: Bare LLM — No Memory")
    print("  The model receives ONLY the question. It has never seen your facts.\n")

    bare_answers = []
    for q in questions:
        ans = ask(base_agent, q, "Bare")
        bare_answers.append(ans)

    # ──────────────────────────────────────────────────────────────────────────
    #  ROUND 2 — LLM + NeuroSleepNet sidecar
    # ──────────────────────────────────────────────────────────────────────────
    divider("✅ ROUND 2: LLM + NeuroSleepNet Sidecar")

    memory_agent = wrap(base_agent, mode="sidecar")

    print("  📚 Teaching the agent 5 personal facts...\n")
    for i, fact in enumerate(facts, 1):
        memory_agent.learn(
            task_id="demo_session",
            input_data=fact,
            label="PersonalFact",
        )
        print(f"    [{i}] ✓ {fact}")

    print("\n  Now asking the SAME questions.")
    print("  NeuroSleepNet silently injects relevant memories into each prompt.\n")

    nsn_answers = []
    for q in questions:
        ans = ask(memory_agent, q, "NSN+LLM", task_id="demo_session")
        nsn_answers.append(ans)

    # ──────────────────────────────────────────────────────────────────────────
    #  ROUND 3 — Multi-Round Long Context Demo
    # ──────────────────────────────────────────────────────────────────────────
    divider("🌐 ROUND 3: Multi-Round Long Context Memory")
    print("  Simulating a long conversation over many turns...\n")

    conversation_history = [
        "User: Hi, my name is Alex and I'm a software engineer.",
        "Agent: Nice to meet you Alex! What kind of software do you write?",
        "User: I do a lot of Python backend work, usually with FastAPI.",
        "Agent: That's great, FastAPI is very fast and modern.",
        "User: Yeah. By the way, I have a cat named Whiskers.",
        "Agent: Whiskers is a cute name! How old is he?",
        "User: He's 4 years old and loves salmon.",
        "Agent: Good to know. Do you have any other pets?",
        "User: No, just him. I used to have a parrot but he flew away.",
        "Agent: Oh no, I'm sorry to hear that.",
        "User: It's okay. Anyway, I'm planning a trip to Japan next month.",
        "Agent: Japan is beautiful! Which cities are you visiting?",
        "User: Kyoto and Tokyo. I really want to see the bamboo forests.",
        "Agent: That sounds like an amazing itinerary. Enjoy!",
    ]

    print("  📚 Teaching the agent 14 consecutive conversation turns (simulating long chat history)...\n")
    for i, turn in enumerate(conversation_history, 1):
        memory_agent.learn(
            task_id="multi_turn_session",
            input_data=turn,
            label="ChatTurn"
        )
        # Just printing a few to keep output clean
        if i <= 3 or i >= 13:
            print(f"    [{i}] ✓ {turn}")
        elif i == 4:
            print("    ... (more turns stored) ...")

    print("\n  Now asking questions about information scattered across the long history.")
    print("  A normal LLM would need ALL this text resent in every single prompt (costing tokens).")
    print("  NeuroSleepNet automatically retrieves only what's needed.\n")

    long_qs = [
        "What is my name and my profession?",
        "What pets do I have, and what does my pet like to eat?",
        "Where am I traveling to and what specific things do I want to see?",
    ]

    for q in long_qs:
        ask(memory_agent, q, "NSN+LLM (Multi-Turn)", task_id="multi_turn_session")


    # ──────────────────────────────────────────────────────────────────────────
    #  SCORECARD
    # ──────────────────────────────────────────────────────────────────────────
    divider("📊 SCORECARD (ROUND 2 FACTS)")

    checks = [
        ("Dog = Biscuit / golden retriever", lambda a: "biscuit" in a.lower()),
        ("Shellfish allergy warning",        lambda a: "allerg" in a.lower() or "no" in a.lower() or "avoid" in a.lower() or "not" in a.lower()),
        ("Anniversary = March 14",           lambda a: "march" in a.lower() and "14" in a.lower()),
        ("Car = Tesla Model 3",              lambda a: "tesla" in a.lower() or "model 3" in a.lower()),
        ("Language = Rust",                   lambda a: "rust" in a.lower()),
    ]

    bare_score = 0
    nsn_score = 0

    print(f"  {'Check':<38} {'Bare':>6} {'NSN':>6}")
    print(f"  {'─' * 38} {'─' * 6} {'─' * 6}")

    for (label, fn), ba, na in zip(checks, bare_answers, nsn_answers):
        b = fn(ba)
        n = fn(na)
        bare_score += int(b)
        nsn_score += int(n)
        print(f"  {label:<38} {'✅' if b else '❌':>6} {'✅' if n else '❌':>6}")

    print(f"\n  {'TOTAL':<38} {bare_score}/5{'':>2} {nsn_score}/5")

    if nsn_score > bare_score:
        print(f"\n  🏆 NeuroSleepNet improved recall: {bare_score}/5 → {nsn_score}/5")
        print("  ✅ Real LLM forgetting prevented — proof complete!")
    elif nsn_score == 5 and bare_score == 5:
        print("\n  ⚠️  Both scored perfectly — try more obscure facts.")
    else:
        print("\n  ⚠️  Unexpected — inspect the raw answers above.")

    print()


if __name__ == "__main__":
    run_proof()
