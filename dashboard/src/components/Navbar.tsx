import { Brain } from "lucide-react";

const COLAB_URL = "https://colab.research.google.com/github/avirooppal/NeuroSleepNet/blob/main/notebooks/NeuroSleepNet_Demo.ipynb";

const Navbar = () => (
  <nav className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-6 py-4 md:px-12">
    <div className="flex items-center gap-2">
      <Brain className="h-5 w-5 text-primary" />
      <span className="font-heading text-sm font-semibold tracking-wide text-foreground">NeuroSleepNet</span>
    </div>
    <div className="hidden md:flex glass-nav px-6 py-2 gap-6 text-sm text-muted-foreground">
      <a href="#problem" className="hover:text-foreground transition-colors">problem</a>
      <a href="#solution" className="hover:text-foreground transition-colors">solution</a>
      <a href="#benchmarks" className="hover:text-foreground transition-colors">benchmarks</a>
      <a href="#use-cases" className="hover:text-foreground transition-colors">use cases</a>
    </div>
    <a href="https://github.com/avirooppal/NeuroSleepNet" target="_blank" rel="noopener noreferrer" className="btn-outline-glow text-sm">
      get started
    </a>
  </nav>
);

export default Navbar;
