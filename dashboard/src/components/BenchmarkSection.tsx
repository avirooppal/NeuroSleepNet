import { motion } from "framer-motion";
import { Check, X } from "lucide-react";

const benchmarks = [
  { test: "Short-term Fact Retrieval", baseline: false, augmented: true },
  { test: "Long-term Context (15+ turns)", baseline: false, augmented: false },
  { test: "Multi-Hop Entity Combining", baseline: false, augmented: true },
  { test: "Contradiction Handling", baseline: false, augmented: false },
  { test: "Irrelevant Memory Injection", baseline: true, augmented: true },
];

const StatusIcon = ({ pass }: { pass: boolean }) =>
  pass ? (
    <span className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-primary/20">
      <Check className="h-4 w-4 text-primary" />
    </span>
  ) : (
    <span className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-destructive/20">
      <X className="h-4 w-4 text-destructive" />
    </span>
  );

const BenchmarkSection = () => (
  <section id="benchmarks" className="py-24 md:py-32">
    <div className="container mx-auto px-6 max-w-5xl">
      <motion.div
        className="text-center mb-16"
        initial={{ opacity: 0, y: 30 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
      >
        <p className="text-xs uppercase tracking-[0.3em] text-primary mb-4">benchmarks</p>
        <h2 className="font-heading text-3xl md:text-5xl font-bold mb-4">
          Proven to boost small-model
          <br />
          <span className="text-gradient-orange">recall accuracy by 200%</span>
        </h2>
        <p className="text-muted-foreground max-w-2xl mx-auto text-sm md:text-base">
          Benchmarked raw Qwen-0.5B against the same model augmented with NeuroSleepNet
          across 5 hardcore retrieval dimensions. Baseline scored 1/5, augmented scored 3/5.
        </p>
      </motion.div>

      <motion.div
        className="glass-card overflow-hidden"
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ delay: 0.2 }}
      >
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border/50">
                <th className="text-left p-4 md:p-6 font-heading font-semibold text-muted-foreground">Test Dimension</th>
                <th className="p-4 md:p-6 font-heading font-semibold text-muted-foreground text-center">Vanilla Qwen-0.5B</th>
                <th className="p-4 md:p-6 font-heading font-semibold text-center">
                  <span className="text-gradient-orange">+ NeuroSleepNet</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {benchmarks.map((b, i) => (
                <tr key={i} className="border-b border-border/30 last:border-0">
                  <td className="p-4 md:p-6 text-foreground">{b.test}</td>
                  <td className="p-4 md:p-6 text-center"><StatusIcon pass={b.baseline} /></td>
                  <td className="p-4 md:p-6 text-center"><StatusIcon pass={b.augmented} /></td>
                </tr>
              ))}
              <tr className="bg-secondary/30">
                <td className="p-4 md:p-6 font-heading font-bold">Overall Accuracy</td>
                <td className="p-4 md:p-6 text-center font-heading font-bold text-destructive">1 / 5</td>
                <td className="p-4 md:p-6 text-center font-heading font-bold text-primary">3 / 5</td>
              </tr>
            </tbody>
          </table>
        </div>
      </motion.div>

      <motion.p
        className="text-xs text-muted-foreground text-center mt-6"
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
        transition={{ delay: 0.4 }}
      >
        * Retrieval overhead as low as ~1-5ms using the LRU edge cache. TinyLlama results: Baseline 2/5 → Augmented 3/5.
      </motion.p>
    </div>
  </section>
);

export default BenchmarkSection;
