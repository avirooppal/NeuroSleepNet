import { motion } from "framer-motion";

const codeSnippet = `from neurosleepnet import wrap
from my_local_llm import LocalAgent

# 1. Load your standard stateless agent
base_agent = LocalAgent(model_id="Qwen/Qwen2.5-0.5B")

# 2. Wrap it in the NeuroSleepNet sidecar
memory_agent = wrap(base_agent, mode="sidecar")

# 3. It now remembers everything flawlessly.
memory_agent.predict("What did I say my favorite color was?")`;

const CodeSection = () => (
  <section className="py-24 md:py-32">
    <div className="container mx-auto px-6 max-w-4xl">
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
      >
        <p className="text-xs uppercase tracking-[0.3em] text-primary mb-4">developer ux</p>
        <h2 className="font-heading text-3xl md:text-5xl font-bold mb-10">
          Two lines of code<br />
          <span className="text-muted-foreground">to upgrade your Agent.</span>
        </h2>
      </motion.div>

      <motion.div
        className="glass-card p-6 md:p-8 overflow-x-auto glow-orange"
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ delay: 0.2 }}
      >
        <pre className="text-sm md:text-base font-mono leading-relaxed">
          <code>
            {codeSnippet.split('\n').map((line, i) => (
              <span key={i} className="block">
                {line.startsWith('#') ? (
                  <span className="text-muted-foreground">{line}</span>
                ) : line.includes('from') || line.includes('import') ? (
                  <span>
                    <span className="text-primary">{line.split(' ')[0]}</span>
                    <span className="text-foreground">{' ' + line.split(' ').slice(1).join(' ')}</span>
                  </span>
                ) : (
                  <span className="text-foreground">{line}</span>
                )}
              </span>
            ))}
          </code>
        </pre>
      </motion.div>
    </div>
  </section>
);

export default CodeSection;
