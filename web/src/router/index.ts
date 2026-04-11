import { createRouter, createWebHistory, type NavigationGuardNext, type RouteLocationNormalized } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import BookDetailView from '../views/BookDetailView.vue'
import LoginView from '../views/LoginView.vue'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
      meta: { requiresAuth: true },
    },
    {
      path: '/books/:id',
      name: 'book-detail',
      component: BookDetailView,
      meta: { requiresAuth: true },
    },
    {
      path: '/login',
      name: 'login',
      component: LoginView,
      meta: { guest: true },
    },
  ],
})

// Navigation guard
router.beforeEach((to: RouteLocationNormalized, from: RouteLocationNormalized, next: NavigationGuardNext) => {
  const authStore = useAuthStore()
  authStore.initAuth()

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next('/login')
  } else if (to.meta.guest && authStore.isAuthenticated) {
    next('/')
  } else {
    next()
  }
})

export default router
