import http from './index'

/** 启动运行 */
export function startRun(taskId, paramValues = {}) {
  return http.post(`/tasks/${taskId}/run`, { param_values: paramValues })
}

/** 优雅停止 */
export function stopRun(runId) {
  return http.post(`/runs/${runId}/stop`)
}

/** 强制终止 */
export function forceKillRun(runId) {
  return http.post(`/runs/${runId}/kill`)
}

/** 重启运行 */
export function restartRun(runId) {
  return http.post(`/runs/${runId}/restart`)
}

/** 运行列表 */
export function getRuns(params) {
  return http.get('/runs', { params })
}

/** 运行详情 */
export function getRun(runId) {
  return http.get(`/runs/${runId}`)
}