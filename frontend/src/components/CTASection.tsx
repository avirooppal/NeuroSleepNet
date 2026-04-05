import { motion } from "framer-motion";

const COLAB_URL = "https://colab.research.google.com/github/avirooppal/NeuroSleepNet/blob/main/notebooks/NeuroSleepNet_Demo.ipynb";

const CTASection = () => (
  <section className="py-24 md:py-32 border-t border-border/30">
    <div className="container mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-8 max-w-5xl">
      <motion.div
        initial={{ opacity: 0, x: -20 }}
        whileInView={{ opacity: 1, x: 0 }}
        viewport={{ once: true }}
      >
        <p className="text-muted-foreground text-sm md:text-base max-w-md">
          protecting your data with outmost tech,
          <br />empowering you with memory everywhere
        </p>
      </motion.div>
      <motion.a
        href={COLAB_URL}
        target="_blank"
        rel="noopener noreferrer"
        className="btn-outline-glow text-sm"
        initial={{ opacity: 0, x: 20 }}
        whileInView={{ opacity: 1, x: 0 }}
        viewport={{ once: true }}
      >
        Try Demo
      </motion.a>
    </div>
  </section>
);

export default CTASection;
