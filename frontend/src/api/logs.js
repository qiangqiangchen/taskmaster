import http from './index'

/** 获取日志 */
export function getLogs(runId, params) {
  return http.get(`/runs/${runId}/logs`, {
    params: {
      offset: params?.offset ?? 0,
      limit: params?.limit ?? 2000,
      search: params?.search ?? '',
    }
  }).then(res => {
    // 后端返回 {lines: [...], total: N}，转为 {content: "..."}
    if (res.lines) {
      return { content: res.lines.join('\n'), total_lines: res.total }
    }
    return res
  })
}