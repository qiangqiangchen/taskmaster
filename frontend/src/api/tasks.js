import http from './index'

/** 获取任务列表 */
export function getTasks(params) {
  return http.get('/tasks', { params })
}

/** 获取任务详情 */
export function getTask(taskId) {
  return http.get(`/tasks/${taskId}`)
}

/** 新建任务 */
export function createTask(data) {
  return http.post('/tasks', data)
}

/** 更新任务 */
export function updateTask(taskId, data) {
  return http.put(`/tasks/${taskId}`, data)
}

/** 删除任务 */
export function deleteTask(taskId) {
  return http.delete(`/tasks/${taskId}`)
}

/** 启用/停用切换 */
export function toggleTask(taskId) {
  return http.post(`/tasks/${taskId}/toggle`)
}

/** 复制为新任务 */
export function copyTask(taskId) {
  return http.post(`/tasks/${taskId}/copy`)
}

/** 上传脚本文件 */
export function uploadScript(taskId, file) {
  const formData = new FormData()
  formData.append('file', file)
  return http.post(`/tasks/${taskId}/upload`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}