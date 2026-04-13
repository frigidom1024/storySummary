"use client"

import { Upload, Settings, Sparkles, Download } from "lucide-react"
import { useLanguage } from "@/lib/i18n/language-context"

const stepIcons = [Upload, Settings, Sparkles, Download]

export function Workflow() {
  const { t } = useLanguage()

  return (
    <section className="py-24 px-4 sm:px-6 lg:px-8 bg-secondary/30">
      <div className="max-w-6xl mx-auto">
        {/* 标题区域 */}
        <div className="text-center mb-16">
          <p className="text-primary font-medium mb-4">{t.workflow.sectionLabel}</p>
          <h2 className="text-3xl sm:text-4xl font-bold text-foreground mb-4 text-balance">
            {t.workflow.title}
          </h2>
          <p className="text-muted-foreground text-lg max-w-2xl mx-auto text-pretty">
            {t.workflow.subtitle}
          </p>
        </div>

        {/* 步骤展示 */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
          {t.workflow.steps.map((step, index) => {
            const Icon = stepIcons[index]
            return (
              <div key={index} className="relative">
                {/* 连接线 */}
                {index < t.workflow.steps.length - 1 && (
                  <div className="hidden lg:block absolute top-10 left-[calc(100%+1rem)] w-[calc(100%-2rem)] h-px bg-border" />
                )}
                
                <div className="text-center">
                  {/* 步骤编号 */}
                  <div className="relative inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-card border border-border mb-6">
                    <Icon className="w-8 h-8 text-primary" />
                    <span className="absolute -top-2 -right-2 w-6 h-6 rounded-full bg-primary text-primary-foreground text-xs font-bold flex items-center justify-center">
                      {index + 1}
                    </span>
                  </div>
                  
                  <h3 className="text-xl font-semibold text-foreground mb-2">
                    {step.title}
                  </h3>
                  <p className="text-muted-foreground leading-relaxed">
                    {step.description}
                  </p>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
