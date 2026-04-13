"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Sparkles, ArrowRight, Mail } from "lucide-react"
import { useLanguage } from "@/lib/i18n/language-context"

export function CTA() {
  const [email, setEmail] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isSubmitted, setIsSubmitted] = useState(false)
  const { t } = useLanguage()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email) return
    setIsSubmitting(true)
    await new Promise((resolve) => setTimeout(resolve, 1000))
    setIsSubmitting(false)
    setIsSubmitted(true)
    setEmail("")
  }

  return (
    <section className="py-24 px-4 sm:px-6 lg:px-8 relative overflow-hidden">
      {/* 背景装饰 */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-primary/5 rounded-full blur-3xl" />
      </div>

      <div className="relative z-10 max-w-4xl mx-auto text-center">
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-accent/10 border border-accent/20 text-accent text-sm font-medium mb-8">
          <Mail className="w-4 h-4" />
          <span>{t.cta.badge}</span>
        </div>

        <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold text-foreground mb-6 text-balance">
          {t.cta.title}
        </h2>

        <p className="text-lg text-muted-foreground max-w-2xl mx-auto mb-12 leading-relaxed text-pretty">
          {t.cta.subtitle}
        </p>

        {isSubmitted ? (
          <div className="inline-flex items-center gap-2 px-6 py-4 rounded-xl bg-accent/10 border border-accent/20 text-accent">
            <Sparkles className="w-5 h-5" />
            <span className="font-medium">{t.cta.thankYou}</span>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-4 max-w-lg mx-auto">
            <Input
              type="email"
              placeholder={t.cta.emailPlaceholder}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="h-14 px-5 bg-secondary border-border text-foreground placeholder:text-muted-foreground text-base"
              required
            />
            <Button 
              type="submit" 
              size="lg"
              disabled={isSubmitting}
              className="h-14 px-8 bg-primary hover:bg-primary/90 text-primary-foreground font-medium text-base"
            >
              {isSubmitting ? (
                t.cta.submitting
              ) : (
                <>
                  {t.cta.joinNow}
                  <ArrowRight className="w-5 h-5 ml-2" />
                </>
              )}
            </Button>
          </form>
        )}

        <p className="text-sm text-muted-foreground mt-6">
          {t.cta.privacy}
        </p>
      </div>
    </section>
  )
}
