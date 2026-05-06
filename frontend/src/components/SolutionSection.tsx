import { motion } from "framer-motion";
import { Search, Clock, Zap, Moon, Bell } from "lucide-react";

const features = [
  {
    icon: Search,
    title: "Adaptive Graph Retrieval",
    desc: "Fuses Stage-2 Reranking with 2-hop Graph Expansion to surface related facts even with low direct similarity.",
    detail: "Retrieval automatically traverses semantic links created during synthesis to build a more context-aware prompt.",
  },
  {
    icon: Clock,
    title: "Diminishing Returns Scoring",
    desc: "Built-in chronological weighting with saturation-aware scoring. Prevents 'burst' noise from saturating recall.",
    detail: "Non-linear boost formula ensures recent memories outrank stale ones without drowning out established semantic facts.",
  },
  {
    icon: Zap,
    title: "ANN Matrix Cache (O1)",
    desc: "New in-memory embedding matrix enables sub-5ms retrievals with O(1) scaling at any scale.",
    detail: "Eliminates database search overhead by keeping an atomic, copy-on-write matrix ready for instant matmul search.",
  },
  {
    icon: Moon,
    title: "Synthetic Sleep Engine",
    desc: "Periodically clusters episodic fragments into stable, multi-fact Semantic nodes during idle periods.",
    detail: "Uses greedy centroid clustering to compress noisy chat logs into high-fidelity knowledge graphs.",
  },
  {
    icon: Bell,
    title: "LRU Re-embedding Cache",
    desc: "16,000x speedup for repeated content (boilerplate/agent loops) via MD5-keyed re-embedding caching.",
    detail: "Critical for high-frequency remember() calls in tight agent loops where redundant model calls would block execution.",
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
          Five pillars of persistent memory
        </h2>
        <p className="text-muted-foreground mt-4 max-w-2xl mx-auto text-sm md:text-base">
          NeuroSleepNet augments any local model with a lightweight sidecar that handles encoding,
          retrieval, consolidation, and event delivery—all without external services.
        </p>
      </motion.div>

      <div className="grid md:grid-cols-2 gap-5 max-w-5xl mx-auto">
        {features.map((f, i) => (
          <motion.div
            key={f.title}
            className={`glass-card p-7 group hover:border-primary/30 transition-all duration-500 ${
              i === 4 ? "md:col-span-2" : ""
            }`}
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
