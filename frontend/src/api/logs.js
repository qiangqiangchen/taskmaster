import http from './index'

/** 读取历史日志 */
export function getLogs(runId, params = {}) {
  return http.get(`/runs/${runId}/logs`, { params })
}

/** SSE 实时日志流地址 */
export function getLogStreamUrl(runId) {
  const token = localStorage.getItem('token')
  return `/api/runs/${runId}/logs/stream?token=${encodeURIComponent(token)}`
}

/** 下载日志文件 */
export function downloadLog(runId) {
  const token = localStorage.getItem('token')
  window.open(`/api/runs/${runId}/logs/download?token=${encodeURIComponent(token)}`, '_blank')
}