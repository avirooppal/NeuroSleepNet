import { Brain, LogOut, LayoutDashboard } from "lucide-react";
import { Link } from "react-router-dom";
import { useEffect, useState } from "react";

const Navbar = () => {
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const urlToken = urlParams.get("token");
    if (urlToken) {
      localStorage.setItem("auth_token", urlToken);
      window.history.replaceState({}, document.title, window.location.pathname);
    }
    setToken(localStorage.getItem("auth_token"));
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("auth_token");
    setToken(null);
    window.location.href = "/";
  };

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
        <a href="/#pricing" className="hover:text-foreground transition-colors">pricing</a>
      </div>
      
      <div className="flex gap-4 items-center">
        {!token ? (
          <a href="http://localhost:8080/api/v1/auth/login" className="btn-outline-glow text-sm">
            login via github
          </a>
        ) : (
          <>
            <Link to="/dashboard" className="text-sm font-medium text-gradient-orange flex items-center gap-1 hover:opacity-80 transition-opacity">
              <LayoutDashboard className="h-4 w-4" /> Go to Dashboard
            </Link>
            <button onClick={handleLogout} className="btn-outline-glow text-sm flex items-center gap-2 ml-4">
              <LogOut className="h-4 w-4" /> logout
            </button>
          </>
        )}
      </div>
    </nav>
  );
};
export default Navbar;
