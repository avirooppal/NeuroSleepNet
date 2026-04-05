import os
import sys

# Add the parent directory to sys.path to allow importing from local 'neurosleepnet'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from neurosleepnet.client import NeuroSleepClient

def main():
    # 1. Initialize Client (assuming default API key or mock for now)
    client = NeuroSleepClient(
        api_key="nsn_live_your_key_here",
        base_url="http://localhost:8001/api/v1"
    )

    print("🚀 Initializing NeuroSleepNet Example...")

    try:
        # 2. Check health
        # health = client._request("GET", "/health") 
        # print(f"✅ Health Status: {health['status']}")

        # 3. Create a task
        print("\n📝 Creating context 'Agent-User Learning'...")
        task = client.create_task("Agent-User Learning")
        task_id = task["id"]
        print(f"✅ Task created with ID: {task_id}")

        # 4. Add memories
        print("\n🧠 Adding memories...")
        client.add_memory(
            content="The user's favorite programming language is Python and they dislike Java.",
            task_id=task_id,
            metadata={"source": "conversation_01", "type": "preference"}
        )
        client.add_memory(
            content="The user is currently working on a production-ready AI platform called NeuroSleepNet.",
            task_id=task_id,
            metadata={"source": "conversation_01", "type": "project"}
        )
        print("✅ Memories added.")

        # 5. Search with Attention scorer
        print("\n🔍 Searching for user preferences...")
        results = client.search(
            query="What are the user's coding interests?",
            task_id=task_id,
            top_k=2
        )

        for i, res in enumerate(results["memories"], 1):
            print(f"\nResult {i}:")
            print(f" - Content: {res['content']}")
            print(f" - Attention Score: {res['attention_score']:.2f}")
            print(f" - Explanation: {res['why_retrieved']}")

        # 6. Check dashboard stats
        print("\n📊 Fetching dashboard stats...")
        stats = client.get_stats()
        print(f" - Total Memories: {stats['total_memories']}")
        print(f" - Monthly Ops: {stats['monthly_ops']}")
        print(f" - Memory Health: {stats['memory_health_score']}%")

        # 7. Nightly Sleep Phase (forced trigger)
        print("\n💤 Triggering Sleep Phase (Consolidation)...")
        sleep_result = client.trigger_sleep()
        print(f"✅ Sleep completed: Consolidated {sleep_result['consolidated']} memories.")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("💡 Hint: Ensure Docker stack is up and API is responding on http://localhost:8001")

if __name__ == "__main__":
    main()
