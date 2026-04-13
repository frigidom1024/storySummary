import { Header } from "@/components/landing/header"
import { Hero } from "@/components/landing/hero"
import { Features } from "@/components/landing/features"
import { WhyUs } from "@/components/landing/why-us"
import { Workflow } from "@/components/landing/workflow"
import { Preview } from "@/components/landing/preview"
import { Pricing } from "@/components/landing/pricing"
import { FAQ } from "@/components/landing/faq"
import { CTA } from "@/components/landing/cta"
import { Footer } from "@/components/landing/footer"

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background">
      <Header />
      
      <main className="pt-16">
        {/* Hero区域 */}
        <Hero />
        
        {/* 功能展示 */}
        <section id="features">
          <Features />
        </section>
        
        {/* 为什么选择我们 */}
        <section id="why-us">
          <WhyUs />
        </section>
        
        {/* 工作流程 */}
        <section id="workflow">
          <Workflow />
        </section>
        
        {/* 产品预览 */}
        <Preview />
        
        {/* 定价方案 */}
        <section id="pricing">
          <Pricing />
        </section>
        
        {/* FAQ */}
        <section id="faq">
          <FAQ />
        </section>
        
        {/* CTA */}
        <CTA />
      </main>
      
      <Footer />
    </div>
  )
}
