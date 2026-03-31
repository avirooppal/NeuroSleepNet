import { motion } from "framer-motion";
import { Bot, Gamepad2, Headphones } from "lucide-react";
import blobSmall from "@/assets/blob-small.jpg";

const cases = [
  {
    icon: Bot,
    title: "Fully Local Personal Assistants",
    desc: "Build a JARVIS that runs securely on your laptop and remembers your family, your schedule, and your tech stack.",
  },
  {
    icon: Gamepad2,
    title: "Endless AI RPGs & Gaming",
    desc: "Create NPCs that actually remember their previous interactions with the player without blowing up token costs.",
  },
  {
    icon: Headphones,
    title: "Autonomous Customer Support",
    desc: "Sidecar agents that remember a user's entire ticketing history across multiple disconnected sessions.",
  },
];

const UseCasesSection = () => (
  <section id="use-cases" className="py-24 md:py-32">
    <div className="container mx-auto px-6">
      <motion.div
        className="text-center mb-16"
        initial={{ opacity: 0, y: 30 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
      >
        <h2 className="font-heading text-3xl md:text-5xl font-bold">Our Benefits</h2>
      </motion.div>

      <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto">
        {cases.map((c, i) =>
          i === 1 ? (
            <motion.div
              key={c.title}
              className="glass-card p-8 flex flex-col items-center justify-center"
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.1 }}
            >
              <img src={blobSmall} alt="" className="w-40 h-40 object-contain mb-6" loading="lazy" width={512} height={512} />
              <h3 className="font-heading text-lg font-semibold mb-2">{c.title}</h3>
              <p className="text-sm text-muted-foreground text-center leading-relaxed">{c.desc}</p>
            </motion.div>
          ) : (
            <motion.div
              key={c.title}
              className="glass-card p-8"
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
            >
              <c.icon className="h-8 w-8 text-primary mb-4" />
              <h3 className="font-heading text-lg font-semibold mb-3">{c.title}</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">{c.desc}</p>
            </motion.div>
          )
        )}
      </div>
    </div>
  </section>
);

export default UseCasesSection;
