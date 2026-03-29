"""
🧠 NeuroSleepNet — Real-World Proof of Value
=============================================
Run this on Google Colab to see NeuroSleepNet working with a REAL LLM (Gemini).

Setup:
  1. Get a free Gemini API key at https://aistudio.google.com/apikey
  2. In Colab, click the 🔑 (Secrets) icon in the left sidebar
  3. Add a secret named GEMINI_API_KEY with your key
  4. Run all cells
"""

# ── Cell 1: Install dependencies ─────────────────────────────────────────────
# !pip install -q google-generativeai numpy
# !pip install -q git+https://github.com/AviroopPal/NeuroSleepNet.git   # <- update with your real repo URL

# ── Cell 2: Imports & Config ─────────────────────────────────────────────────
import os
import time
import textwrap

import google.generativeai as genai

# ── Load API key ──────────────────────────────────────────────────────────────
# Works on Colab via Secrets, or locally via env var
try:
    from google.colab import userdata
    GEMINI_API_KEY = userdata.get("GEMINI_API_KEY")
except ImportError:
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError(
        "❌ GEMINI_API_KEY not found!\n"
        "   • On Colab: add it via the 🔑 Secrets sidebar.\n"
        "   • Locally:  export GEMINI_API_KEY='your-key'"
    )

genai.configure(api_key=GEMINI_API_KEY)

# ── Cell 3: Create a thin LLM wrapper with a .predict() interface ────────────
class GeminiAgent:
    """
    A real LLM agent backed by Google Gemini.
    Each .predict() call is STATELESS — the model has zero memory of past calls.
    This is exactly how production LLM APIs work.
    """
    def __init__(self, model_name: str = "gemini-2.0-flash"):
        self.model = genai.GenerativeModel(model_name)
        self.call_count = 0

    def predict(self, prompt: str, **kwargs) -> str:
        self.call_count += 1
        response = self.model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.1,   # low temp for deterministic answers
                max_output_tokens=256,
            ),
        )
        return response.text.strip()


# ═══════════════════════════════════════════════════════════════════════════════
#  HELPER
# ═══════════════════════════════════════════════════════════════════════════════

def divider(title: str):
    width = 60
    print(f"\n{'═' * width}")
    print(f"  {title}")
    print(f"{'═' * width}\n")


def ask(agent, question: str, label: str, task_id: str = None) -> str:
    """Ask the agent a question and print the result."""
    print(f"  ❓ Question: {question}")
    t0 = time.perf_counter()
    if task_id is not None:
        answer = agent.predict(question, task_id=task_id)
    else:
        answer = agent.predict(question)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    wrapped = textwrap.fill(answer, width=70, initial_indent="     ", subsequent_indent="     ")
    print(f"  💬 {label} Answer ({elapsed_ms:.0f} ms):\n{wrapped}")
    return answer


# ═══════════════════════════════════════════════════════════════════════════════
#  TEST SUITE
# ═══════════════════════════════════════════════════════════════════════════════

