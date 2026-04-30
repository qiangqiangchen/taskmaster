import http from './index'

/** 获取参数配置 */
export function getParams(taskId) {
  return http.get(`/tasks/${taskId}/params`)
}

/** 保存参数配置 */
export function saveParams(taskId, data) {
  return http.put(`/tasks/${taskId}/params`, data)
}

/** 从模板重新解析占位符 */
export function parseParams(taskId) {
  return http.post(`/tasks/${taskId}/parse-params`)
}

/** 预览最终命令（Dry Run） */
export function renderCommand(taskId, values) {
  return http.post(`/tasks/${taskId}/render-command`, { values })
}