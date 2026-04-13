"use client"

import { useState } from "react"
import { BookOpen, Users, TrendingUp, MessageSquare, ChevronRight, GitBranch, Zap, Heart, Swords, Star, Smile, Search, HeartHandshake, Briefcase } from "lucide-react"
import { useLanguage } from "@/lib/i18n/language-context"

export function Preview() {
  const [activeTab, setActiveTab] = useState<"chapters" | "character" | "narrative" | "style">("narrative")
  const [hoveredNode, setHoveredNode] = useState<number | null>(null)
  const { t } = useLanguage()

  const mockChapters = [
    { id: 1, title: t.preview.chapters.ch1, selected: false },
    { id: 2, title: t.preview.chapters.ch2, selected: true },
    { id: 3, title: t.preview.chapters.ch3, selected: true },
    { id: 4, title: t.preview.chapters.ch4, selected: false },
    { id: 5, title: t.preview.chapters.ch5, selected: false },
  ]

  const narrativeNodes = [
    {
      id: 1,
      type: "opening",
      title: t.preview.narrativeNodes.opening.title,
      chapter: t.preview.chapters.ch1,
      description: t.preview.narrativeNodes.opening.desc,
      icon: Star,
      color: "bg-primary",
      position: { x: 10, y: 20 },
    },
    {
      id: 2,
      type: "encounter",
      title: t.preview.narrativeNodes.encounter.title,
      chapter: t.preview.chapters.ch2,
      description: t.preview.narrativeNodes.encounter.desc,
      icon: Zap,
      color: "bg-chart-4",
      position: { x: 35, y: 40 },
    },
    {
      id: 3,
      type: "romance",
      title: t.preview.narrativeNodes.romance.title,
      chapter: t.preview.chapters.ch2,
      description: t.preview.narrativeNodes.romance.desc,
      icon: Heart,
      color: "bg-accent",
      position: { x: 60, y: 25 },
    },
    {
      id: 4,
      type: "conflict",
      title: t.preview.narrativeNodes.conflict.title,
      chapter: t.preview.chapters.ch3,
      description: t.preview.narrativeNodes.conflict.desc,
      icon: Swords,
      color: "bg-destructive",
      position: { x: 85, y: 45 },
    },
  ]

  const styles = [
    { id: "humor", icon: Smile, ...t.preview.styles.humor },
    { id: "suspense", icon: Search, ...t.preview.styles.suspense },
    { id: "emotional", icon: HeartHandshake, ...t.preview.styles.emotional },
    { id: "professional", icon: Briefcase, ...t.preview.styles.professional },
  ]

  return (
    <section className="py-24 px-4 sm:px-6 lg:px-8">
      <div className="max-w-6xl mx-auto">
        {/* 标题区域 */}
        <div className="text-center mb-16">
          <p className="text-primary font-medium mb-4">{t.preview.sectionLabel}</p>
          <h2 className="text-3xl sm:text-4xl font-bold text-foreground mb-4 text-balance">
            {t.preview.title}
          </h2>
          <p className="text-muted-foreground text-lg max-w-2xl mx-auto text-pretty">
            {t.preview.subtitle}
          </p>
        </div>

        {/* 产品预览模拟界面 */}
        <div className="rounded-2xl bg-card border border-border overflow-hidden shadow-2xl">
          {/* 顶部工具栏 */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-secondary/50">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-destructive/80" />
                <div className="w-3 h-3 rounded-full bg-chart-4/80" />
                <div className="w-3 h-3 rounded-full bg-accent/80" />
              </div>
              <div className="text-sm text-muted-foreground">
                {t.preview.projectTitle}
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs px-2 py-1 rounded bg-accent/20 text-accent">{t.preview.autoSave}</span>
            </div>
          </div>

          {/* Tab 切换 */}
          <div className="flex items-center gap-1 px-6 py-3 border-b border-border bg-secondary/30">
            <button
              onClick={() => setActiveTab("chapters")}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm transition-colors ${
                activeTab === "chapters"
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground hover:bg-secondary"
              }`}
            >
              <BookOpen className="w-4 h-4" />
              {t.preview.tabs.chapters}
            </button>
            <button
              onClick={() => setActiveTab("character")}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm transition-colors ${
                activeTab === "character"
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground hover:bg-secondary"
              }`}
            >
              <Users className="w-4 h-4" />
              {t.preview.tabs.character}
            </button>
            <button
              onClick={() => setActiveTab("narrative")}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm transition-colors ${
                activeTab === "narrative"
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground hover:bg-secondary"
              }`}
            >
              <GitBranch className="w-4 h-4" />
              {t.preview.tabs.narrative}
            </button>
            <button
              onClick={() => setActiveTab("style")}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm transition-colors ${
                activeTab === "style"
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground hover:bg-secondary"
              }`}
            >
              <MessageSquare className="w-4 h-4" />
              {t.preview.tabs.style}
            </button>
          </div>

          {/* 主内容区 */}
          <div className="min-h-[500px]">
            {/* 章节选择 Tab */}
            {activeTab === "chapters" && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 p-6">
                <div>
                  <div className="flex items-center gap-2 mb-4">
                    <BookOpen className="w-5 h-5 text-primary" />
                    <span className="font-medium text-foreground">{t.preview.selectChapters}</span>
                  </div>
                  <div className="space-y-2">
                    {mockChapters.map((chapter) => (
                      <div
                        key={chapter.id}
                        className={`flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-colors ${
                          chapter.selected 
                            ? "bg-primary/10 border border-primary/30" 
                            : "bg-secondary/50 hover:bg-secondary"
                        }`}
                      >
                        <div className={`w-4 h-4 rounded border ${
                          chapter.selected 
                            ? "bg-primary border-primary" 
                            : "border-muted-foreground"
                        }`}>
                          {chapter.selected && (
                            <svg className="w-4 h-4 text-primary-foreground" viewBox="0 0 16 16" fill="currentColor">
                              <path d="M13.78 4.22a.75.75 0 010 1.06l-7.25 7.25a.75.75 0 01-1.06 0L2.22 9.28a.75.75 0 011.06-1.06L6 10.94l6.72-6.72a.75.75 0 011.06 0z" />
                            </svg>
                          )}
                        </div>
                        <span className="text-sm text-foreground">{chapter.title}</span>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="flex flex-col justify-center items-center text-center p-8 bg-secondary/30 rounded-xl">
                  <div className="w-16 h-16 rounded-full bg-primary/20 flex items-center justify-center mb-4">
                    <BookOpen className="w-8 h-8 text-primary" />
                  </div>
                  <p className="text-foreground font-medium mb-2">{t.preview.chaptersSelected}</p>
                  <p className="text-muted-foreground text-sm mb-4">{t.preview.estimatedWords}</p>
                  <button className="px-6 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors">
                    {t.preview.startGenerate}
                  </button>
                </div>
              </div>
            )}

            {/* 人物关系图谱 Tab */}
            {activeTab === "character" && (
              <div className="p-6">
                <div className="flex items-center gap-2 mb-4">
                  <Users className="w-5 h-5 text-accent" />
                  <span className="font-medium text-foreground">{t.preview.characterGraph}</span>
                  <span className="text-xs px-2 py-1 rounded bg-secondary text-muted-foreground ml-2">
                    {t.preview.aiAnalyzed}
                  </span>
                </div>
                
                {/* 模拟关系图 */}
                <div className="relative h-80 bg-secondary/30 rounded-xl p-4">
                  {/* SVG 连接线 */}
                  <svg className="absolute inset-0 w-full h-full pointer-events-none">
                    <line x1="50%" y1="50%" x2="50%" y2="15%" stroke="currentColor" strokeWidth="2" className="text-muted-foreground/30" strokeDasharray="4,4" />
                    <line x1="50%" y1="50%" x2="25%" y2="80%" stroke="currentColor" strokeWidth="2" className="text-accent/50" />
                    <line x1="50%" y1="50%" x2="75%" y2="80%" stroke="currentColor" strokeWidth="2" className="text-destructive/50" />
                  </svg>
                  
                  {/* 中心人物 */}
                  <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 z-10">
                    <div className="w-20 h-20 rounded-full bg-primary flex items-center justify-center text-primary-foreground font-medium shadow-lg shadow-primary/30 border-4 border-background">
                      <div className="text-center">
                        <div className="text-sm font-bold">Li Yifeng</div>
                        <div className="text-xs opacity-80">{t.preview.characters.protagonist}</div>
                      </div>
                    </div>
                  </div>
                  
                  {/* 连接线和其他人物 */}
                  <div className="absolute top-4 left-1/2 transform -translate-x-1/2">
                    <div className="w-14 h-14 rounded-full bg-chart-4 flex items-center justify-center text-xs text-primary-foreground border-2 border-background">
                      <div className="text-center">
                        <div className="font-medium">Master</div>
                        <div className="text-xs opacity-80">{t.preview.characters.mentor}</div>
                      </div>
                    </div>
                  </div>
                  <div className="absolute bottom-4 left-1/4 transform -translate-x-1/2">
                    <div className="w-14 h-14 rounded-full bg-accent flex items-center justify-center text-xs text-accent-foreground border-2 border-background">
                      <div className="text-center">
                        <div className="font-medium">Su Qing</div>
                        <div className="text-xs opacity-80">{t.preview.characters.heroine}</div>
                      </div>
                    </div>
                  </div>
                  <div className="absolute bottom-4 right-1/4 transform translate-x-1/2">
                    <div className="w-14 h-14 rounded-full bg-destructive flex items-center justify-center text-xs text-destructive-foreground border-2 border-background">
                      <div className="text-center">
                        <div className="font-medium">Wang Ba</div>
                        <div className="text-xs opacity-80">{t.preview.characters.villain}</div>
                      </div>
                    </div>
                  </div>
                  
                  {/* 关系标签 */}
                  <div className="absolute top-24 left-1/2 transform -translate-x-1/2 px-2 py-1 rounded bg-chart-4/20 text-xs text-chart-4">
                    {t.preview.relationships.master}
                  </div>
                  <div className="absolute bottom-28 left-[30%] px-2 py-1 rounded bg-accent/20 text-xs text-accent">
                    {t.preview.relationships.lovers}
                  </div>
                  <div className="absolute bottom-28 right-[30%] px-2 py-1 rounded bg-destructive/20 text-xs text-destructive">
                    {t.preview.relationships.enemy}
                  </div>
                </div>
              </div>
            )}

            {/* 叙述节点图谱 Tab */}
            {activeTab === "narrative" && (
              <div className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <GitBranch className="w-5 h-5 text-primary" />
                    <span className="font-medium text-foreground">{t.preview.narrativeGraph}</span>
                    <span className="text-xs px-2 py-1 rounded bg-secondary text-muted-foreground ml-2">
                      {t.preview.storyVisualization}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1"><Star className="w-3 h-3 text-primary" /> {t.preview.opening}</span>
                    <span className="flex items-center gap-1"><Zap className="w-3 h-3 text-chart-4" /> {t.preview.turning}</span>
                    <span className="flex items-center gap-1"><Heart className="w-3 h-3 text-accent" /> {t.preview.emotion}</span>
                    <span className="flex items-center gap-1"><Swords className="w-3 h-3 text-destructive" /> {t.preview.conflict}</span>
                  </div>
                </div>
                
                {/* 叙述节点图谱 */}
                <div className="relative h-72 bg-secondary/30 rounded-xl overflow-hidden">
                  {/* 背景网格 */}
                  <div className="absolute inset-0 opacity-10">
                    <svg width="100%" height="100%">
                      <defs>
                        <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                          <path d="M 40 0 L 0 0 0 40" fill="none" stroke="currentColor" strokeWidth="1" className="text-foreground"/>
                        </pattern>
                      </defs>
                      <rect width="100%" height="100%" fill="url(#grid)" />
                    </svg>
                  </div>
                  
                  {/* 连接线 SVG */}
                  <svg className="absolute inset-0 w-full h-full pointer-events-none">
                    {/* 节点1 -> 节点2 */}
                    <path 
                      d="M 12% 30% Q 25% 25%, 37% 50%" 
                      fill="none" 
                      stroke="currentColor" 
                      strokeWidth="2" 
                      className="text-muted-foreground/40"
                      strokeDasharray="6,3"
                    />
                    <text x="22%" y="32%" className="text-xs fill-muted-foreground">{t.preview.connections.trigger}</text>
                    
                    {/* 节点2 -> 节点3 */}
                    <path 
                      d="M 40% 50% Q 50% 30%, 62% 35%" 
                      fill="none" 
                      stroke="currentColor" 
                      strokeWidth="2" 
                      className="text-accent/50"
                    />
                    <text x="48%" y="33%" className="text-xs fill-accent">{t.preview.connections.leadTo}</text>
                    
                    {/* 节点2 -> 节点4 */}
                    <path 
                      d="M 40% 55% Q 60% 65%, 82% 55%" 
                      fill="none" 
                      stroke="currentColor" 
                      strokeWidth="2" 
                      className="text-muted-foreground/40"
                      strokeDasharray="6,3"
                    />
                    <text x="58%" y="65%" className="text-xs fill-muted-foreground">{t.preview.connections.foreshadow}</text>
                    
                    {/* 节点3 -> 节点4 */}
                    <path 
                      d="M 67% 35% Q 77% 40%, 82% 50%" 
                      fill="none" 
                      stroke="currentColor" 
                      strokeWidth="2" 
                      className="text-destructive/50"
                    />
                    <text x="75%" y="38%" className="text-xs fill-destructive">{t.preview.connections.drive}</text>
                  </svg>
                  
                  {/* 叙述节点 */}
                  {narrativeNodes.map((node) => {
                    const Icon = node.icon
                    const isHovered = hoveredNode === node.id
                    return (
                      <div
                        key={node.id}
                        className="absolute transform -translate-x-1/2 -translate-y-1/2 cursor-pointer transition-all duration-200"
                        style={{ left: `${node.position.x}%`, top: `${node.position.y}%` }}
                        onMouseEnter={() => setHoveredNode(node.id)}
                        onMouseLeave={() => setHoveredNode(null)}
                      >
                        <div className={`relative ${isHovered ? 'scale-110 z-20' : 'z-10'}`}>
                          {/* 节点主体 */}
                          <div className={`w-14 h-14 rounded-xl ${node.color} flex items-center justify-center shadow-lg transition-shadow ${
                            isHovered ? 'shadow-xl' : ''
                          }`}>
                            <Icon className="w-6 h-6 text-primary-foreground" />
                          </div>
                          
                          {/* 节点标签 */}
                          <div className={`absolute -bottom-8 left-1/2 transform -translate-x-1/2 whitespace-nowrap text-center transition-opacity ${
                            isHovered ? 'opacity-100' : 'opacity-80'
                          }`}>
                            <div className="text-xs font-medium text-foreground">{node.title}</div>
                          </div>
                          
                          {/* Hover 详情卡片 */}
                          {isHovered && (
                            <div className="absolute top-full left-1/2 transform -translate-x-1/2 mt-12 w-48 p-3 bg-card border border-border rounded-lg shadow-xl z-30">
                              <div className="flex items-center gap-2 mb-2">
                                <div className={`w-6 h-6 rounded ${node.color} flex items-center justify-center`}>
                                  <Icon className="w-3 h-3 text-primary-foreground" />
                                </div>
                                <span className="text-sm font-medium text-foreground">{node.title}</span>
                              </div>
                              <p className="text-xs text-muted-foreground mb-2">{node.description}</p>
                              <div className="flex items-center justify-between text-xs">
                                <span className="text-muted-foreground">{node.chapter}</span>
                                <span className="text-primary cursor-pointer hover:underline">{t.preview.viewDetails}</span>
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    )
                  })}
                  
                  {/* 时间线指示器 */}
                  <div className="absolute bottom-4 left-6 right-6 flex items-center">
                    <div className="flex-1 h-1 bg-gradient-to-r from-primary via-chart-4 via-accent to-destructive rounded-full opacity-30" />
                    <div className="ml-4 text-xs text-muted-foreground flex items-center gap-1">
                      <TrendingUp className="w-3 h-3" />
                      {t.preview.storyProgress}
                    </div>
                  </div>
                </div>
                
                {/* 节点统计 */}
                <div className="grid grid-cols-4 gap-4 mt-4">
                  <div className="p-3 bg-primary/10 rounded-lg border border-primary/20">
                    <div className="flex items-center gap-2 mb-1">
                      <Star className="w-4 h-4 text-primary" />
                      <span className="text-xs text-muted-foreground">{t.preview.openingIntro}</span>
                    </div>
                    <div className="text-lg font-bold text-foreground">1</div>
                  </div>
                  <div className="p-3 bg-chart-4/10 rounded-lg border border-chart-4/20">
                    <div className="flex items-center gap-2 mb-1">
                      <Zap className="w-4 h-4 text-chart-4" />
                      <span className="text-xs text-muted-foreground">{t.preview.turningPoint}</span>
                    </div>
                    <div className="text-lg font-bold text-foreground">1</div>
                  </div>
                  <div className="p-3 bg-accent/10 rounded-lg border border-accent/20">
                    <div className="flex items-center gap-2 mb-1">
                      <Heart className="w-4 h-4 text-accent" />
                      <span className="text-xs text-muted-foreground">{t.preview.emotionLine}</span>
                    </div>
                    <div className="text-lg font-bold text-foreground">1</div>
                  </div>
                  <div className="p-3 bg-destructive/10 rounded-lg border border-destructive/20">
                    <div className="flex items-center gap-2 mb-1">
                      <Swords className="w-4 h-4 text-destructive" />
                      <span className="text-xs text-muted-foreground">{t.preview.conflictNode}</span>
                    </div>
                    <div className="text-lg font-bold text-foreground">1</div>
                  </div>
                </div>
              </div>
            )}

            {/* 稿件预览 Tab */}
            {activeTab === "style" && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 p-6">
                {/* 风格选择 */}
                <div>
                  <div className="flex items-center gap-2 mb-4">
                    <MessageSquare className="w-5 h-5 text-accent" />
                    <span className="font-medium text-foreground">{t.preview.selectStyle}</span>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    {styles.map((style) => {
                      const Icon = style.icon
                      return (
                        <div
                          key={style.id}
                          className={`p-4 rounded-xl border cursor-pointer transition-all ${
                            style.id === "humor"
                              ? "bg-primary/10 border-primary/30"
                              : "bg-secondary/50 border-border hover:border-primary/30"
                          }`}
                        >
                          <Icon className={`w-6 h-6 mb-2 ${style.id === "humor" ? "text-primary" : "text-muted-foreground"}`} />
                          <div className="font-medium text-foreground text-sm">{style.name}</div>
                          <div className="text-xs text-muted-foreground">{style.desc}</div>
                        </div>
                      )
                    })}
                  </div>
                </div>

                {/* 稿件预览 */}
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2">
                      <ChevronRight className="w-5 h-5 text-primary" />
                      <span className="font-medium text-foreground">{t.preview.scriptPreview}</span>
                    </div>
                    <button className="text-xs text-primary hover:underline">{t.preview.regenerate}</button>
                  </div>
                  <div className="p-4 bg-secondary/30 rounded-xl border border-border">
                    <p className="text-foreground text-sm leading-relaxed">
                      {"各位观众老爷们大家好！今天咱们要聊的这本小说，简直就是把我看傻了！"}
                    </p>
                    <p className="text-foreground text-sm leading-relaxed mt-3">
                      {"话说这位主角李逸风，从小就是个孤儿，在村子里被各种欺负。但是！就在他被打得半死的时候，天降一个神秘老道士..."}
                    </p>
                    <p className="text-foreground text-sm leading-relaxed mt-3">
                      {"这老道士一看李逸风的骨骼清奇，当场就惊呼：'这小子，百年难遇的修仙奇才啊！'"}
                    </p>
                    <div className="mt-4 pt-4 border-t border-border flex items-center justify-between text-xs text-muted-foreground">
                      <span>Chapter 1-2</span>
                      <span>~3000 words</span>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  )
}