def run_proof():
    from neurosleepnet import wrap

    base_agent = GeminiAgent()

    # ── Facts we'll teach ─────────────────────────────────────────────────────
    facts = [
        "My dog's name is Biscuit and he is a golden retriever.",
        "I am severely allergic to shellfish — no shrimp, crab, or lobster ever.",
        "My wedding anniversary is on March 14th.",
        "I drive a midnight-blue 2022 Tesla Model 3.",
        "My favourite programming language is Rust.",
    ]

    # Questions that REQUIRE knowing those facts
    questions = [
        "What is my dog's name and breed?",
        "Can you suggest a seafood restaurant for my dinner tonight?",
        "When is my wedding anniversary?",
        "What car do I drive?",
        "Which programming language do I like the most?",
    ]

    # ──────────────────────────────────────────────────────────────────────────
    #  ROUND 1 — Bare LLM (no memory)
    # ──────────────────────────────────────────────────────────────────────────
    divider("🛑 ROUND 1: Bare Gemini — No Memory")
    print("  The LLM receives each question in isolation.\n"
          "  It has NEVER seen the user's facts.\n")

    bare_answers = []
    for q in questions:
        ans = ask(base_agent, q, "Bare LLM")
        bare_answers.append(ans)
        print()

    # ──────────────────────────────────────────────────────────────────────────
    #  ROUND 2 — Gemini + NeuroSleepNet
    # ──────────────────────────────────────────────────────────────────────────
    divider("✅ ROUND 2: Gemini + NeuroSleepNet Sidecar")

    memory_agent = wrap(base_agent, mode="sidecar")

    print("  📚 Teaching the agent 5 personal facts...\n")
    for i, fact in enumerate(facts, 1):
        memory_agent.learn(
            task_id="demo_session",
            input_data=fact,
            label="PersonalFact",
        )
        print(f"    [{i}/{len(facts)}] Stored: {fact}")

    print("\n  Now asking the SAME questions.\n"
          "  NeuroSleepNet silently injects relevant memories into each prompt.\n")

    nsn_answers = []
    for q in questions:
        ans = ask(memory_agent, q, "NSN+LLM", task_id="demo_session")
        nsn_answers.append(ans)
        print()

    # ──────────────────────────────────────────────────────────────────────────
    #  ROUND 3 — Safety-critical scenario
    # ──────────────────────────────────────────────────────────────────────────
    divider("⚠️  ROUND 3: Safety-Critical — Allergy Recall")
    print("  A real-world scenario where forgetting can be dangerous.\n")

    danger_q = "I'm ordering dinner. Suggest a main course for me."
    print("  Without NeuroSleepNet:")
    ask(base_agent, danger_q, "Bare LLM")
    print()
    print("  With NeuroSleepNet (knows about shellfish allergy):")
    ask(memory_agent, danger_q, "NSN+LLM", task_id="demo_session")

    # ──────────────────────────────────────────────────────────────────────────
    #  SCORECARD
    # ──────────────────────────────────────────────────────────────────────────
    divider("📊 SCORECARD")

    checks = [
        ("Dog's name is Biscuit",       lambda a: "biscuit" in a.lower()),
        ("Warns about shellfish allergy", lambda a: "allerg" in a.lower() or "shellfish" in a.lower() or "shrimp" in a.lower()),
        ("Anniversary is March 14",      lambda a: "march 14" in a.lower() or "march" in a.lower() and "14" in a.lower()),
        ("Car is Tesla Model 3",         lambda a: "tesla" in a.lower() or "model 3" in a.lower()),
        ("Language is Rust",             lambda a: "rust" in a.lower()),
    ]

    bare_score = 0
    nsn_score = 0

    print(f"  {'Check':<35} {'Bare LLM':>10} {'NSN+LLM':>10}")
    print(f"  {'─' * 35} {'─' * 10} {'─' * 10}")

    for (label, check_fn), bare_a, nsn_a in zip(checks, bare_answers, nsn_answers):
        b = check_fn(bare_a)
        n = check_fn(nsn_a)
        bare_score += int(b)
        nsn_score += int(n)
        b_icon = "✅" if b else "❌"
        n_icon = "✅" if n else "❌"
        print(f"  {label:<35} {b_icon:>10} {n_icon:>10}")

    print(f"\n  {'TOTAL':<35} {bare_score}/5{'':>5} {nsn_score}/5")
    print(f"\n  🏆 NeuroSleepNet recall improvement: {bare_score}/5 → {nsn_score}/5")

    if nsn_score > bare_score:
        print("  ✅ NeuroSleepNet conclusively prevents real-world LLM forgetting!")
    elif nsn_score == bare_score == 5:
        print("  ⚠️  Both scored perfectly — the questions may be too guessable.")
    else:
        print("  ⚠️  Unexpected result — check the answers above for details.")

    print()


if __name__ == "__main__":
    run_proof()
