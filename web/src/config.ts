// 后端 API 和 WebSocket 配置
// 这些变量在构建时从 .env 注入

export interface AppConfig {
  apiBaseUrl: string
  wsUrl: string
}

const config: AppConfig = {
  // API 请求基础地址 - 使用相对路径通过 Vite proxy
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || '/api',

  // WebSocket 地址
  // 空字符串表示使用相对路径（通过 Vite proxy）
  // 或者可以设置为完整地址如 'ws://localhost:8005/api'
  wsUrl: import.meta.env.VITE_WS_URL || '',
}

export default config