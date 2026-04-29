import {
  Brain, LayoutDashboard, Settings, LogOut, Activity, Database,
  FolderOpen, Key, Webhook, BarChart2
} from "lucide-react";
import { Link, useLocation } from "react-router-dom";
import React from "react";

import { useParams } from "react-router-dom";

const DashboardLayout = ({ children }: { children: React.ReactNode }) => {
  const location = useLocation();
  const { projectId } = useParams();

  const NAV_ITEMS = [
    { to: `/dashboard/${projectId}`,             icon: LayoutDashboard, label: "Dashboard" },
    { to: `/dashboard/${projectId}/pulse`,       icon: Activity,        label: "Memory Pulse" },
    { to: `/dashboard/${projectId}/memories`,    icon: Database,        label: "Memory Explorer" },
    { to: `/dashboard/${projectId}/projects`,    icon: FolderOpen,      label: "Projects" },
    { to: `/dashboard/${projectId}/benchmarks`,  icon: BarChart2,       label: "Benchmarks" },
    { to: `/dashboard/${projectId}/settings`,    icon: Settings,        label: "Settings" },
  ];

  return (
    <div className="min-h-screen bg-background flex flex-col md:flex-row">
      <aside className="w-full md:w-64 border-r border-zinc-900 bg-black p-8 flex flex-col relative z-20 shrink-0">
        <div className="flex items-center gap-2 mb-12">
          <Link to="/" className="font-heading text-lg font-black tracking-tighter text-white uppercase">NeuroSleepNet</Link>
        </div>
        <nav className="flex-1 space-y-0.5">
          {NAV_ITEMS.map(({ to, icon: Icon, label }) => {
            const active = location.pathname === to;
            return (
              <Link key={to} to={to} className={`flex items-center gap-3 px-3 py-2.5 rounded-none text-xs transition-all duration-150 uppercase tracking-widest ${
                active
                  ? "bg-white text-black font-bold"
                  : "text-zinc-500 hover:text-white"
              }`}>
                <Icon className="h-4 w-4 shrink-0" />
                {label}
              </Link>
            );
          })}
        </nav>
      </aside>
      <main className="flex-1 overflow-y-auto relative z-10 p-6 md:p-10">
        {children}
      </main>
    </div>
  );
};

export default DashboardLayout;
