import { motion } from "framer-motion";

const plans = [
  {
    name: "Free",
    price: "$0",
    period: "/mo",
    description: "Perfect for testing and personal projects.",
    features: ["Local SQLite Backend", "Up to 3 Users", "500 Writes / mo", "1K Reads / mo"],
    cta: "Start Free",
    glow: false,
  },
  {
    name: "Starter",
    price: "$9",
    period: "/mo",
    description: "For small teams building AI products.",
    features: ["Local SQLite Backend", "Up to 50 Users", "10K Writes / mo", "20K Reads / mo", "Basic Consolidation"],
    cta: "Upgrade to Starter",
    glow: true,
  },
  {
    name: "Growth",
    price: "$29",
    period: "/mo",
    description: "For scaling production agents.",
    features: ["PostgreSQL Backend", "Up to 500 Users", "100K Writes / mo", "200K Reads / mo", "Priority Consolidation"],
    cta: "Upgrade to Growth",
    glow: false,
  }
];

const PricingSection = () => (
  <section id="pricing" className="py-24 relative overflow-hidden">
    <div className="container mx-auto px-6 relative z-10">
      <div className="text-center max-w-2xl mx-auto mb-16">
        <h2 className="text-3xl md:text-5xl font-heading font-bold mb-4">
          Simple <span className="text-gradient-orange">Pricing</span>
        </h2>
        <p className="text-muted-foreground">
          Start with our generous free tier and upgrade as your agent user base scales.
        </p>
      </div>
      
      <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
        {plans.map((plan, i) => (
          <motion.div
            key={plan.name}
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.2 }}
            className={`glass-card p-8 flex flex-col relative ${plan.glow ? 'border border-primary/50 shadow-[0_0_15px_rgba(255,107,0,0.2)]' : ''}`}
          >
            {plan.glow && (
              <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-primary text-black text-[10px] font-bold px-3 py-1 rounded-full uppercase tracking-wider">
                Most Popular
              </span>
            )}
            <h3 className="text-xl font-heading font-semibold mb-2">{plan.name}</h3>
            <p className="text-sm text-muted-foreground mb-6 h-10">{plan.description}</p>
            <div className="mb-6">
              <span className="text-4xl font-bold">{plan.price}</span>
              <span className="text-muted-foreground">{plan.period}</span>
            </div>
            <ul className="mb-8 flex-1 space-y-3">
              {plan.features.map(f => (
                <li key={f} className="flex items-center text-sm text-foreground/80">
                  <span className="text-primary mr-2">✓</span> {f}
                </li>
              ))}
            </ul>
            <button className={`w-full py-2 rounded-md font-medium transition-all ${plan.glow ? 'bg-primary text-black hover:bg-primary/90' : 'bg-white/5 hover:bg-white/10 border border-white/10'}`}>
              {plan.cta}
            </button>
          </motion.div>
        ))}
      </div>
    </div>
  </section>
);

export default PricingSection;
