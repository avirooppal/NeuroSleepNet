import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes, Navigate } from "react-router-dom";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Toaster as HotToaster } from "react-hot-toast";

import Index from "./pages/Index.tsx";
import NotFound from "./pages/NotFound.tsx";
import Onboarding from "./pages/Onboarding.tsx";
import Dashboard from "./pages/Dashboard.tsx";
import MemoryPulse from "./pages/MemoryPulse.tsx";
import MemoryExplorer from "./pages/MemoryExplorer.tsx";
import Projects from "./pages/Projects.tsx";
import Benchmarks from "./pages/Benchmarks.tsx";
import Settings from "./pages/Settings.tsx";
import DashboardLayout from "./components/DashboardLayout.tsx";

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, retry: 1 } },
});

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <HotToaster
        position="bottom-right"
        toastOptions={{
          style: {
            background: '#1e2030',
            color: '#e2e8f0',
            border: '1px solid #00e5cc33',
            borderRadius: '10px',
          },
        }}
      />
      <BrowserRouter>
        <Routes>
          {/* Landing */}
          <Route path="/" element={<Index />} />
          {/* Onboarding */}
          <Route path="/onboarding" element={<Onboarding />} />
          {/* Dashboard routes — all wrapped in DashboardLayout */}
          <Route path="/dashboard/:projectId" element={<DashboardLayout><Dashboard /></DashboardLayout>} />
          <Route path="/p/:projectId" element={<DashboardLayout><Dashboard /></DashboardLayout>} />
          <Route path="/dashboard/:projectId/pulse" element={<DashboardLayout><MemoryPulse /></DashboardLayout>} />
          <Route path="/dashboard/:projectId/memories" element={<DashboardLayout><MemoryExplorer /></DashboardLayout>} />
          <Route path="/dashboard/:projectId/projects" element={<DashboardLayout><Projects /></DashboardLayout>} />
          <Route path="/dashboard/:projectId/benchmarks" element={<DashboardLayout><Benchmarks /></DashboardLayout>} />
          <Route path="/dashboard/:projectId/settings" element={<DashboardLayout><Settings /></DashboardLayout>} />
          {/* Catch-all */}
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
