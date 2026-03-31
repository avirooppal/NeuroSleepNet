import { motion } from "framer-motion";
import { Search, Clock, Zap, Moon } from "lucide-react";

const features = [
  {
    icon: Search,
    title: "Hybrid Search Retrieval",
    desc: "Fuses Latent Semantic Similarity with Exact Keyword matching (BM25)—bridging the gap where standard cosine similarity fails.",
    detail: "Combines dense vector embeddings with sparse token matching for robust recall across query types.",
  },
  {
    icon: Clock,
    title: "Time-Decay Recency Weighting",
    desc: "Built-in chronological weighting guarantees the newest fact outranks the old one. No more contradictions.",
    detail: "Exponential decay function ensures recent memories surface first while older ones gracefully fade.",
  },
  {
    icon: Zap,
    title: "Edge-Optimized Speeds",
    desc: "LRU Edge Cache enables sub-100ms retrievals. No bloated databases required.",
    detail: "In-process caching means zero network hops. Benchmarked at <5ms overhead on consumer hardware.",
  },
  {
    icon: Moon,
    title: "The 'Sleep' Consolidator",
    desc: "Memories are periodically aggregated into a clean Knowledge Graph during idle periods.",
    detail: "Automatic deduplication and noise pruning keep the memory store lean and accurate over time.",
  },
];

const SolutionSection = () => (
  <section id="solution" className="py-16 md:py-24">
    <div className="container mx-auto px-6">
      <motion.div
        className="text-center mb-12"
        initial={{ opacity: 0, y: 30 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
      >
        <p className="text-xs uppercase tracking-[0.3em] text-primary mb-4">how it works</p>
        <h2 className="font-heading text-3xl md:text-5xl font-bold">
          Four pillars of persistent memory
        </h2>
        <p className="text-muted-foreground mt-4 max-w-2xl mx-auto text-sm md:text-base">
          NeuroSleepNet augments any local model with a lightweight sidecar that handles encoding, retrieval, and consolidation—all without external services.
        </p>
      </motion.div>

      <div className="grid md:grid-cols-2 gap-5 max-w-5xl mx-auto">
        {features.map((f, i) => (
          <motion.div
            key={f.title}
            className="glass-card p-7 group hover:border-primary/30 transition-all duration-500"
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.1 }}
          >
            <div className="flex items-start gap-4">
              <div className="p-2 rounded-lg bg-primary/10 shrink-0">
                <f.icon className="h-6 w-6 text-primary group-hover:scale-110 transition-transform" />
              </div>
              <div>
                <h3 className="font-heading text-base font-semibold mb-2">{f.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed mb-2">{f.desc}</p>
                <p className="text-xs text-muted-foreground/70 leading-relaxed">{f.detail}</p>
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  </section>
);

export default SolutionSection;
