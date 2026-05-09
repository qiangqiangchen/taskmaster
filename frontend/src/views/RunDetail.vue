<template>
  <div class="run-detail" v-loading="loading">
    <!-- 顶部导航 -->
    <div class="page-header">
      <div class="header-left">
        <el-button text @click="$router.back()">
          <el-icon><ArrowLeft /></el-icon> 返回
        </el-button>
        <h2 v-if="run">
          <span class="mono">{{ run.run_id?.slice(0, 8) }}...</span>
          <span class="run-task-name" v-if="run.task_name"> — {{ run.task_name }}</span>
        </h2>
      </div>
      <div class="header-actions" v-if="run">
        <el-tag v-if="run.trigger_type" size="small" effect="plain" type="info">
          {{ triggerLabel(run.trigger_type) }}
        </el-tag>
        <el-button v-if="run.status === 'running'" type="warning" size="small" @click="handleStop">
          <el-icon><VideoPause /></el-icon> 停止
        </el-button>
        <el-button v-if="run.status === 'running'" type="danger" size="small" @click="handleForceKill">
          <el-icon><CloseBold /></el-icon> 强制终止
        </el-button>
        <el-button v-if="['success','failed','stopped'].includes(run.status)" type="primary" size="small" @click="handleRerun">
          <el-icon><RefreshRight /></el-icon> 重新运行
        </el-button>
      </div>
    </div>

    <template v-if="run">
      <!-- 状态概览 -->
      <el-card shadow="never">
        <div class="status-section">
          <span class="status-dot" :class="run.status"></span>
          <el-tag :type="statusTagType(run.status)" size="large" effect="light">
            {{ statusLabel(run.status) }}
          </el-tag>
          <span v-if="run.duration_ms" class="mono duration-text">
            耗时 {{ formatDuration(run.duration_ms) }}
          </span>
          <span v-if="run.exit_code != null" class="mono exit-code" :class="run.exit_code === 0 ? 'exit-ok' : 'exit-err'">
            退出码: {{ run.exit_code }}
          </span>
        </div>

        <el-descriptions :column="3" border size="small" style="margin-top: 16px">
          <el-descriptions-item label="任务名称">
            <span class="clickable" @click="$router.push(`/tasks/${run.task_id}`)">{{ run.task_name || '—' }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="触发方式">{{ triggerLabel(run.trigger_type) }}</el-descriptions-item>
          <el-descriptions-item label="工作目录">
            <span class="mono">{{ run.work_dir || '—' }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="开始时间">{{ formatDT(run.started_at) }}</el-descriptions-item>
          <el-descriptions-item label="结束时间">{{ formatDT(run.ended_at) }}</el-descriptions-item>
          <el-descriptions-item label="PID">{{ run.pid || '—' }}</el-descriptions-item>
        </el-descriptions>

        <!-- 进度 -->
        <div class="progress-section" v-if="progress && (progress.percent > 0 || progress.message)">
          <div class="section-label">运行进度</div>
          <el-progress
            :percentage="progress.percent || 0"
            :status="progressStatus"
            :stroke-width="20"
            :text-inside="true"
            style="margin-bottom: 8px"
          />
          <div class="progress-info">
            <span v-if="progress.current != null && progress.total != null">
              {{ progress.current }} / {{ progress.total }}
            </span>
            <span v-if="progress.eta_sec" class="mono" style="margin-left: 12px; color: #64748b">
              预计剩余 {{ formatDuration(progress.eta_sec * 1000) }}
            </span>
            <span v-if="progress.message" style="margin-left: 12px; color: #64748b">
              {{ progress.message }}
            </span>
          </div>
          <div class="progress-hint">
            <el-icon size="12"><InfoFilled /></el-icon>
            SDK 上报进度：<code>from progress import TaskProgress; p = TaskProgress(); p.report(percent=50, message="处理中...")</code>
          </div>
        </div>

        <!-- 命令 -->
        <div class="command-section" v-if="run.final_command">
          <div class="section-label">执行命令</div>
          <div class="command-box mono">
            <el-icon class="copy-btn" @click="copyText(run.final_command, '已复制命令')"><CopyDocument /></el-icon>
            {{ run.final_command }}
          </div>
        </div>

        <!-- 失败摘要 -->
        <div class="failure-section" v-if="run.failure_summary">
          <div class="section-label" style="color: #ef4444">失败摘要</div>
          <div class="failure-box mono">{{ run.failure_summary }}</div>
        </div>
      </el-card>

      <!-- 参数快照 -->
      <el-card shadow="never" style="margin-top: 16px" v-if="hasParams">
        <template #header>
          <div class="card-header">
            <el-icon><Document /></el-icon>
            <span>参数快照</span>
          </div>
        </template>
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item v-for="(value, key) in paramSnapshot" :key="key" :label="key">
            <span class="mono">{{ value }}</span>
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- 日志 -->
      <el-card shadow="never" style="margin-top: 16px">
        <template #header>
          <div class="card-header">
            <el-icon><Notebook /></el-icon>
            <span>运行日志</span>
            <span v-if="isStreaming" class="live-indicator">
              <span class="live-dot"></span>
              实时
            </span>
            <span v-if="logTruncated" class="truncated-warning">
              <el-icon><WarningFilled /></el-icon> 日志已截断
            </span>
            <div style="margin-left: auto; display: flex; align-items: center; gap: 6px">
              <el-input
                v-model="logSearch"
                placeholder="搜索日志..."
                prefix-icon="Search"
                clearable
                size="small"
                style="width: 150px"
              />
              <el-tooltip :content="isLive ? '暂停实时' : '实时跟踪'">
                <el-button size="small" :type="isLive ? 'success' : ''" @click="toggleLive">
                  <el-icon><VideoPlay v-if="!isLive" /><VideoPause v-else /></el-icon>
                  {{ isLive ? '暂停实时' : '实时跟踪' }}
                </el-button>
              </el-tooltip>
              <el-tooltip content="底部">
                <el-button size="small" @click="scrollToBottom">
                  <el-icon><Bottom /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip content="复制日志">
                <el-button size="small" @click="copyText(allLogContent, '已复制日志')">
                  <el-icon><CopyDocument /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip content="下载日志">
                <el-button size="small" @click="downloadLog">
                  <el-icon><Download /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip content="刷新">
                <el-button size="small" @click="loadLogs">
                  <el-icon><Refresh /></el-icon>
                </el-button>
              </el-tooltip>
            </div>
          </div>
        </template>
        <!-- 搜索匹配数 -->
        <div class="log-toolbar" v-if="logSearch">
          <span class="log-search-info">
            匹配 {{ filteredLineCount }} / {{ totalLineCount }} 行
          </span>
        </div>
        <div class="log-container" ref="logContainer" @scroll="handleLogScroll">
          <pre class="log-content mono" v-html="displayedLog"></pre>
        </div>
        <div v-if="!allLogContent && !isStreaming" class="log-empty">等待日志输出...</div>
      </el-card>

      <!-- 产物 -->
      <el-card shadow="never" style="margin-top: 16px">
        <template #header>
          <div class="card-header">
            <el-icon><FolderOpened /></el-icon>
            <span>产出文件</span>
            <div v-if="artifactBreadcrumbs.length > 0" class="breadcrumb">
              <el-button size="small" text @click="navigateArtifact('')">根目录</el-button>
              <template v-for="(crumb, idx) in artifactBreadcrumbs" :key="idx">
                <span class="breadcrumb-sep">/</span>
                <el-button size="small" text @click="navigateArtifact(crumb.path)">{{ crumb.name }}</el-button>
              </template>
            </div>
            <div style="margin-left: auto; display: flex; align-items: center; gap: 4px">
              <el-tooltip v-if="artifactOutputDir" content="复制输出路径">
                <el-button size="small" text @click="copyText(artifactOutputDir, '已复制路径')">
                  <el-icon><CopyDocument /></el-icon>
                </el-button>
              </el-tooltip>
              <el-button size="small" text @click="loadArtifacts(artifactPath)">
                <el-icon><Refresh /></el-icon>
              </el-button>
            </div>
          </div>
        </template>
        <el-table :data="artifacts" empty-text="暂无产出文件" size="small">
          <el-table-column label="文件名" min-width="200">
            <template #default="{ row }">
              <span v-if="row.is_dir" class="clickable folder-link" @click="navigateArtifact(row.path)">
                <el-icon style="margin-right: 4px; color: #f59e0b"><Folder /></el-icon>
                {{ row.name }}/
              </span>
              <span v-else class="mono file-link">
                <el-icon :style="{ marginRight: '4px', color: fileIconColor(row.extension) }">
                  <component :is="fileIconName(row.extension)" />
                </el-icon>
                {{ row.name }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="大小" width="120" align="right">
            <template #default="{ row }">
              {{ row.is_dir ? '—' : (row.size_display || formatSize(row.size)) }}
            </template>
          </el-table-column>
          <el-table-column label="修改时间" width="180">
            <template #default="{ row }">{{ formatDT(row.modified) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="140" align="center">
            <template #default="{ row }">
              <el-button v-if="!row.is_dir" size="small" text type="primary"
                @click="handleDownloadArtifact(row.path)">下载</el-button>
              <el-button size="small" text type="danger"
                @click="handleDeleteArtifact(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getRun, stopRun, forceKillRun, restartRun } from '../api/runs'
import { getLogs } from '../api/logs'
import { getArtifacts, downloadArtifactFile, deleteArtifact } from '../api/artifacts'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const run = ref(null)
const allLogContent = ref('')
const logSearch = ref('')
const autoFollow = ref(true)
const logPaused = ref(false)
const isStreaming = ref(false)
const logTruncated = ref(false)
const artifacts = ref([])
const artifactPath = ref('')
const artifactBreadcrumbs = ref([])
const artifactOutputDir = ref('')
const logContainer = ref(null)
let eventSource = null
let pendingLines = []
let flushTimer = null
let pollTimer = null

// ========== 状态映射 ==========

const statusMap = {
  running: '运行中', success: '成功', failed: '失败',
  stopped: '已停止', skipped: '已跳过', pending: '等待中',
}
const statusTagMap = {
  running: '', success: 'success', failed: 'danger',
  stopped: 'info', skipped: 'warning', pending: 'info',
}
const triggerMap = {
  manual: '手动', cron: '定时', interval: '周期',
  startup: '开机', daemon_restart: '守护', skipped: '跳过',
}

function statusLabel(s) { return statusMap[s] || s }
function statusTagType(s) { return statusTagMap[s] || 'info' }
function triggerLabel(t) { return triggerMap[t] || t }

// ========== 工具函数 ==========

function formatDT(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('zh-CN')
}

function formatDuration(ms) {
  const sec = Math.floor(ms / 1000)
  if (sec < 60) return `${sec} 秒`
  const min = Math.floor(sec / 60)
  const remainSec = sec % 60
  if (min < 60) return `${min} 分 ${remainSec} 秒`
  const hr = Math.floor(min / 60)
  const remainMin = min % 60
  return `${hr} 小时 ${remainMin} 分 ${remainSec} 秒`
}

function formatSize(bytes) {
  if (!bytes) return '—'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function copyText(text, msg) {
  if (!text) return
  navigator.clipboard.writeText(text)
  ElMessage.success(msg || '已复制')
}

function fileIconColor(ext) {
  const map = { '.py': '#3b82f6', '.json': '#22c55e', '.csv': '#f97316', '.txt': '#94a3b8', '.log': '#94a3b8', '.sh': '#22c55e', '.bat': '#3b82f6', '.exe': '#ef4444', '.md': '#6366f1' }
  return map[ext] || '#64748b'
}

function fileIconName(ext) {
  const map = { '.py': 'Document', '.exe': 'Monitor' }
  return map[ext] || 'Document'
}

// ========== 计算属性 ==========

const paramSnapshot = computed(() => {
  if (!run.value?.param_snapshot) return {}
  if (typeof run.value.param_snapshot === 'string') {
    try { return JSON.parse(run.value.param_snapshot) } catch { return {} }
  }
  return run.value.param_snapshot
})

const hasParams = computed(() => paramSnapshot.value && Object.keys(paramSnapshot.value).length > 0)

const progress = computed(() => {
  if (!run.value?.progress) return null
  const p = run.value.progress
  if (typeof p === 'string') {
    try { return JSON.parse(p) } catch { return null }
  }
  return p
})

const progressStatus = computed(() => {
  if (!progress.value) return ''
  if (run.value?.status === 'failed') return 'exception'
  if (progress.value.percent >= 100) return 'success'
  return ''
})

const isLive = computed(() => autoFollow.value && !logPaused.value && isStreaming.value)

// ========== 日志渲染 ==========

const allLines = computed(() => {
  if (!allLogContent.value) return []
  return allLogContent.value.split('\n')
})

const totalLineCount = computed(() => allLines.value.length)

const filteredLineCount = computed(() => {
  if (!logSearch.value) return totalLineCount.value
  const kw = logSearch.value.toLowerCase()
  return allLines.value.filter(l => l.toLowerCase().includes(kw)).length
})

const displayedLog = computed(() => {
  const lines = allLines.value
  if (!lines.length) return ''

  const keyword = logSearch.value ? logSearch.value.toLowerCase() : ''
  const keywordRaw = logSearch.value || ''

  let result = []
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    // 搜索过滤
    if (keyword && !line.toLowerCase().includes(keyword)) continue

    // 转义 HTML
    let escaped = line.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

    // 高亮匹配
    if (keywordRaw) {
      const regex = new RegExp(`(${keywordRaw.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi')
      escaped = escaped.replace(regex, '<span class="log-highlight">$1</span>')
    }

    const lineNum = String(i + 1).padStart(4, ' ')
    result.push(`<span class="line-num">${lineNum}</span><span class="line-sep"> │ </span>${escaped}`)
  }

  return result.join('\n')
})

// ========== 日志滚动 ==========

function scrollToBottom() {
  if (logContainer.value) {
    logContainer.value.scrollTop = logContainer.value.scrollHeight
  }
}

function handleLogScroll() {
  if (!logContainer.value) return
  const el = logContainer.value
  const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 50
  if (!atBottom && autoFollow.value) {
    autoFollow.value = false
  }
}

function toggleLive() {
  if (isLive.value) {
    // 暂停
    logPaused.value = true
    autoFollow.value = false
  } else {
    // 恢复实时跟踪
    logPaused.value = false
    autoFollow.value = true
    // 刷新暂停期间的遗漏日志
    loadLogs()
    nextTick(scrollToBottom)
  }
}

// ========== 批量刷新 ==========

function startFlushTimer() {
  if (flushTimer) return
  flushTimer = setInterval(() => {
    if (pendingLines.length > 0 && !logPaused.value) {
      allLogContent.value += (allLogContent.value ? '\n' : '') + pendingLines.join('\n')
      pendingLines = []
      if (autoFollow.value) {
        nextTick(scrollToBottom)
      }
    }
  }, 100)
}

function stopFlushTimer() {
  if (flushTimer) {
    clearInterval(flushTimer)
    flushTimer = null
  }
  if (pendingLines.length > 0) {
    allLogContent.value += (allLogContent.value ? '\n' : '') + pendingLines.join('\n')
    pendingLines = []
  }
}

// ========== 轮询降级 ==========

function startPolling() {
  if (pollTimer) return
  pollTimer = setInterval(() => {
    if (run.value?.status === 'running') {
      loadLogs()
      loadRun()
    }
  }, 2000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

// ========== 数据加载 ==========

async function loadRun() {
  loading.value = true
  try {
    run.value = await getRun(route.params.id)
    logTruncated.value = !!run.value.log_truncated
    if (run.value.status === 'running' && !eventSource && !pollTimer) {
      connectSSE()
    }
  } catch {
    ElMessage.error('运行记录不存在')
    router.push('/runs')
  } finally {
    loading.value = false
  }
}

async function loadLogs() {
  try {
    const res = await getLogs(route.params.id, { offset: 0, limit: 5000, search: '' })
    allLogContent.value = res.content || res.lines?.join('\n') || ''
    if (autoFollow.value) nextTick(scrollToBottom)
  } catch {}
}

async function loadArtifacts(path) {
  artifactPath.value = path || ''
  try {
    const res = await getArtifacts(route.params.id, { path: artifactPath.value })
    artifacts.value = res.items || res.files || []
    artifactBreadcrumbs.value = res.breadcrumbs || []
    artifactOutputDir.value = res.output_dir || ''
  } catch {}
}

function navigateArtifact(path) {
  loadArtifacts(path)
}

// ========== SSE ==========

function connectSSE() {
  if (eventSource) eventSource.close()
  stopPolling()
  isStreaming.value = true
  pendingLines = []
  startFlushTimer()

  const token = localStorage.getItem('token')
  const url = `/api/runs/${route.params.id}/logs/stream?token=${token}`
  eventSource = new EventSource(url)

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      if (data.type === 'log' && data.line) {
        if (!logPaused.value) {
          pendingLines.push(data.line)
        }
      }
      if (data.type === 'progress') {
        if (run.value) {
          run.value.progress = {
            percent: data.percent || 0,
            current: data.current,
            total: data.total,
            eta_sec: data.eta_sec,
            message: data.message || '',
          }
        }
      }
      if (data.type === 'end' || data.type === 'timeout') {
        eventSource.close()
        eventSource = null
        isStreaming.value = false
        stopFlushTimer()
        loadRun()
        loadArtifacts('')
      }
    } catch {}
  }

  eventSource.onerror = () => {
    eventSource.close()
    eventSource = null
    isStreaming.value = false
    stopFlushTimer()
    // 如果任务仍在运行，降级为轮询
    if (run.value?.status === 'running') {
      startPolling()
    } else {
      loadRun()
      loadArtifacts('')
    }
  }
}

// ========== 操作 ==========

function downloadLog() {
  const token = localStorage.getItem('token')
  window.open(`/api/runs/${route.params.id}/logs/download?token=${token}`, '_blank')
}

async function handleDownloadArtifact(path) {
  try {
    await downloadArtifactFile(route.params.id, path)
  } catch {
    ElMessage.error('下载失败')
  }
}

async function handleDeleteArtifact(row) {
  try {
    await ElMessageBox.confirm(`确定要删除「${row.name}」吗？`, '删除确认', { type: 'warning' })
    await deleteArtifact(route.params.id, row.path)
    ElMessage.success('已删除')
    loadArtifacts(artifactPath.value)
  } catch {}
}

async function handleStop() {
  try {
    await ElMessageBox.confirm('确定要优雅停止该任务吗？', '停止任务', { type: 'warning' })
    await stopRun(route.params.id)
    ElMessage.success('已发送停止信号')
    loadRun()
  } catch {}
}

async function handleForceKill() {
  try {
    await ElMessageBox.confirm('确定要强制终止该任务吗？', '强制终止', { type: 'error' })
    await forceKillRun(route.params.id)
    ElMessage.success('已强制终止')
    loadRun()
  } catch {}
}

async function handleRerun() {
  try {
    await ElMessageBox.confirm('确定要重新运行该任务吗？', '重新运行', { type: 'info' })
    const res = await restartRun(route.params.id)
    ElMessage.success('已启动新运行')
    router.push(`/runs/${res.run_id}`)
  } catch {}
}

// ========== 生命周期 ==========

onMounted(() => {
  loadRun()
  loadLogs()
  loadArtifacts('')
})

onBeforeUnmount(() => {
  if (eventSource) {
    eventSource.close()
    eventSource = null
  }
  stopFlushTimer()
  stopPolling()
})
</script>

<style scoped>
.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.header-left h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #0f172a;
  display: flex;
  align-items: center;
  gap: 4px;
}
.run-task-name {
  font-weight: 400;
  color: #64748b;
  font-size: 16px;
}
.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.status-section {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 0;
}
.duration-text {
  margin-left: 12px;
  color: #64748b;
  font-size: 13px;
}
.exit-code { margin-left: 12px; font-size: 13px; }
.exit-ok { color: #22c55e; }
.exit-err { color: #ef4444; font-weight: 600; }

.progress-section { margin-top: 16px; }
.progress-info {
  display: flex;
  align-items: center;
  font-size: 13px;
  color: #1e293b;
}
.progress-hint {
  margin-top: 8px;
  font-size: 11px;
  color: #94a3b8;
  display: flex;
  align-items: center;
  gap: 4px;
}
.progress-hint code {
  background: #f1f5f9;
  padding: 1px 4px;
  border-radius: 3px;
  font-size: 11px;
  color: #64748b;
}

.command-section { margin-top: 16px; }
.command-box {
  position: relative;
  background: #1e293b;
  color: #e2e8f0;
  padding: 12px 16px;
  padding-right: 40px;
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.5;
  word-break: break-all;
  white-space: pre-wrap;
}
.copy-btn {
  position: absolute;
  top: 10px;
  right: 10px;
  cursor: pointer;
  color: #94a3b8;
  font-size: 16px;
  transition: color 0.15s;
}
.copy-btn:hover { color: #e2e8f0; }

.failure-section { margin-top: 16px; }
.failure-box {
  background: #fef2f2;
  color: #dc2626;
  padding: 12px 16px;
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.5;
  word-break: break-all;
  white-space: pre-wrap;
}

/* 实时指示灯 */
.live-indicator {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  margin-left: 8px;
  font-size: 12px;
  font-weight: 600;
  color: #22c55e;
}
.live-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #22c55e;
  animation: live-blink 1.2s ease-in-out infinite;
}
@keyframes live-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

/* 日志截断警告 */
.truncated-warning {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-left: 8px;
  font-size: 12px;
  color: #f59e0b;
  font-weight: 500;
}

/* 日志工具栏 */
.log-toolbar {
  padding: 4px 12px;
  background: #f8fafc;
  border-bottom: 1px solid #f1f5f9;
}
.log-search-info {
  font-size: 12px;
  color: #64748b;
}

/* 日志容器 */
.log-container {
  background: #1e293b;
  border-radius: 8px;
  max-height: 500px;
  overflow-y: auto;
  padding: 0;
}
.log-content {
  margin: 0;
  padding: 12px 16px;
  color: #e2e8f0;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
}

/* 行号 */
:deep(.line-num) {
  color: #4a5568;
  user-select: none;
  display: inline-block;
  width: 3.5em;
  text-align: right;
  margin-right: 0;
}
:deep(.line-sep) {
  color: #2d3748;
  user-select: none;
}

/* 搜索高亮 */
:deep(.log-highlight) {
  background: #f59e0b;
  color: #1e293b;
  border-radius: 2px;
  padding: 0 2px;
}

.log-empty {
  text-align: center;
  padding: 40px;
  color: #94a3b8;
  font-size: 14px;
}

/* 产物 */
.folder-link {
  display: inline-flex;
  align-items: center;
  color: #3b82f6 !important;
  font-weight: 500;
}
.folder-link:hover { color: #2563eb !important; }
.file-link {
  display: inline-flex;
  align-items: center;
}
.breadcrumb {
  display: flex;
  align-items: center;
  margin-left: 12px;
  font-size: 12px;
}
.breadcrumb-sep {
  color: #cbd5e1;
  margin: 0 2px;
}
</style>