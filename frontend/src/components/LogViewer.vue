<template>
  <div class="log-viewer">
    <!-- 工具栏 -->
    <div class="log-toolbar">
      <div class="toolbar-left">
        <el-button size="small" @click="loadHistory" :loading="loadingHistory">
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>
        <el-button
          v-if="status === 'running'"
          size="small"
          :type="streaming ? 'warning' : 'success'"
          @click="toggleStream"
        >
          <el-icon>
            <component :is="streaming ? 'VideoPause' : 'VideoPlay'" />
          </el-icon>
          {{ streaming ? '暂停实时' : '实时跟踪' }}
        </el-button>
      </div>
      <div class="toolbar-right">
        <el-input
          v-model="searchText"
          placeholder="搜索日志..."
          prefix-icon="Search"
          clearable
          size="small"
          style="width: 200px"
          @input="onSearch"
        />
        <el-button size="small" @click="scrollToBottom">
          <el-icon><Bottom /></el-icon> 底部
        </el-button>
        <el-button size="small" @click="handleDownload">
          <el-icon><Download /></el-icon> 下载
        </el-button>
        <el-button size="small" @click="handleCopy">
          <el-icon><CopyDocument /></el-icon> 复制
        </el-button>
      </div>
    </div>

    <!-- 日志状态指示 -->
    <div class="log-status-bar">
      <span class="line-count">共 {{ filteredLines.length }} 行</span>
      <span v-if="searchText" class="search-info">
        / 匹配 {{ matchedCount }} 行
      </span>
      <span v-if="streaming" class="stream-indicator">
        <span class="blink-dot"></span> 实时
      </span>
      <span v-if="truncated" class="truncated-info">
        日志已截断
      </span>
    </div>

    <!-- 日志内容 -->
    <div
      ref="logContainer"
      class="log-container"
      @scroll="onScroll"
    >
      <div class="log-lines">
        <div
          v-for="(line, idx) in filteredLines"
          :key="offset + idx"
          :class="['log-line', { 'log-line-match': isMatch(line) }]"
        >
          <span class="line-number">{{ offset + idx + 1 }}</span>
          <span class="line-content" v-html="highlightLine(line)"></span>
        </div>
      </div>
      <div v-if="filteredLines.length === 0" class="log-empty">
        {{ loadingHistory ? '加载中...' : '暂无日志' }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { getLogs, getLogStreamUrl, downloadLog } from '../api/logs'

const props = defineProps({
  runId: { type: String, required: true },
  status: { type: String, default: '' },
  truncated: { type: Boolean, default: false },
})

const logContainer = ref(null)
const allLines = ref([])
const offset = ref(0)
const loadingHistory = ref(false)
const streaming = ref(false)
const searchText = ref('')
const autoScroll = ref(true)
const eventSource = ref(null)

const filteredLines = computed(() => {
  if (!searchText.value) return allLines.value
  const q = searchText.value.toLowerCase()
  return allLines.value.filter(line => line.toLowerCase().includes(q))
})

const matchedCount = computed(() => {
  if (!searchText.value) return 0
  const q = searchText.value.toLowerCase()
  return allLines.value.filter(line => line.toLowerCase().includes(q)).length
})

function isMatch(line) {
  if (!searchText.value) return false
  return line.toLowerCase().includes(searchText.value.toLowerCase())
}

function highlightLine(line) {
  if (!searchText.value) return escapeHtml(line)
  const q = searchText.value
  const escaped = escapeHtml(line)
  const qEscaped = escapeHtml(q)
  const regex = new RegExp(`(${escapeRegex(qEscaped)})`, 'gi')
  return escaped.replace(regex, '<mark class="log-highlight">$1</mark>')
}

function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
  }

function escapeRegex(str) {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

// ========== 历史日志 ==========

async function loadHistory() {
  loadingHistory.value = true
  try {
    const res = await getLogs(props.runId, { offset: 0, limit: 2000, search: '' })
    allLines.value = res.lines || []
    offset.value = 0
    if (autoScroll.value) {
      nextTick(() => scrollToBottom())
    }
  } catch {} finally {
    loadingHistory.value = false
  }
}

let searchTimer = null
function onSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    if (autoScroll.value) {
      nextTick(() => scrollToBottom())
    }
  }, 300)
}

