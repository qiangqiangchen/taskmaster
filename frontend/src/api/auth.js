import http from './index'

/** 登录 */
export function login(data) {
  return http.post('/auth/login', data).then(res => {
    localStorage.setItem('token', res.token)
    localStorage.setItem('username', data.username)
    return res
  })
}

/** 登出 */
export function logout() {
  return http.post('/auth/logout')
}

/** 获取当前用户 */
export function getMe() {
  return http.get('/auth/me')
}

/** 修改密码 */
export function changePassword(data) {
  return http.put('/auth/password', data)
}