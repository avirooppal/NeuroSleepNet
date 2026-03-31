import { motion } from "framer-motion";
import { AlertTriangle, Brain, Timer, DollarSign } from "lucide-react";

const painPoints = [
  { icon: Brain, title: "Context Window Limits", desc: "Small models (0.5B–3B) only hold 2K–4K tokens. After ~15 turns your entire conversation history exceeds the window." },
  { icon: Timer, title: "Slow Full-History Injection", desc: "Concatenating every past message into the prompt balloons latency and makes inference unusable on edge hardware." },
  { icon: DollarSign, title: "Token Cost Explosion", desc: "Even with cloud APIs, re-sending full history every call multiplies cost linearly with conversation length." },
  { icon: AlertTriangle, title: "Fact Contradictions", desc: "Without temporal awareness, the model can't distinguish 'I drive a Honda' (old) from 'I now drive a Toyota' (new)." },
];

const ProblemSection = () => (
  <section id="problem" className="py-16 md:py-24">
    <div className="container mx-auto px-6">
      <motion.div
        className="max-w-4xl mb-12"
        initial={{ opacity: 0, y: 30 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.6 }}
      >
        <p className="text-xs uppercase tracking-[0.3em] text-primary mb-4">the amnesia bottleneck</p>
        <h2 className="font-heading text-3xl md:text-5xl font-bold leading-tight mb-6">
          Small models forget.
          <br />
          <span className="text-muted-foreground">That's the problem.</span>
        </h2>
        <p className="text-muted-foreground leading-relaxed text-base md:text-lg max-w-2xl">
          Running powerful models like Qwen or TinyLlama locally ensures utter privacy.
          But small models have small context windows. By the 15th conversational turn,
          they forget who you are, what car you drive, and what your preferences are.
        </p>
      </motion.div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {painPoints.map((p, i) => (
          <motion.div
            key={p.title}
            className="glass-card p-6 border-destructive/20"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.1 }}
          >
            <p.icon className="h-6 w-6 text-destructive mb-3" />
            <h3 className="font-heading text-sm font-semibold mb-2">{p.title}</h3>
            <p className="text-xs text-muted-foreground leading-relaxed">{p.desc}</p>
          </motion.div>
        ))}
      </div>
    </div>
  </section>
);

export default ProblemSection;
