import { motion } from "framer-motion";
import { Bell, Database, Layers, Zap } from "lucide-react";

// ─── Architecture constants ──────────────────────────────────────────────────

const QUEUES = [
  {
    name: "sleep",
    label: "worker-sleep",
    desc: "Nightly consolidation passes. Boosts high-utility memories, prunes stale ones.",
    color: "border-primary/40 bg-primary/5",
    accent: "text-primary",
    icon: Layers,
    concurrency: 2,
  },
  {
    name: "webhooks",
    label: "worker-webhooks",
    desc: "Delivers memory.stored, memory.archived, sleep.completed events. Enqueued after DB commit — never inside the handler.",
    color: "border-amber-500/40 bg-amber-500/5",
    accent: "text-amber-400",
    icon: Bell,
    concurrency: 3,
  },
  {
    name: "embed",
    label: "worker-embed",
    desc: "Async embedding generation via BAAI/bge-small. Keeps API response latency near zero.",
    color: "border-cyan-500/40 bg-cyan-500/5",
    accent: "text-cyan-400",
    icon: Zap,
    concurrency: 4,
  },
];

const FALLBACK_STEPS = [
  { label: "API healthy", detail: "Retrieve from backend → inject → log usage", ok: true },
  { label: "API slow (>500ms)", detail: "Use local SQLite cache → inject → queue retry", ok: true },
  { label: "API unreachable", detail: "Skip injection → agent runs as-is → log warning", ok: true },
  { label: "SDK crash", detail: "try/catch wraps ALL NSN code → original agent runs untouched", ok: true },
];

// ─── Component ───────────────────────────────────────────────────────────────

const ArchitectureSection = () => (
  <section id="architecture" className="py-24 md:py-32 border-t border-border/20">
    <div className="container mx-auto px-6 max-w-6xl">

      {/* Heading */}
      <motion.div
        className="text-center mb-16"
        initial={{ opacity: 0, y: 30 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
      >
        <p className="text-xs uppercase tracking-[0.3em] text-primary mb-4">architecture</p>
        <h2 className="font-heading text-3xl md:text-5xl font-bold">
          Built to never stall.
          <br />
          <span className="text-muted-foreground">Three queues. Zero starvation.</span>
        </h2>
        <p className="text-sm text-muted-foreground mt-4 max-w-2xl mx-auto">
          Sleep consolidation, webhook delivery, and embedding generation run on separate Celery
          worker containers — each with its own queue and concurrency budget so a slow sleep job
          never blocks a time-sensitive webhook.
        </p>
      </motion.div>

      {/* Three-queue diagram */}
      <div className="grid md:grid-cols-3 gap-5 mb-16">
        {QUEUES.map((q, i) => (
          <motion.div
            key={q.name}
            className={`glass-card p-6 border ${q.color}`}
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.12 }}
          >
            <div className="flex items-center gap-3 mb-4">
              <div className={`p-2 rounded-lg bg-white/5`}>
                <q.icon className={`h-5 w-5 ${q.accent}`} />
              </div>
              <div>
                <p className={`font-mono text-xs font-semibold ${q.accent}`}>-Q {q.name}</p>
                <p className="text-xs text-muted-foreground">{q.label}</p>
              </div>
            </div>
            <p className="text-sm text-foreground/80 leading-relaxed mb-4">{q.desc}</p>
            <div className="flex items-center justify-between text-xs text-muted-foreground border-t border-white/5 pt-3">
              <span>concurrency</span>
              <span className={`font-mono font-semibold ${q.accent}`}>{q.concurrency}</span>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Webhook delivery note */}
      <motion.div
        className="glass-card p-6 mb-16 border border-amber-500/20"
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
      >
        <div className="flex items-start gap-4">
          <Bell className="h-5 w-5 text-amber-400 shrink-0 mt-0.5" />
          <div>
            <h3 className="font-heading text-sm font-semibold mb-2">
              Webhook Delivery: After-Commit Pattern
            </h3>
            <p className="text-sm text-muted-foreground leading-relaxed">
              Webhook tasks are <strong className="text-foreground">enqueued after the database transaction commits</strong>,
              never inside the FastAPI handler. This guarantees a consumer processing a{" "}
              <code className="text-amber-400 bg-amber-400/10 px-1 rounded text-xs">memory.stored</code> event
              will always find the memory in the database — no race conditions. Failed deliveries retry
              with exponential back-off (3 attempts: 30s, 5m, 30m). Supported events:{" "}
              <code className="text-foreground bg-white/5 px-1 rounded text-xs">memory.stored</code>,{" "}
              <code className="text-foreground bg-white/5 px-1 rounded text-xs">memory.archived</code>,{" "}
              <code className="text-foreground bg-white/5 px-1 rounded text-xs">sleep.completed</code>,{" "}
              <code className="text-foreground bg-white/5 px-1 rounded text-xs">quota.warning</code>.
            </p>
          </div>
        </div>
      </motion.div>

      {/* SDK Fallback cascade */}
      <motion.div
        className="glass-card p-6 md:p-8"
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
      >
        <div className="flex items-center gap-3 mb-6">
          <Database className="h-5 w-5 text-primary" />
          <div>
            <h3 className="font-heading text-sm font-semibold">SDK Fallback Cascade</h3>
            <p className="text-xs text-muted-foreground">
              SDK tries the API directly first. SQLite is a fallback, not a mandatory pipeline.
            </p>
          </div>
        </div>

        <div className="space-y-3">
          {FALLBACK_STEPS.map((step, i) => (
            <motion.div
              key={i}
              className="flex items-start gap-4 p-3 rounded-lg bg-white/[0.02] border border-white/5"
              initial={{ opacity: 0, x: -10 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.08 }}
            >
              <div className="flex items-center justify-center w-6 h-6 rounded-full bg-primary/10 text-primary text-xs font-bold shrink-0 mt-0.5">
                {i + 1}
              </div>
              <div>
                <p className="text-sm font-medium text-foreground">{step.label}</p>
                <p className="text-xs text-muted-foreground mt-0.5">{step.detail}</p>
              </div>
            </motion.div>
          ))}
        </div>

        <div className="mt-6 pt-4 border-t border-white/5 flex items-start gap-3">
          <div className="w-2 h-2 rounded-full bg-primary shrink-0 mt-1.5" />
          <p className="text-xs text-muted-foreground leading-relaxed">
            All NSN logic is wrapped in try/except at the outermost level. A bug in the SDK can never
            propagate to the host agent. The agent always runs.
          </p>
        </div>
      </motion.div>

    </div>
  </section>
);

export default ArchitectureSection;
