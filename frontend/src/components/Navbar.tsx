import { Brain } from "lucide-react";
import { Link } from "react-router-dom";

const Navbar = () => {
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-6 py-4 md:px-12 backdrop-blur-md bg-background/50">
      <div className="flex items-center gap-2">
        <Brain className="h-5 w-5 text-primary" />
        <Link to="/" className="font-heading text-sm font-semibold tracking-wide text-foreground">NeuroSleepNet</Link>
      </div>
      
      {/* Public Landing Links */}
      <div className="hidden md:flex glass-nav px-6 py-2 gap-6 text-sm text-muted-foreground">
        <a href="/#problem" className="hover:text-foreground transition-colors">problem</a>
        <a href="/#solution" className="hover:text-foreground transition-colors">solution</a>
        <a href="/#benchmarks" className="hover:text-foreground transition-colors">benchmarks</a>
      </div>
      
      <div className="flex gap-4 items-center">
        <a href="https://github.com/avirooppal/NeuroSleepNet" target="_blank" rel="noopener noreferrer" className="text-xs text-muted-foreground hover:text-foreground transition-colors">
          GitHub
        </a>
        <a href="https://pypi.org/project/neurosleepnet/" target="_blank" rel="noopener noreferrer" className="btn-primary-glow text-sm flex items-center gap-2">
          View on PyPI
        </a>
      </div>
    </nav>
  );
};
export default Navbar;
