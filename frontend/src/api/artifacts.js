import http from './index'

/** 获取产物列表 */
export function getArtifacts(runId, params) {
  return http.get(`/runs/${runId}/artifacts`, { params })
    .then(res => {
      if (res.files) {
        return { items: res.files, breadcrumbs: res.breadcrumbs || [], output_dir: res.output_dir || '' }
      }
      return res
    })
}

/** 下载产物文件 */
export function downloadArtifactFile(runId, path) {
  const token = localStorage.getItem('token')
  const url = `/api/runs/${runId}/artifacts/download?path=${encodeURIComponent(path)}&token=${token}`
  window.open(url, '_blank')
}

/** 删除产物文件 */
export function deleteArtifact(runId, path) {
  return http.delete(`/runs/${runId}/artifacts`, { params: { path } })
}