import http from './index'

/** 获取设置 */
export function getSettings() {
  return http.get('/settings')
}

/** 更新设置 */
export function updateSettings(settings) {
  return http.put('/settings', { settings })
}

/** 获取系统统计 */
export function getSystemStats() {
  return http.get('/settings/stats')
}