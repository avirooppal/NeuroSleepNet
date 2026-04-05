import Navbar from "@/components/Navbar";
import HeroSection from "@/components/HeroSection";
import ProblemSection from "@/components/ProblemSection";
import SolutionSection from "@/components/SolutionSection";
import CodeSection from "@/components/CodeSection";
import BenchmarkSection from "@/components/BenchmarkSection";
import UseCasesSection from "@/components/UseCasesSection";
import PricingSection from "@/components/PricingSection";
import CTASection from "@/components/CTASection";
import Footer from "@/components/Footer";

const Index = () => (
  <div className="min-h-screen">
    <Navbar />
    <HeroSection />
    <ProblemSection />
    <SolutionSection />
    <CodeSection />
    <BenchmarkSection />
    <UseCasesSection />
    <PricingSection />
    <CTASection />
    <Footer />
  </div>
);

export default Index;
