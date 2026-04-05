import { Brain, LayoutDashboard, Settings, LogOut, ShieldCheck } from "lucide-react";
import { Link, useLocation } from "react-router-dom";
import React, { useEffect, useState } from "react";
import { jwtDecode } from "jwt-decode";

const DashboardLayout = ({ children }: { children: React.ReactNode }) => {
  const location = useLocation();
  const [isAdmin, setIsAdmin] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("auth_token");
    if (token) {
      try {
        const decoded: any = jwtDecode(token);
        setIsAdmin(decoded.role === 'admin');
      } catch (e) {
        console.error("Invalid token");
      }
    }
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("auth_token");
    window.location.href = "/";
  };

  return (
    <div className="min-h-screen bg-background flex flex-col md:flex-row">
      {/* Sidebar */}
      <aside className="w-full md:w-64 border-r border-white/10 bg-black/20 p-6 flex flex-col relative z-20">
        <div className="flex items-center gap-2 mb-12">
          <Brain className="h-6 w-6 text-primary" />
          <Link to="/" className="font-heading text-lg font-bold tracking-wide">NeuroSleepNet</Link>
        </div>

        <nav className="flex-1 space-y-2">
          <Link 
            to="/dashboard" 
            className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${location.pathname === '/dashboard' ? 'bg-primary/10 text-primary' : 'text-muted-foreground hover:bg-white/5 hover:text-foreground'}`}
          >
            <LayoutDashboard className="h-5 w-5" />
            User Metrics
          </Link>
          
          {isAdmin && (
            <Link 
              to="/super-admin" 
              className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${location.pathname === '/super-admin' ? 'bg-primary/10 text-primary border border-primary/20' : 'text-muted-foreground hover:bg-white/5 hover:text-foreground'}`}
            >
              <ShieldCheck className="h-5 w-5" />
              Creator Admin
            </Link>
          )}
        </nav>

        <div className="mt-8 pt-8 border-t border-white/10">
          <button onClick={handleLogout} className="flex items-center gap-3 px-4 py-2 w-full text-muted-foreground hover:text-red-400 transition-colors">
            <LogOut className="h-5 w-5" />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 overflow-y-auto relative z-10 p-6 md:p-12">
        {children}
      </main>
    </div>
  );
};

export default DashboardLayout;
