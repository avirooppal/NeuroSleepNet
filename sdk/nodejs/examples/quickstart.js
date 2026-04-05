const { NeuroSleepClient } = require("../dist/index");

async function main() {
  const client = new NeuroSleepClient(
    "nsn_live_your_key_here",
    "http://localhost:8001/api/v1"
  );

  console.log("🚀 Initializing NeuroSleepNet Example (Node.js)...");

  try {
    // 1. Create a task
    console.log("\n📝 Creating context 'Agent-User Learning'...");
    const task = await client.createTask("Agent-User Learning");
    const taskId = task.id;
    console.log(`✅ Task created with ID: ${taskId}`);

    // 2. Add memories
    console.log("\n🧠 Adding memories...");
    await client.addMemory(
      "The user's favorite programming language is Python and they dislike Java.",
      taskId,
      { source: "conversation_01", type: "preference" }
    );
    await client.addMemory(
      "The user is currently working on a production-ready AI platform called NeuroSleepNet.",
      taskId,
      { source: "conversation_01", type: "project" }
    );
    console.log("✅ Memories added.");

    // 3. Search with Attention scorer
    console.log("\n🔍 Searching for user preferences...");
    const results = await client.search(
      "What are the user's coding interests?",
      taskId,
      2
    );

    results.memories.forEach((res, i) => {
      console.log(`\nResult ${i + 1}:`);
      console.log(` - Content: ${res.content}`);
      console.log(` - Attention Score: ${res.attention_score.toFixed(2)}`);
      console.log(` - Explanation: ${res.why_retrieved}`);
    });

    // 4. Check dashboard stats
    console.log("\n📊 Fetching dashboard stats...");
    const stats = await client.getStats();
    console.log(` - Total Memories: ${stats.total_memories}`);
    console.log(` - Monthly Ops: ${stats.monthly_ops}`);
    console.log(` - Memory Health: ${stats.memory_health_score}%`);

    // 5. Nightly Sleep Phase (forced trigger)
    console.log("\n💤 Triggering Sleep Phase (Consolidation)...");
    const sleepResult = await client.triggerSleep();
    console.log(`✅ Sleep completed: Consolidated ${sleepResult.consolidated} memories.`);

  } catch (error) {
    console.log("\n❌ Error:", error.message);
    console.log("💡 Hint: Ensure Docker stack is up and API is responding on http://localhost:8001");
  }
}

main();
