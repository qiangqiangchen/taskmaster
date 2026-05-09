import http from './index'

/** 获取调度配置 */
export function getSchedule(taskId) {
  return http.get(`/tasks/${taskId}/schedule`)
}

/** 保存调度配置 */
export function saveSchedule(taskId, data) {
  return http.put(`/tasks/${taskId}/schedule`, data)
}

/** 校验 cron 表达式 */
export function validateCron(taskId, expression) {
  return http.post(`/tasks/${taskId}/schedule/validate-cron`, { expression })
}

/** 获取 cron 预设 */
export function getCronPresets() {
  return http.get('/tasks/scheduler/presets')
}