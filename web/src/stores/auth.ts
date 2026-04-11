import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi, userApi, type User } from '../api'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const token = ref<string | null>(localStorage.getItem('access_token'))
  const loading = ref(false)
  const error = ref<string | null>(null)

  const isAuthenticated = computed(() => !!token.value && !!user.value)

  async function login(username: string, password: string) {
    loading.value = true
    error.value = null
    try {
      const res = await authApi.login(username, password)
      token.value = res.data.access_token
      localStorage.setItem('access_token', res.data.access_token)

      // Fetch user info
      const userRes = await userApi.getMe()
      user.value = userRes.data
      localStorage.setItem('user', JSON.stringify(user.value))

      return true
    } catch (e: any) {
      error.value = e.response?.data?.detail || '登录失败'
      return false
    } finally {
      loading.value = false
    }
  }

  async function register(username: string, email: string, password: string) {
    loading.value = true
    error.value = null
    try {
      const res = await authApi.register(username, email, password)
      token.value = res.data.access_token
      localStorage.setItem('access_token', res.data.access_token)

      // Fetch user info
      const userRes = await userApi.getMe()
      user.value = userRes.data
      localStorage.setItem('user', JSON.stringify(user.value))

      return true
    } catch (e: any) {
      error.value = e.response?.data?.detail || '注册失败'
      return false
    } finally {
      loading.value = false
    }
  }

  async function fetchUser() {
    if (!token.value) return
    try {
      const res = await userApi.getMe()
      user.value = res.data
      localStorage.setItem('user', JSON.stringify(user.value))
    } catch {
      logout()
    }
  }

  function logout() {
    user.value = null
    token.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('user')
  }

  function initAuth() {
    const storedToken = localStorage.getItem('access_token')
    const storedUser = localStorage.getItem('user')
    if (storedToken && storedUser) {
      token.value = storedToken
      try {
        user.value = JSON.parse(storedUser)
      } catch {
        logout()
      }
    }
  }

  return {
    user,
    token,
    loading,
    error,
    isAuthenticated,
    login,
    register,
    logout,
    fetchUser,
    initAuth,
  }
})
