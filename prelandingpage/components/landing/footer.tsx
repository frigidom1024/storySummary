"use client"

import { Sparkles } from "lucide-react"
import { useLanguage } from "@/lib/i18n/language-context"

export function Footer() {
  const { t, locale } = useLanguage()

  const footerLinks = [
    {
      title: t.footer.groups.product.title,
      links: t.footer.groups.product.links.map((label) => ({ label, href: "#" })),
    },
    {
      title: t.footer.groups.company.title,
      links: t.footer.groups.company.links.map((label) => ({ label, href: "#" })),
    },
    {
      title: t.footer.groups.resources.title,
      links: t.footer.groups.resources.links.map((label) => ({ label, href: "#" })),
    },
    {
      title: t.footer.groups.legal.title,
      links: t.footer.groups.legal.links.map((label) => ({ label, href: "#" })),
    },
  ]

  return (
    <footer className="bg-secondary/30 border-t border-border">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-8">
          {/* Logo和简介 */}
          <div className="col-span-2 md:col-span-1">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
                <Sparkles className="w-5 h-5 text-primary-foreground" />
              </div>
              <span className="text-lg font-bold text-foreground">
                {locale === "zh" ? "口播稿AI" : "ScriptAI"}
              </span>
            </div>
            <p className="text-sm text-muted-foreground leading-relaxed">
              {t.footer.tagline}
            </p>
          </div>

          {/* 链接分组 */}
          {footerLinks.map((group) => (
            <div key={group.title}>
              <h4 className="font-medium text-foreground mb-4">{group.title}</h4>
              <ul className="space-y-3">
                {group.links.map((link) => (
                  <li key={link.label}>
                    <a
                      href={link.href}
                      className="text-sm text-muted-foreground hover:text-foreground transition-colors"
                    >
                      {link.label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* 底部版权信息 */}
        <div className="mt-12 pt-8 border-t border-border flex flex-col md:flex-row items-center justify-between gap-4">
          <p className="text-sm text-muted-foreground">
            {t.footer.copyright}
          </p>
          <div className="flex items-center gap-6">
            {t.footer.social.map((item) => (
              <a key={item} href="#" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
                {item}
              </a>
            ))}
          </div>
        </div>
      </div>
    </footer>
  )
}
