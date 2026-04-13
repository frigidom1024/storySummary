"use client"

import { useLanguage } from "@/lib/i18n/language-context"
import { Globe } from "lucide-react"
import { Button } from "@/components/ui/button"

export function LanguageSwitcher() {
  const { locale, setLocale } = useLanguage()

  const toggleLocale = () => {
    setLocale(locale === "zh" ? "en" : "zh")
  }

  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={toggleLocale}
      className="flex items-center gap-1.5 text-muted-foreground hover:text-foreground"
    >
      <Globe className="w-4 h-4" />
      <span className="text-sm font-medium">
        {locale === "zh" ? "EN" : "中文"}
      </span>
    </Button>
  )
}
