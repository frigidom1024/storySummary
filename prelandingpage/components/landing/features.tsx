"use client"

import { BookOpen, Network, Palette, FileText, Layers, Zap, Video, UserCircle } from "lucide-react"
import { useLanguage } from "@/lib/i18n/language-context"

const featureIcons = [BookOpen, Network, Palette, FileText, Layers, Zap, Video, UserCircle]
const featureColors = [
  { color: "text-primary", bgColor: "bg-primary/10" },
  { color: "text-accent", bgColor: "bg-accent/10" },
  { color: "text-primary", bgColor: "bg-primary/10" },
  { color: "text-accent", bgColor: "bg-accent/10" },
  { color: "text-primary", bgColor: "bg-primary/10" },
  { color: "text-accent", bgColor: "bg-accent/10" },
  { color: "text-primary", bgColor: "bg-primary/10", isNew: true },
  { color: "text-accent", bgColor: "bg-accent/10", isNew: true },
]

export function Features() {
  const { t } = useLanguage()

  return (
    <section className="py-24 px-4 sm:px-6 lg:px-8">
      <div className="max-w-6xl mx-auto">
        {/* 标题区域 */}
        <div className="text-center mb-16">
          <p className="text-primary font-medium mb-4">{t.features.sectionLabel}</p>
          <h2 className="text-3xl sm:text-4xl font-bold text-foreground mb-4 text-balance">
            {t.features.title}
          </h2>
          <p className="text-muted-foreground text-lg max-w-2xl mx-auto text-pretty">
            {t.features.subtitle}
          </p>
        </div>

        {/* 功能卡片网格 */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {t.features.items.map((feature, index) => {
            const Icon = featureIcons[index]
            const colors = featureColors[index]
            return (
              <div
                key={index}
                className="group relative p-6 rounded-2xl bg-card border border-border hover:border-primary/50 transition-all duration-300"
              >
                {colors.isNew && (
                  <span className="absolute top-4 right-4 px-2 py-1 text-xs font-medium bg-primary/20 text-primary rounded-full">
                    {t.features.comingSoon}
                  </span>
                )}
                <div className={`w-12 h-12 rounded-xl ${colors.bgColor} flex items-center justify-center mb-4`}>
                  <Icon className={`w-6 h-6 ${colors.color}`} />
                </div>
                <h3 className="text-xl font-semibold text-foreground mb-2">
                  {feature.title}
                </h3>
                <p className="text-muted-foreground leading-relaxed">
                  {feature.description}
                </p>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
