import { motion } from "framer-motion";

const plans = [
  {
    name: "Free",
    price: "$0",
    period: "/mo",
    description: "Generous free tier. No credit card. No expiry.",
    features: [
      "10,000 memories / project",
      "1 project",
      "Offline SQLite fallback",
      "nsn-bench access",
      "Community support",
    ],
    cta: "Start Free",
    glow: false,
    tag: null,
  },
  {
    name: "Pro",
    price: "$29",
    period: "/mo",
    description: "For teams shipping production AI products.",
    features: [
      "500,000 memories",
      "Unlimited projects",
      "Webhooks (memory.stored, sleep.completed)",
      "Memory Diff API",
      "Dashboard analytics",
      "Priority support",
    ],
    cta: "Upgrade to Pro",
    glow: true,
    tag: "Most Popular",
  },
  {
    name: "Enterprise",
    price: "Custom",
    period: "",
    description: "Unlimited scale. SLA. On-prem deployment.",
    features: [
      "Unlimited memories",
      "Self-hosted always free",
      "SAML SSO + audit logs",
      "Custom SLA",
      "Dedicated support channel",
    ],
    cta: "Contact Us",
    glow: false,
    tag: null,
  },
];

const PricingSection = () => (
  <section id="pricing" className="py-24 relative overflow-hidden">
    <div className="container mx-auto px-6 relative z-10">
      <div className="text-center max-w-2xl mx-auto mb-16">
        <p className="text-xs uppercase tracking-[0.3em] text-primary mb-4">pricing</p>
        <h2 className="text-3xl md:text-5xl font-heading font-bold mb-4">
          Simple <span className="text-gradient-orange">Pricing</span>
        </h2>
        <p className="text-muted-foreground">
          10,000 memories free forever. No credit card required.
          Self-hosted is always free.
        </p>
      </div>

      <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
        {plans.map((plan, i) => (
          <motion.div
            key={plan.name}
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.15 }}
            className={`glass-card p-8 flex flex-col relative ${
              plan.glow
                ? "border border-primary/50 shadow-[0_0_20px_rgba(255,107,0,0.2)]"
                : ""
            }`}
          >
            {plan.tag && (
              <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-primary text-black text-[10px] font-bold px-3 py-1 rounded-full uppercase tracking-wider">
                {plan.tag}
              </span>
            )}

            <h3 className="text-xl font-heading font-semibold mb-2">{plan.name}</h3>
            <p className="text-sm text-muted-foreground mb-6 min-h-[40px]">{plan.description}</p>

            <div className="mb-6">
              <span className="text-4xl font-bold">{plan.price}</span>
              {plan.period && (
                <span className="text-muted-foreground">{plan.period}</span>
              )}
            </div>

            <ul className="mb-8 flex-1 space-y-3">
              {plan.features.map((f) => (
                <li key={f} className="flex items-start text-sm text-foreground/80">
                  <span className="text-primary mr-2 mt-0.5 shrink-0">✓</span>
                  {f}
                </li>
              ))}
            </ul>

            <button
              className={`w-full py-2.5 rounded-md font-medium transition-all ${
                plan.glow
                  ? "bg-primary text-black hover:bg-primary/90"
                  : "bg-white/5 hover:bg-white/10 border border-white/10"
              }`}
            >
              {plan.cta}
            </button>
          </motion.div>
        ))}
      </div>

      <p className="text-center text-xs text-muted-foreground mt-8">
        Self-hosted is <span className="text-primary font-medium">always free</span>. Deploy with{" "}
        <code className="bg-white/5 px-1.5 py-0.5 rounded">docker compose up</code> and connect your own
        infrastructure.
      </p>
    </div>
  </section>
);

export default PricingSection;
