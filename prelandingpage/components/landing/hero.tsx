"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Sparkles, ArrowRight, BookOpen, Mic } from "lucide-react"
import { useLanguage } from "@/lib/i18n/language-context"

export function Hero() {
  const [email, setEmail] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isSubmitted, setIsSubmitted] = useState(false)
  const { t } = useLanguage()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email) return
    setIsSubmitting(true)
    // 模拟提交
    await new Promise((resolve) => setTimeout(resolve, 1000))
    setIsSubmitting(false)
    setIsSubmitted(true)
    setEmail("")
  }

  return (
    <section className="relative min-h-[90vh] flex items-center justify-center overflow-hidden">
      {/* 背景装饰 */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary/10 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-accent/10 rounded-full blur-3xl" />
      </div>

      <div className="relative z-10 max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        {/* 预发布标签 */}
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 border border-primary/20 text-primary text-sm font-medium mb-8">
          <Sparkles className="w-4 h-4" />
          <span>{t.hero.badge}</span>
        </div>

        {/* 主标题 */}
        <h1 className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-bold tracking-tight text-foreground mb-6">
          <span className="text-balance">{t.hero.titlePart1}</span>
          <br />
          <span className="bg-gradient-to-r from-primary via-accent to-primary bg-clip-text text-transparent">
            {t.hero.titlePart2}
          </span>
        </h1>

        {/* 副标题 */}
        <p className="text-lg sm:text-xl text-muted-foreground max-w-2xl mx-auto mb-12 leading-relaxed text-pretty">
          {t.hero.subtitle}
        </p>

        {/* 核心功能图标 */}
        <div className="flex flex-wrap justify-center gap-6 mb-12">
          <div className="flex items-center gap-2 text-muted-foreground">
            <BookOpen className="w-5 h-5 text-primary" />
            <span>{t.hero.feature1}</span>
          </div>
          <div className="flex items-center gap-2 text-muted-foreground">
            <Sparkles className="w-5 h-5 text-accent" />
            <span>{t.hero.feature2}</span>
          </div>
          <div className="flex items-center gap-2 text-muted-foreground">
            <Mic className="w-5 h-5 text-primary" />
            <span>{t.hero.feature3}</span>
          </div>
        </div>

        {/* 邮箱订阅表单 */}
        {isSubmitted ? (
          <div className="inline-flex items-center gap-2 px-6 py-4 rounded-xl bg-accent/10 border border-accent/20 text-accent">
            <Sparkles className="w-5 h-5" />
            <span className="font-medium">{t.hero.thankYou}</span>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-4 max-w-md mx-auto">
            <Input
              type="email"
              placeholder={t.hero.emailPlaceholder}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="h-12 px-4 bg-secondary border-border text-foreground placeholder:text-muted-foreground"
              required
            />
            <Button 
              type="submit" 
              size="lg"
              disabled={isSubmitting}
              className="h-12 px-6 bg-primary hover:bg-primary/90 text-primary-foreground font-medium"
            >
              {isSubmitting ? (
                t.hero.submitting
              ) : (
                <>
                  {t.hero.joinWaitlist}
                  <ArrowRight className="w-4 h-4 ml-2" />
                </>
              )}
            </Button>
          </form>
        )}

        <p className="text-sm text-muted-foreground mt-4">
          {t.hero.alreadyJoined} <span className="text-primary font-medium">2,847</span> {t.hero.waitlistCount}
        </p>
      </div>
    </section>
  )
}
