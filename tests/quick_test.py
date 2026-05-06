import neurosleepnet as nsn
import time
import os
import shutil
from neurosleepnet.local_sleep import Synthesizer
from neurosleepnet import _ctx

# Mock Synthesizer for V2 Verification
class QuickSynthesizer(Synthesizer):
    def synthesize(self, memories):
        return f"[Synthesized Fact] The project deadline is strictly Friday at 5 PM, based on {len(memories)} related reports."

def run_v2_test():
    print("--- NeuroSleepNet V2 Quick Verification ---")
    data_dir = "./test_data_v2"
    if os.path.exists(data_dir):
        shutil.rmtree(data_dir)

    # 1. Initialize with Synthesis Mode enabled
    nsn.init(project="v2-verify", data_dir=data_dir, synthesis_mode=True, debug=True)
    
    # Inject our mock synthesizer
    if _ctx.sleep_engine:
        _ctx.sleep_engine.synthesizer = QuickSynthesizer()

    print("\n[Step 1] Verifying Stage 2 Re-ranking...")
    # Add a nuanced pair
    nsn.remember("The project deadline is Friday at 5 PM.", importance=0.8)
    nsn.remember("The project deadline might be moved to next Monday.", importance=0.5) # Distractor
    
    # Recall with a query that matches 'Friday' specifically
    results = nsn.recall("Is the deadline definitely Friday at 5 PM?", top_k=2, min_score=0.1)
    if results:
        print(f"✓ Recalled Top Hit: {results[0]['content']} (Score: {results[0]['attention_score']})")
    
    print("\n[Step 2] Verifying Memory Synthesis...")
    # Add multiple episodic memories with same prefix (first 3 words) to trigger clustering
    nsn.remember("Deadline report cutoff: Friday 5pm confirmed.", type="episodic")
    nsn.remember("Deadline report cutoff: Meeting 5pm Friday.", type="episodic")
    nsn.remember("Deadline report cutoff: 5pm Friday is the hard cutoff.", type="episodic")
    
    # Manually boost consolidation for test
    with _ctx.local_store._conn() as c:
        c.execute("UPDATE memories SET consolidation_score = 0.8 WHERE content LIKE 'Deadline report cutoff%'")
        c.commit()

    print("Triggering synthesis pass...")
    _ctx.sleep_engine._run_synthesis_pass()
    
    # Verify synthesis
    mems = nsn.list_memories(limit=10)
    synthesized = [m for m in mems if "[synthesized]" in (m.get("label") or "")]
    if synthesized:
        print(f"✓ Synthesis Success: {synthesized[0]['content']}")
    else:
        # Debug why it failed
        print("✗ Synthesis failed to create a master node.")
        print(f"Active memories: {[m['content'] for m in mems]}")

    # 3. Check the Dashboard (Local)
    print("\n[Step 3] Launching Dashboard...")
    nsn.dashboard(open_browser=False)
    print('[NeuroSleepNet] Dashboard server is running – press Ctrl+C to stop')
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('\n[NeuroSleepNet] Test complete. Cleaning up...')
        nsn.sleep_pause()
        nsn.forget_project()

if __name__ == "__main__":
    run_v2_test()
