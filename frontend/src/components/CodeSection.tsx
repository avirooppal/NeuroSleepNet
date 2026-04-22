import { motion } from "framer-motion";
import { useState } from "react";

const CLOUD_SNIPPET = `import neurosleepnet as nsn

# One-time setup — hosted or self-hosted
nsn.init(api_key="nsn_your_key_here")

# Drop-in wrap — works with LangChain, OpenAI, HuggingFace, Ollama
agent = nsn.wrap(your_agent)

# That's it. Your agent now has persistent memory.
response = agent("What did we work on last session?")

# Manually inject a high-priority fact
nsn.remember("User prefers Python over JavaScript", importance=0.9)

# Explicitly retrieve memories (debug / custom injection)
memories = nsn.recall(query="auth module fixes", top_k=5)

# Export and migrate full memory state
snapshot = nsn.snapshot()         # → dict
nsn.restore(snapshot)             # restore on any instance`;

const SELF_HOSTED_SNIPPET = `import neurosleepnet as nsn

# Point to your own backend — no external dependency
nsn.init(
    api_key="nsn_your_key_here",
    base_url="http://localhost:8080",   # self-hosted endpoint
    project="my-agent-v2",
    fallback_mode="silent",             # never crash the host agent
    offline_cache=True,                 # SQLite fallback if API unreachable
)

agent = nsn.wrap(your_agent)

# Diagnostics — prints latency, quota, cache hits to stdout
nsn.status()`;

const tabs = [
  { label: "Hosted", snippet: CLOUD_SNIPPET },
  { label: "Self-Hosted", snippet: SELF_HOSTED_SNIPPET },
];

const tokenize = (line: string) => {
  if (line.startsWith("#")) return <span className="text-muted-foreground/70 italic">{line}</span>;
  if (line.trim().startsWith("import") || line.trim().startsWith("from"))
    return <span className="text-cyan-400">{line}</span>;
  if (line.includes("nsn."))
    return (
      <span>
        {line.split(/(nsn\.\w+)/).map((part, i) =>
          part.startsWith("nsn.") ? (
            <span key={i} className="text-primary font-semibold">{part}</span>
          ) : (
            <span key={i} className="text-foreground">{part}</span>
          )
        )}
      </span>
    );
  return <span className="text-foreground">{line}</span>;
};

const CodeSection = () => {
  const [active, setActive] = useState(0);

  return (
    <section className="py-24 md:py-32" id="quickstart">
      <div className="container mx-auto px-6 max-w-4xl">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
        >
          <p className="text-xs uppercase tracking-[0.3em] text-primary mb-4">quickstart</p>
          <h2 className="font-heading text-3xl md:text-5xl font-bold mb-4">
            Three lines to integrate.
            <br />
            <span className="text-muted-foreground">Everything else is automatic.</span>
          </h2>
          <p className="text-sm text-muted-foreground mb-10 max-w-xl">
            One key, one wrap. Works with any agent. SDK falls back to local SQLite cache if the API
            is unreachable — the host agent never breaks.
          </p>
        </motion.div>

        {/* Tab switcher */}
        <motion.div
          className="flex gap-2 mb-4"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
        >
          {tabs.map((t, i) => (
            <button
              key={t.label}
              onClick={() => setActive(i)}
              className={`px-4 py-1.5 text-xs rounded-full font-medium transition-all border ${
                active === i
                  ? "bg-primary text-black border-primary"
                  : "bg-transparent text-muted-foreground border-white/10 hover:border-white/30"
              }`}
            >
              {t.label}
            </button>
          ))}
        </motion.div>

        <motion.div
          className="glass-card p-6 md:p-8 overflow-x-auto glow-orange"
          key={active}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25 }}
        >
          <pre className="text-sm md:text-base font-mono leading-relaxed">
            <code>
              {tabs[active].snippet.split("\n").map((line, i) => (
                <span key={i} className="block">
                  {tokenize(line)}
                </span>
              ))}
            </code>
          </pre>
        </motion.div>

        <motion.p
          className="text-xs text-muted-foreground mt-4"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
        >
          <span className="text-primary">nsn.recall()</span> for semantic retrieval ·{" "}
          <span className="text-primary">nsn.snapshot()</span> /{" "}
          <span className="text-primary">nsn.restore()</span> for migrations ·{" "}
          <span className="text-primary">nsn.status()</span> for diagnostics
        </motion.p>
      </div>
    </section>
  );
};

export default CodeSection;
