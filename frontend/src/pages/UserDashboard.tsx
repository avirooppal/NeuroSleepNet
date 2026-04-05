import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { jwtDecode } from "jwt-decode";
import { Shield, Zap } from "lucide-react";

const UserDashboard = () => {
  const [metrics, setMetrics] = useState({ total_nodes: 0, active_nodes: 0, total_tasks: 0 });
  const [loading, setLoading] = useState(true);
  const [userTier, setUserTier] = useState("Free");

  // In a real app, this user_id is injected by Auth Context (JWT decoder)
  const MOCK_USER_ID = "test_user_1"; 
  
  useEffect(() => {
    // 1. Check URL parameters from OAuth Redirect
    const urlParams = new URLSearchParams(window.location.search);
    const urlToken = urlParams.get("token");
    if (urlToken) {
      localStorage.setItem("auth_token", urlToken);
      window.history.replaceState({}, document.title, window.location.pathname);
    }

    // 2. Lock mechanism
    const token = localStorage.getItem("auth_token");
    if (!token) {
      window.location.href = "http://localhost:8000/api/auth/login";
      return;
    }

    try {
      const decoded: any = jwtDecode(token);
      setUserTier(decoded.tier || "Free");
    } catch (e) {
      console.error("Failed to decode token");
    }

    const fetchMetrics = async () => {
      try {
        const res = await fetch(`http://localhost:8000/api/v2/metrics`, {
          headers: {
            "Authorization": `Bearer ${token}`
          }
        });
        if(res.ok) {
          const data = await res.json();
          setMetrics(data);
        }
      } catch (err) {
        console.error("Failed to fetch metrics", err);
      } finally {
        setLoading(false);
      }
    };
    fetchMetrics();
    
    // Poll every 5s for realtime effect
    const interval = setInterval(fetchMetrics, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="w-full max-w-5xl">
      <div className="flex justify-between items-start mb-2">
        <div>
          <h1 className="text-3xl font-heading font-bold">Developer Dashboard</h1>
          <p className="text-muted-foreground">Monitor your deployed memory agents.</p>
        </div>
        <div className={`px-4 py-2 rounded-full border flex items-center gap-2 ${userTier === 'Growth' ? 'bg-primary/10 border-primary/50 text-primary' : 'bg-white/5 border-white/10 text-muted-foreground'}`}>
          {userTier === 'Growth' ? <Zap className="h-4 w-4" /> : <Shield className="h-4 w-4" />}
          <span className="text-xs font-bold uppercase tracking-wider">{userTier} Plan</span>
        </div>
      </div>
      <div className="h-12" /> {/* Spacer */}
        
        <div className="grid md:grid-cols-3 gap-6">
          <motion.div initial={{opacity:0, y:20}} animate={{opacity:1, y:0}} className="glass-card p-6">
            <h3 className="text-sm uppercase tracking-wider text-muted-foreground mb-2">Active Memory Nodes</h3>
            <span className="text-5xl font-bold text-gradient-orange stat-glow block">
              {loading ? "..." : metrics.active_nodes}
            </span>
          </motion.div>
          
          <motion.div initial={{opacity:0, y:20}} animate={{opacity:1, y:0}} transition={{delay: 0.1}} className="glass-card p-6">
            <h3 className="text-sm uppercase tracking-wider text-muted-foreground mb-2">Unique Task Threads</h3>
            <span className="text-5xl font-bold text-gradient-orange stat-glow block">
               {loading ? "..." : metrics.total_tasks}
            </span>
          </motion.div>

          <motion.div initial={{opacity:0, y:20}} animate={{opacity:1, y:0}} transition={{delay: 0.2}} className="glass-card p-6">
            <h3 className="text-sm uppercase tracking-wider text-muted-foreground mb-2">Pruned Nodes</h3>
            <span className="text-5xl font-bold text-white/80 block">
               {loading ? "..." : (metrics.total_nodes - metrics.active_nodes)}
            </span>
          </motion.div>
        </div>
    </div>
  );
};

export default UserDashboard;
