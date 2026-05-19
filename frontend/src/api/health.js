import http from './index'

/** 获取健康状态 */
export function getHealth(taskId) {
  return http.get(`/tasks/${taskId}/health`)
}

/** 重置健康状态 */
export function resetHealth(taskId) {
  return http.post(`/tasks/${taskId}/health/reset`)
}