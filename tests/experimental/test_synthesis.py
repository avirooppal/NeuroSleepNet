import nsn
import os
import shutil
from neurosleepnet.local_sleep import Synthesizer
from neurosleepnet import _ctx

class MockSynthesizer(Synthesizer):
    def synthesize(self, memories):
        return "The user loves espresso and has it every morning as a ritual."

def test_synthesis():
    print("--- Testing V2 Synthesis ---")
    data_dir = "./test_nsn_synthesis"
    if os.path.exists(data_dir):
        shutil.rmtree(data_dir)
        
    nsn.init(project="test-synthesis", data_dir=data_dir, synthesis_mode=True)
    
    # Add 3 related episodic memories (using a prefix that will cluster)
    nsn.remember("Morning espresso ritual is great.", type="episodic")
    nsn.remember("Morning espresso ritual is nice.", type="episodic")
    nsn.remember("Morning espresso ritual helps me wake up.", type="episodic")
    
    # Manually boost consolidation to trigger synthesis cluster logic
    with _ctx.local_store._conn() as c:
        c.execute("UPDATE memories SET consolidation_score = 0.8")
        c.commit()
    
    # Inject mock synthesizer
    _ctx.sleep_engine.synthesizer = MockSynthesizer()
    
    # Trigger sleep
    print("Triggering sleep...")
    _ctx.sleep_engine._run_synthesis_pass()
    
    # Check memories
    mems = nsn.list_memories(limit=10)
    print("\nMemories after synthesis:")
    for m in mems:
        print(f"- [{m.get('memory_type')}] {m.get('label') or ''}: {m.get('content')}")
        
    # Verify we have a synthesized memory
    has_synth = any("[synthesized]" in (m.get("label") or "") for m in mems)
    print(f"\nSynthesized memory found: {has_synth}")
    
    # Cleanup
    nsn.sleep_pause()
    nsn.forget_project()

if __name__ == "__main__":
    test_synthesis()
