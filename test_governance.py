import os
import sys

# Add local SDK to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'sdk', 'python')))

import neurosleepnet as nsn

def test_governance():
    print("🧠 TESTING NEURO-SLEEP-NET GOVERNANCE LAYER")
    nsn.init(project="gov-test", mode="local", log_level="none")
    nsn.forget("") # Reset

    # 1. SECURITY TEST: Sanitization
    print("\n[1] Security: Sanitizing PII and Scripts...")
    # Memory containing an email and a script tag
    nsn.remember("My email is boss@apple.com and <script>alert(1)</script>")
    
    results = nsn.recall("email", top_k=1)
    if results:
        res = results[0]
        print(f"Stored as: {res['content']}")
        if "[EMAIL_REDACTED]" in res['content'] and "<script>" not in res['content']:
            print("✅ Sanitization Successful!")
        else:
            print("❌ Sanitization Failed.")
    else:
        print("❌ No memory found for sanitization test.")

    # 2. CONFLICT TEST: Preference Update
    print("\n[2] Consistency: Resolving Semantic Conflicts...")
    nsn.remember("My favorite color is Blue.", importance=1.0)
    print("Turn 1: My favorite color is Blue.")
    
    # Overwrite with high semantic overlap
    nsn.remember("My favorite color is Red.", importance=1.0)
    print("Turn 2: My favorite color is Red.")
    
    mems = nsn.recall("what is my favorite color?", top_k=5)
    print(f"Recall count: {len(mems)}")
    for m in mems:
        print(f" - {m['content']} (Score: {m['attention_score']:.3f})")
    
    if len(mems) == 1 and "Red" in mems[0]['content']:
        print("✅ Conflict Resolution Successful!")
    else:
        print("❌ Conflict Resolution Failed.")

    # 3. CONFIDENCE TEST: Thresholding
    print("\n[3] Hallucination: Confidence Thresholding...")
    mems = nsn.recall("who is the president of Mars?")
    for m in mems:
        print(f" - Unexpected Match: {m['content']} (Score: {m['attention_score']:.3f})")
    print(f"Query: 'President of Mars' -> Memories Found: {len(mems)}")
    if len(mems) == 0:
        print("✅ Confidence Guardrail Successful! (Refused to return irrelevant junk)")
    else:
        print(f"❌ Confidence Guardrail Failed. Returned {len(mems)} irrelevant items.")

if __name__ == "__main__":
    try:
        test_governance()
    except Exception as e:
        print(f"ERROR: {e}")
