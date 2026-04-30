import { defineStore } from 'pinia'
import { ref } from 'vue'
import { login as loginApi, logout as logoutApi } from '../api/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const username = ref(localStorage.getItem('username') || '')

  async function login(user, pass) {
    const res = await loginApi({ username: user, password: pass })
    token.value = res.access_token
    username.value = res.username
    localStorage.setItem('token', res.access_token)
    localStorage.setItem('username', res.username)
    return res
  }

  async function logout() {
    try {
      await logoutApi()
    } catch {
      // 忽略登出接口错误
    }
    token.value = ''
    username.value = ''
    localStorage.removeItem('token')
    localStorage.removeItem('username')
  }

  function isLoggedIn() {
    return !!token.value
  }

  return { token, username, login, logout, isLoggedIn }
})