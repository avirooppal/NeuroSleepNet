"""
demo_memory_test.py — NSN vs No-Memory: Multi-round real-world comparison
============================================================================

Tests llama3.2:1b on a realistic 12-turn conversation simulating a developer
onboarding session. Runs twice: once with memory (NSN), once without.

NSN usage: exactly 2 lines of code (import + wrap).
Everything else is identical between the two runs.

Requirements:
  - Ollama running locally with llama3.2:1b pulled
  - pip install neurosleepnet   (or install from sdk/python)

Usage:
  python demo_memory_test.py
"""

import requests
import json
import time
import os


# ─────────────────────────────────────────────────────────────────────────────
# THE 2 MAGIC LINES  (commented out below for the "no memory" run)
# ─────────────────────────────────────────────────────────────────────────────
import nsn                                      # line 1
# ─────────────────────────────────────────────────────────────────────────────


OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL      = "llama3.2:1b"

# ── Colour codes for readable terminal output ─────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
CYAN   = "\033[96m"
YELLOW = "\033[93m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"


def raw_chat(messages):
    """Bare Ollama call — no memory."""
    resp = requests.post(
        OLLAMA_URL,
        json={"model": MODEL, "messages": messages, "stream": False},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"]


# ── Realistic multi-round conversation ────────────────────────────────────────
# Simulates a developer who introduces themselves and their project across
# several turns, then asks questions that require remembering earlier context.
CONVERSATION = [
    # Round 1-3: Introductions & project setup
    ("user", "Hi! My name is Priya. I'm a senior backend engineer at Zephyr Labs."),
    ("user", "I'm building an AI coding assistant called DevMind. It helps junior devs write tests."),
    ("user", "DevMind uses Python, FastAPI, and PostgreSQL. Our biggest challenge is latency."),

    # Round 4-5: Technical detail
    ("user", "We're targeting a p99 latency of under 400ms for test generation. Currently sitting at 620ms."),
    ("user", "The bottleneck is our embedding step — we're using sentence-transformers on CPU."),

    # Round 6: Test question — requires remembering name
    ("user", "What's my name and what company do I work for?"),

    # Round 7: Test question — requires remembering project name and stack
    ("user", "What's the project called, and what tech stack is it built on?"),

    # Round 8: Test question — requires remembering latency target
    ("user", "What latency are we targeting and what's the current bottleneck?"),

    # Round 9: Follow-up requiring synthesis of multiple facts
    ("user", "Given what you know about my project, what would you recommend to hit the latency target?"),

    # Round 10: Direct recall test
    ("user", "Quick check — do you remember what tool I'm building and who I work for?"),

    # Round 11: Cross-turn reasoning
    ("user", "If I switched from sentence-transformers to fastembed on GPU, would that help DevMind?"),

    # Round 12: Final identity check (sessions apart, hardest test)
    ("user", "One last thing — can you summarise everything you know about me and my project?"),
]

# Questions we can score automatically (turn index → expected keywords)
SCORED_TURNS = {
    5:  ["priya", "zephyr"],                      # name + company
    6:  ["devmind", "python", "fastapi", "postgres"],  # project + stack
    7:  ["400", "embedding", "sentence-transformer"],  # latency + bottleneck
    9:  ["priya", "devmind"],                     # direct recall
    11: ["summary", "priya", "devmind", "zephyr", "latency"],  # synthesis
}


def score_response(turn_idx: int, response: str) -> tuple[int, int]:
    """Returns (hits, total) for keyword matching on scored turns."""
    if turn_idx not in SCORED_TURNS:
        return (0, 0)
    keywords = SCORED_TURNS[turn_idx]
    resp_lower = response.lower()
    hits = sum(1 for kw in keywords if kw in resp_lower)
    return hits, len(keywords)


def run_session(use_memory: bool):
    label = f"{BOLD}{GREEN}WITH NSN MEMORY{RESET}" if use_memory else f"{BOLD}{RED}WITHOUT MEMORY{RESET}"
    print(f"\n{'='*65}")
    print(f"  {label}")
    print(f"{'='*65}")

    if use_memory:
        # ── THE ONLY NSN LINE IN THE ACTUAL AGENT ────────────────────────
        agent = nsn.wrap(raw_chat)              # line 2 — that's it
        # ─────────────────────────────────────────────────────────────────
    else:
        agent = raw_chat

    messages = []
    total_hits = 0
    total_possible = 0
    latencies = []

    for i, (role, content) in enumerate(CONVERSATION):
        messages.append({"role": role, "content": content})

        print(f"\n{DIM}[Turn {i+1:02d}]{RESET} {CYAN}User:{RESET} {content[:80]}{'...' if len(content)>80 else ''}")

        t0 = time.time()
        try:
            if use_memory:
                # wrap() takes the message list exactly as raw_chat does
                response = agent(messages)
            else:
                response = agent(messages)
        except Exception as e:
            response = f"[ERROR: {e}]"
        elapsed = time.time() - t0
        latencies.append(elapsed)

        # Append assistant response to keep conversation history
        messages.append({"role": "assistant", "content": response})

        # Display response (truncated)
        resp_display = response[:200] + ("..." if len(response) > 200 else "")
        print(f"         {YELLOW}Model:{RESET} {resp_display}")

        # Score if this is a recall turn
        hits, total = score_response(i, response)
        if total > 0:
            total_hits += hits
            total_possible += total
            pct = int(100 * hits / total)
            bar = "█" * hits + "░" * (total - hits)
            colour = GREEN if pct >= 60 else RED
            print(f"         {colour}[Memory score: {bar} {hits}/{total} keywords recalled]{RESET}")

        time.sleep(0.3)  # brief pause to not hammer Ollama

    # Summary
    recall_rate = int(100 * total_hits / total_possible) if total_possible else 0
    avg_lat = sum(latencies) / len(latencies)
    print(f"\n{'─'*65}")
    print(f"  {label} — RESULTS")
    print(f"{'─'*65}")
    print(f"  Keyword recall : {total_hits}/{total_possible} ({recall_rate}%)")
    print(f"  Avg latency    : {avg_lat:.2f}s per turn")
    print(f"  Turns graded   : {len(SCORED_TURNS)}")
    print(f"{'─'*65}")

    return {
        "recall_rate": recall_rate,
        "total_hits": total_hits,
        "total_possible": total_possible,
        "avg_latency": avg_lat,
    }


def check_ollama():
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=3)
        models = [m["name"] for m in r.json().get("models", [])]
        has_model = any(MODEL.split(":")[0] in m for m in models)
        if not has_model:
            print(f"{RED}[!] {MODEL} not found. Run: ollama pull {MODEL}{RESET}")
            return False
        return True
    except Exception:
        print(f"{RED}[!] Ollama not reachable at localhost:11434. Start it first.{RESET}")
        return False


