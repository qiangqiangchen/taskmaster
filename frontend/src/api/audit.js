import http from './index'

/** 获取审计日志 */
export function getAuditLogs(params) {
  return http.get('/audit', { params })
}