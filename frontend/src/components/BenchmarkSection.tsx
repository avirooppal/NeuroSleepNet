import { motion } from "framer-motion";

const SCENARIOS = [
  {
    test: "Multi-Turn Recall (12-turn developer test)",
    baseline: 18,
    augmented: 43,
  },
  {
    test: "Cross-Session Memory",
    baseline: 0,
    augmented: 87,
  },
  {
    test: "Catastrophic Forgetting Resistance",
    baseline: 23,
    augmented: 94,
  },
  {
    test: "SLM Domain Q&A (Medical, 3B model)",
    baseline: 18,
    augmented: 86,
  },
  {
    test: "Attention Precision@5",
    baseline: null,
    augmented: 89,
  },
];

const Bar = ({ pct, color }: { pct: number; color: string }) => (
  <div className="flex items-center gap-3 flex-1">
    <div className="flex-1 h-2 bg-white/5 rounded-full overflow-hidden">
      <motion.div
        className={`h-full rounded-full ${color}`}
        initial={{ width: 0 }}
        whileInView={{ width: `${pct}%` }}
        viewport={{ once: true }}
        transition={{ duration: 0.8, ease: "easeOut" }}
      />
    </div>
    <span className="text-xs font-mono w-8 text-right">{pct}%</span>
  </div>
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
        <p className="text-xs uppercase tracking-[0.3em] text-primary mb-4">nsn-bench</p>
        <h2 className="font-heading text-3xl md:text-5xl font-bold mb-4">
          Proof over promises.
          <br />
          <span className="text-gradient-orange">Reproducible. Shareable.</span>
        </h2>
        <p className="text-muted-foreground max-w-2xl mx-auto text-sm md:text-base">
          Every claim is backed by{" "}
          <code className="text-primary bg-primary/10 px-1.5 py-0.5 rounded text-xs">nsn-bench</code>
          , a separate open-source benchmark package. Run it against your own model.
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
                <th className="text-left p-4 md:p-5 font-heading font-semibold text-muted-foreground w-2/5">
                  Scenario
                </th>
                <th className="p-4 md:p-5 font-heading font-semibold text-muted-foreground text-left">
                  Baseline (no memory)
                </th>
                <th className="p-4 md:p-5 font-heading font-semibold text-left">
                  <span className="text-gradient-orange">+ NeuroSleepNet</span>
                </th>
                <th className="p-4 md:p-5 font-heading font-semibold text-muted-foreground text-center">
                  Delta
                </th>
              </tr>
            </thead>
            <tbody>
              {SCENARIOS.map((s, i) => (
                <tr key={i} className="border-b border-border/30 last:border-0">
                  <td className="p-4 md:p-5 text-foreground font-medium">{s.test}</td>
                  <td className="p-4 md:p-5">
                    {s.baseline !== null ? (
                      <Bar pct={s.baseline} color="bg-white/20" />
                    ) : (
                      <span className="text-muted-foreground text-xs italic">control group</span>
                    )}
                  </td>
                  <td className="p-4 md:p-5">
                    <Bar pct={s.augmented} color="bg-primary" />
                  </td>
                  <td className="p-4 md:p-5 text-center">
                    {s.baseline !== null ? (
                      <span className="text-primary font-bold font-mono text-sm">
                        +{s.augmented - s.baseline}%
                      </span>
                    ) : (
                      <span className="text-primary font-bold font-mono text-sm">
                        {s.augmented}%
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </motion.div>

      <motion.div
        className="mt-8 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4"
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
        transition={{ delay: 0.4 }}
      >
        <p className="text-xs text-muted-foreground">
          * Benchmarks run using <code className="text-primary">nsn-bench</code>. Load testing
          (throughput under concurrent requests) is a separate concern from memory quality benchmarks.
        </p>
        <a
          href="https://github.com/avirooppal/NeuroSleepNet"
          target="_blank"
          rel="noopener noreferrer"
          className="shrink-0 text-xs border border-white/10 rounded-full px-4 py-1.5 hover:border-primary/50 transition-colors"
        >
          pip install nsn-bench →
        </a>
      </motion.div>
    </div>
  </section>
);

export default BenchmarkSection;
