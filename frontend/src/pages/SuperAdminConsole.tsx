import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { jwtDecode } from "jwt-decode";

const SuperAdminConsole = () => {
  const [metrics, setMetrics] = useState({ total_nodes: 0, total_users: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const token = localStorage.getItem("auth_token");
    if (!token) {
      window.location.href = "http://localhost:8000/api/auth/login";
      return;
    }

    try {
      const decoded: any = jwtDecode(token);
      if (decoded.role !== 'admin') {
        window.location.href = "/dashboard";
        return;
      }
    } catch (e) {
      window.location.href = "/";
      return;
    }

    const fetchMetrics = async () => {
      try {
        const res = await fetch(`http://localhost:8000/api/v2/admin/metrics`, {
          headers: {
            "Authorization": `Bearer ${token}`
          }
        });
        if(res.ok) {
          const data = await res.json();
          setMetrics(data);
          setError("");
        } else {
          setError("Failed to authenticate Admin API.");
        }
      } catch (err) {
        setError("Failed to fetch admin metrics. Is the API running?");
      } finally {
        setLoading(false);
      }
    };
    fetchMetrics();
    
    // Poll every 5s
    const interval = setInterval(fetchMetrics, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="w-full max-w-5xl">
      <h1 className="text-3xl font-heading font-bold mb-2">Creator Console</h1>
      <p className="text-muted-foreground mb-12">Global observability for the NeuroSleepNet platform.</p>
        
        {error && <div className="p-4 bg-red-500/20 text-red-400 border border-red-500/50 rounded mb-8">{error}</div>}

        <div className="grid md:grid-cols-2 gap-6">
          <motion.div initial={{opacity:0, scale:0.95}} animate={{opacity:1, scale:1}} className="glass-card p-8 border border-primary/20">
            <h3 className="text-sm uppercase tracking-wider text-muted-foreground mb-4">Total Active Tenants</h3>
            <span className="text-7xl font-bold text-gradient-orange stat-glow block">
              {loading ? "..." : metrics.total_users}
            </span>
          </motion.div>
          
          <motion.div initial={{opacity:0, scale:0.95}} animate={{opacity:1, scale:1}} transition={{delay: 0.1}} className="glass-card p-8 border border-primary/20">
            <h3 className="text-sm uppercase tracking-wider text-muted-foreground mb-4">Global Graph Nodes</h3>
            <span className="text-7xl font-bold text-gradient-orange stat-glow block">
               {loading ? "..." : metrics.total_nodes}
            </span>
          </motion.div>
        </div>
    </div>
  );
};

export default SuperAdminConsole;
