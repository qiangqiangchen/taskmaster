import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '../router'

const http = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// 请求拦截
http.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截
http.interceptors.response.use(
  response => response.data,
  error => {
    const status = error.response?.status
    const msg = error.response?.data?.detail || '请求失败'

    const isLoginRequest = error.config?.url?.includes('/auth/login')

    if (status === 401 && !isLoginRequest) {
      localStorage.removeItem('token')
      localStorage.removeItem('username')
      router.push('/login')
      ElMessage.error('登录已过期，请重新登录')
    } else if (status === 401 && isLoginRequest) {
      ElMessage.error(msg)
    } else if (status && msg) {
      ElMessage.error(msg)
    }

    return Promise.reject(error)
  }
)

export default http