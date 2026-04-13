"use client"

import { AlertTriangle, CheckCircle2, Brain, Layers, Shield, Sparkles } from "lucide-react"
import { useLanguage } from "@/lib/i18n/language-context"

const stepIcons = [Layers, Brain, Shield, Sparkles]
const stepStyles = [
  { bg: "bg-primary/10", color: "text-primary", numBg: "bg-primary", numText: "text-primary-foreground" },
  { bg: "bg-accent/10", color: "text-accent", numBg: "bg-accent", numText: "text-accent-foreground" },
  { bg: "bg-primary/10", color: "text-primary", numBg: "bg-primary", numText: "text-primary-foreground" },
  { bg: "bg-accent/10", color: "text-accent", numBg: "bg-accent", numText: "text-accent-foreground" },
]

export function WhyUs() {
  const { t } = useLanguage()

  return (
    <section className="py-24 px-4 relative overflow-hidden">
      {/* 背景装饰 */}
      <div className="absolute inset-0 bg-gradient-to-b from-background via-primary/5 to-background" />
      
      <div className="max-w-6xl mx-auto relative">
        <div className="text-center mb-16">
          <span className="inline-block px-4 py-1.5 rounded-full bg-primary/10 text-primary text-sm font-medium mb-4">
            {t.whyUs.sectionLabel}
          </span>
          <h2 className="text-3xl md:text-4xl font-bold text-foreground mb-4 text-balance">
            {t.whyUs.title}
          </h2>
          <p className="text-muted-foreground text-lg max-w-2xl mx-auto text-pretty">
            {t.whyUs.subtitle}
          </p>
        </div>

        {/* 问题与解决方案对比 */}
        <div className="grid md:grid-cols-2 gap-8 mb-16">
          {/* 传统方案问题 */}
          <div className="p-8 rounded-2xl bg-destructive/5 border border-destructive/20">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-xl bg-destructive/20 flex items-center justify-center">
                <AlertTriangle className="w-5 h-5 text-destructive" />
              </div>
              <h3 className="text-xl font-semibold text-foreground">{t.whyUs.traditional.title}</h3>
            </div>
            
            <div className="space-y-4">
              {t.whyUs.traditional.items.map((item, index) => (
                <div key={index} className="flex items-start gap-3">
                  <div className="w-5 h-5 rounded-full bg-destructive/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-destructive text-xs">{"✕"}</span>
                  </div>
                  <div>
                    <p className="text-foreground font-medium">{item.title}</p>
                    <p className="text-muted-foreground text-sm">{item.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* 我们的解决方案 */}
          <div className="p-8 rounded-2xl bg-primary/5 border border-primary/20">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-xl bg-primary/20 flex items-center justify-center">
                <CheckCircle2 className="w-5 h-5 text-primary" />
              </div>
              <h3 className="text-xl font-semibold text-foreground">{t.whyUs.ourSolution.title}</h3>
            </div>
            
            <div className="space-y-4">
              {t.whyUs.ourSolution.items.map((item, index) => (
                <div key={index} className="flex items-start gap-3">
                  <div className="w-5 h-5 rounded-full bg-primary/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-primary text-xs">{"✓"}</span>
                  </div>
                  <div>
                    <p className="text-foreground font-medium">{item.title}</p>
                    <p className="text-muted-foreground text-sm">{item.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* 技术架构展示 */}
        <div className="p-8 rounded-2xl bg-card border border-border">
          <h3 className="text-xl font-semibold text-foreground text-center mb-8">
            {t.whyUs.architecture.title}
          </h3>
          
          <div className="grid md:grid-cols-4 gap-6">
            {t.whyUs.architecture.steps.map((step, index) => {
              const Icon = stepIcons[index]
              const style = stepStyles[index]
              return (
                <div key={index} className="text-center">
                  <div className={`w-16 h-16 rounded-2xl ${style.bg} flex items-center justify-center mx-auto mb-4 relative`}>
                    <Icon className={`w-8 h-8 ${style.color}`} />
                    <span className={`absolute -top-2 -right-2 w-6 h-6 rounded-full ${style.numBg} ${style.numText} text-sm font-bold flex items-center justify-center`}>
                      {index + 1}
                    </span>
                  </div>
                  <h4 className="font-semibold text-foreground mb-2">{step.title}</h4>
                  <p className="text-sm text-muted-foreground">{step.description}</p>
                </div>
              )
            })}
          </div>

          {/* 底部统计 */}
          <div className="grid grid-cols-3 gap-4 mt-10 pt-8 border-t border-border">
            <div className="text-center">
              <div className="text-3xl font-bold text-primary mb-1">99.2%</div>
              <div className="text-sm text-muted-foreground">{t.whyUs.stats.accuracy}</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-accent mb-1">100万+</div>
              <div className="text-sm text-muted-foreground">{t.whyUs.stats.wordLimit}</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-primary mb-1">0</div>
              <div className="text-sm text-muted-foreground">{t.whyUs.stats.noMistakes}</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
