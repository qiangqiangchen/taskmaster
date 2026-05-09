import http from './index'

/** 获取仪表盘数据 */
export function getDashboardStats() {
  return http.get('/dashboard/stats')
}

/** 获取最近运行 */
export function getRecentRuns(limit = 10) {
  return http.get('/dashboard/recent-runs', { params: { limit } })
}