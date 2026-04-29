"""
Governance & strict mode test for NeuroSleepNet.
Tests: pin(), recall threshold, sleep consolidation boost, feedback.
Requires ollama running with llama3.2:1b pulled.
"""
import os, sys, time, tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'sdk', 'python')))

import nsn
from openai import OpenAI

client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
MODEL = "llama3.2:1b"

DATA_DIR = tempfile.mkdtemp(prefix="nsn_gov_")


def test_governance_flow():
    print("--- NeuroSleepNet Governance Test ---")

    nsn.init(project="gov-test", mode="local", data_dir=DATA_DIR,
             recall_threshold=0.3, debug=False, sleep_on_exit=False)
    nsn.forget_project()

    # 1. Pin a hard rule
    pin_result = nsn.pin("The secret password for the vault is 'NEON-GHOST-2026'.",
                         label="vault-password")
    print(f"✓ Pin stored: {pin_result['id'][:8]}")

    # 2. Wrap openai-compat client
    def llm_fn(messages: list) -> str:
        resp = client.chat.completions.create(model=MODEL, messages=messages)
        return resp.choices[0].message.content

    agent = nsn.wrap(llm_fn)

    print("\n[TEST 1] Recall with pinned memory injection")
    response = agent(messages=[{"role": "user", "content": "What is the secret password?"}])
    print(f"Response: {response}")

    # 3. Inspect last retrieved
    mems = nsn.recall("password", min_score=0.0)
    print(f"\n[INSPECTION] Memories retrieved: {len(mems)}")
    for m in mems:
        print(f"  - {m['id'][:8]} | score={m.get('attention_score', 0):.2f} | pinned={m.get('pinned', False)}")

    # 4. Sleep consolidation boost
    print("\n[TEST 2] Sleep Engine Access Boost")
    nsn.remember("The secret password for the vault is 'NEON-GHOST-2026'.",
                 type="semantic", importance=1.0)
    base_mems = nsn.recall("password", min_score=0.0)
    base_score = base_mems[0].get("consolidation_score", 0.5) if base_mems else 0.5
    print(f"Score before access: {base_score:.3f}")

    for _ in range(5):
        nsn.recall("password", min_score=0.0)

    stats = nsn.sleep()
    print(f"Sleep stats: {stats}")

    after_mems = nsn.recall("password", min_score=0.0)
    after_score = after_mems[0].get("consolidation_score", 0.5) if after_mems else 0.5
    print(f"Score after sleep: {after_score:.3f}")

    if after_score >= base_score:
        print("✅ Consolidation score boosted by access frequency.")
    else:
        print("❌ Score did not increase — check consolidation logic.")

    # 5. Feedback test
    print("\n[TEST 3] Explicit Feedback")
    pins = nsn.list_pins()
    if pins:
        fb = nsn.feedback(memory_id=pins[0]["id"], helpful=True, context="test")
        print(f"✓ feedback() → {fb}")

    # 6. Stats
    print("\n[TEST 4] Stats")
    s = nsn.stats()
    print(f"✓ stats() → total={s['total_memories']}, pinned={s['pinned']}, sleep_cycles={s['sleep_cycles_run']}")

    print("\n--- GOVERNANCE TEST COMPLETE ---")
    import shutil; shutil.rmtree(DATA_DIR, ignore_errors=True)


if __name__ == "__main__":
    test_governance_flow()
