import { Brain } from "lucide-react";

const Footer = () => (
  <footer className="border-t border-border/30 py-12">
    <div className="container mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-6 text-sm text-muted-foreground">
      <div className="flex items-center gap-2">
        <Brain className="h-4 w-4 text-primary" />
        <span className="font-heading font-semibold text-foreground">NeuroSleepNet</span>
      </div>
      <div className="flex gap-8">
        <a href="#solution" className="hover:text-foreground transition-colors">Documentation</a>
        <a href="#benchmarks" className="hover:text-foreground transition-colors">Benchmarks</a>
        <a href="https://github.com/avirooppal/NeuroSleepNet" target="_blank" rel="noopener noreferrer" className="hover:text-foreground transition-colors">GitHub</a>
      </div>
      <p className="text-xs text-muted-foreground">© 2026 NeuroSleepNet</p>
    </div>
  </footer>
);

export default Footer;