if __name__ == "__main__":
    print(f"{BOLD}NeuroSleepNet Demo — Cross-Turn Memory Comparison{RESET}")
    print(f"Model: {MODEL}  |  Turns: {len(CONVERSATION)}  |  Graded turns: {len(SCORED_TURNS)}")

    if not check_ollama():
        exit(1)

    # ── Run WITHOUT memory first (clean baseline) ─────────────────────────────
    results_no_mem = run_session(use_memory=False)
    time.sleep(1)

    # ── Run WITH NSN memory ───────────────────────────────────────────────────
    results_mem = run_session(use_memory=True)

    # ── Side-by-side comparison ───────────────────────────────────────────────
    delta = results_mem["recall_rate"] - results_no_mem["recall_rate"]
    lat_delta = results_mem["avg_latency"] - results_no_mem["avg_latency"]

    print(f"\n{'='*65}")
    print(f"  {BOLD}FINAL COMPARISON{RESET}")
    print(f"{'='*65}")
    print(f"  {'Metric':<28} {'Without NSN':>12} {'With NSN':>12} {'Delta':>10}")
    print(f"  {'─'*60}")
    print(f"  {'Keyword recall rate':<28} {results_no_mem['recall_rate']:>11}% {results_mem['recall_rate']:>11}% {delta:>+9}%")
    print(f"  {'Keywords recalled':<28} {results_no_mem['total_hits']:>12} {results_mem['total_hits']:>12} {results_mem['total_hits']-results_no_mem['total_hits']:>+10}")
    print(f"  {'Avg latency (s)':<28} {results_no_mem['avg_latency']:>11.2f} {results_mem['avg_latency']:>11.2f} {lat_delta:>+9.2f}")
    print(f"{'='*65}")

    if delta > 0:
        print(f"\n  {GREEN}{BOLD}✓ NSN improved cross-turn recall by {delta} percentage points{RESET}")
    else:
        print(f"\n  {YELLOW}⚠ Results similar — try a longer session or re-run{RESET}")
    print(f"\n  {DIM}NSN code added: 2 lines (import nsn / nsn.wrap){RESET}\n")