// ========== SSE 实时推送 ==========

function startStream() {
  if (eventSource.value) {
    eventSource.value.close()
  }

  const url = getLogStreamUrl(props.runId)
  const es = new EventSource(url)
  eventSource.value = es
  streaming.value = true

  es.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)

      if (data.type === 'log') {
        allLines.value.push(data.line)
        if (autoScroll.value) {
          nextTick(() => scrollToBottom())
        }
      } else if (data.type === 'end') {
        streaming.value = false
        es.close()
        eventSource.value = null
      } else if (data.type === 'timeout') {
        streaming.value = false
        es.close()
        eventSource.value = null
      }
    } catch {}
  }

  es.onerror = () => {
    streaming.value = false
    es.close()
    eventSource.value = null
  }
}

function stopStream() {
  if (eventSource.value) {
    eventSource.value.close()
    eventSource.value = null
  }
  streaming.value = false
}

function toggleStream() {
  if (streaming.value) {
    stopStream()
  } else {
    startStream()
  }
}

// ========== 滚动 ==========

function onScroll() {
  if (!logContainer.value) return
  const el = logContainer.value
  const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40
  autoScroll.value = atBottom
}

function scrollToBottom() {
  if (!logContainer.value) return
  const el = logContainer.value
  el.scrollTop = el.scrollHeight
}

// ========== 操作 ==========

function handleDownload() {
  downloadLog(props.runId)
}

function handleCopy() {
  const text = allLines.value.join('\n')
  navigator.clipboard.writeText(text).then(() => {
    ElMessage.success('已复制到剪贴板')
  }).catch(() => {
    ElMessage.error('复制失败')
  })
}

// ========== 生命周期 ==========

onMounted(async () => {
  await loadHistory()
  // 运行中的任务自动开启实时跟踪
  if (props.status === 'running') {
    startStream()
  }
})

onBeforeUnmount(() => {
  stopStream()
})

// runId 变化时重新加载
watch(() => props.runId, async (newId) => {
  if (newId) {
    stopStream()
    await loadHistory()
    if (props.status === 'running') {
      startStream()
    }
  }
})
</script>

<style scoped>
.log-viewer {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.log-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  gap: 8px;
  flex-wrap: wrap;
}

.toolbar-left, .toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.log-status-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 4px 8px;
  font-size: 12px;
  color: #94a3b8;
  border-top: 1px solid #e4e7ed;
  border-bottom: 1px solid #e4e7ed;
  background: #f8fafc;
}

.stream-indicator {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #22c55e;
  font-weight: 500;
}

.blink-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #22c55e;
  animation: blink 1s ease-in-out infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.2; }
}

.truncated-info {
  color: #f59e0b;
  font-weight: 500;
}

.log-container {
  flex: 1;
  overflow-y: auto;
  background: #0f172a;
  border-radius: 0 0 8px 8px;
  min-height: 200px;
  max-height: 500px;
  font-family: 'Cascadia Code', 'Fira Code', 'Consolas', 'Courier New', monospace;
  font-size: 12.5px;
  line-height: 1.6;
}

.log-lines {
  padding: 8px 0;
}

.log-line {
  display: flex;
  padding: 0 12px;
  transition: background 0.15s;
}

.log-line:hover {
  background: rgba(255, 255, 255, 0.04);
}

.log-line-match {
  background: rgba(250, 204, 21, 0.08);
}

.line-number {
  color: #475569;
  min-width: 50px;
  text-align: right;
  padding-right: 16px;
  user-select: none;
  flex-shrink: 0;
}

.line-content {
  color: #e2e8f0;
  white-space: pre-wrap;
  word-break: break-all;
}

.log-empty {
  color: #64748b;
  text-align: center;
  padding: 40px;
}

.search-info {
  color: #60a5fa;
}

:deep(.log-highlight) {
  background: rgba(250, 204, 21, 0.3);
  color: #fbbf24;
  padding: 0 2px;
  border-radius: 2px;
}
</style>