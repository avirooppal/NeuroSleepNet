import { motion } from "framer-motion";
import heroBlob from "@/assets/hero-blob.jpg";

const COLAB_URL = "https://colab.research.google.com/github/avirooppal/NeuroSleepNet/blob/main/notebooks/NeuroSleepNet_Demo.ipynb";

const stats = [
  { value: "+400%", label: "recall accuracy boost" },
  { value: "3/5", label: "augmented accuracy" },
  { value: "<5ms", label: "retrieval overhead" },
  { value: "0", label: "external dependencies" },
  { value: "2", label: "lines to integrate" },
];

const HeroSection = () => (
  <section className="relative min-h-screen flex items-center overflow-hidden pt-20">
    {/* Blob visual */}
    <motion.div
      className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] md:w-[650px] md:h-[650px] opacity-50"
      animate={{ y: [0, -20, 0] }}
      transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }}
    >
      <img src={heroBlob} alt="" className="w-full h-full object-contain" width={1024} height={1024} />
    </motion.div>

    {/* Main content */}
    <div className="relative z-10 container mx-auto px-6">
      <div className="grid lg:grid-cols-[1fr_auto] gap-12 items-center">
        {/* Left: headline + CTA */}
        <div>
          <motion.p
            className="text-xs uppercase tracking-[0.3em] text-primary mb-4"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
          >
            zero-ops memory layer for local LLMs
          </motion.p>

          <motion.h1
            className="font-heading text-5xl md:text-7xl lg:text-8xl font-bold leading-[0.9] tracking-tight"
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
          >
            give local
            <br />
            <span className="text-gradient-orange">LLMs</span> infinite
            <br />
            memory
          </motion.h1>

          <motion.p
            className="mt-6 max-w-lg text-sm md:text-base text-muted-foreground leading-relaxed"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
          >
            A lightweight, zero-ops memory layer for small, open-source models.
            Run offline, remember everything, and eradicate context-window amnesia.
            Built with hybrid BM25 + semantic search, time-decay weighting, and an LRU edge cache.
          </motion.p>

          <motion.div
            className="mt-8 flex flex-wrap gap-4"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.7 }}
          >
            <a href="https://github.com/avirooppal/NeuroSleepNet" target="_blank" rel="noopener noreferrer" className="btn-outline-glow text-sm">
              view on GitHub
            </a>
            <a href={COLAB_URL} target="_blank" rel="noopener noreferrer" className="btn-primary-glow text-sm">
              try demo
            </a>
          </motion.div>

          {/* Supported models badge row */}
          <motion.div
            className="mt-6 flex flex-wrap gap-3"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.9 }}
          >
            {["Qwen 0.5B", "TinyLlama 1.1B", "Phi-2", "Mistral 7B"].map((m) => (
              <span key={m} className="text-[10px] uppercase tracking-wider text-muted-foreground border border-white/10 rounded-full px-3 py-1">
                {m}
              </span>
            ))}
          </motion.div>
        </div>

        {/* Right: stats column */}
        <motion.div
          className="flex flex-row lg:flex-col gap-4 lg:gap-3 flex-wrap justify-center"
          initial={{ opacity: 0, x: 30 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.8, duration: 0.6 }}
        >
          {stats.map((s, i) => (
            <motion.div
              key={s.label}
              className="glass-card px-5 py-4 text-center min-w-[120px]"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.8 + i * 0.1 }}
            >
              <span className="text-2xl md:text-3xl font-heading font-bold text-gradient-orange stat-glow block">{s.value}</span>
              <p className="text-[10px] text-muted-foreground mt-1 uppercase tracking-wider">{s.label}</p>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </div>
  </section>
);

export default HeroSection;
