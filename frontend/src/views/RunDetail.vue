<template>
  <div class="run-detail" v-loading="loading">
    <div class="page-header">
      <div class="header-left">
        <el-button @click="$router.back()" text>
          <el-icon><ArrowLeft /></el-icon> 返回
        </el-button>
        <h2>运行详情</h2>
      </div>
      <div class="header-actions" v-if="run">
        <el-button
          v-if="run.status === 'running'"
          type="warning"
          @click="handleStop"
        >
          <el-icon><VideoPause /></el-icon> 停止
        </el-button>
        <el-button
          v-if="run.status === 'running'"
          type="danger"
          @click="handleKill"
        >
          <el-icon><CloseBold /></el-icon> 强制终止
        </el-button>
        <el-button
          v-if="['failed', 'stopped'].includes(run.status)"
          type="success"
          @click="handleRestart"
        >
          <el-icon><RefreshRight /></el-icon> 重新运行
        </el-button>
      </div>
    </div>

    <template v-if="run">
      <!-- 基本信息 -->
      <el-card shadow="never">
        <template #header>
          <div class="card-header">
            <el-icon><InfoFilled /></el-icon>
            <span>基本信息</span>
            <div class="status-badge" :class="`badge-${run.status}`">
              <span class="badge-dot"></span>
              {{ statusMap[run.status] || run.status }}
            </div>
          </div>
        </template>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="Run ID">
            <span class="mono">{{ run.run_id }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="任务">
            <el-link type="primary" @click="$router.push(`/tasks/${run.task_id}`)">
              {{ run.task_name || run.task_id }}
            </el-link>
          </el-descriptions-item>
          <el-descriptions-item label="触发方式">
            {{ triggerMap[run.trigger_type] || run.trigger_type }}
          </el-descriptions-item>
          <el-descriptions-item label="PID">
            <span class="mono">{{ run.pid ?? '—' }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="开始时间">
            {{ formatDT(run.started_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="结束时间">
            {{ formatDT(run.ended_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="耗时">
            {{ run.duration_ms ? (run.duration_ms / 1000).toFixed(2) + ' 秒' : '—' }}
          </el-descriptions-item>
          <el-descriptions-item label="退出码">
            <span :class="{ 'exit-err': run.exit_code && run.exit_code !== 0 }">
              {{ run.exit_code ?? '—' }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="最终命令" :span="2">
            <code class="command-code">{{ run.final_command || '—' }}</code>
          </el-descriptions-item>
          <el-descriptions-item label="工作目录" :span="2">
            <span class="mono">{{ run.output_dir || '—' }}</span>
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- 参数快照 -->
      <el-card shadow="never" style="margin-top: 16px" v-if="Object.keys(run.param_snapshot || {}).length">
        <template #header>
          <div class="card-header">
            <el-icon><Grid /></el-icon>
            <span>参数快照</span>
          </div>
        </template>
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item
            v-for="(val, key) in run.param_snapshot"
            :key="key"
            :label="String(key)"
          >
            <span class="mono">{{ val || '—' }}</span>
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- 进度 -->
      <el-card shadow="never" style="margin-top: 16px" v-if="run.progress">
        <template #header>
          <div class="card-header">
            <el-icon><DataLine /></el-icon>
            <span>进度</span>
          </div>
        </template>
        <el-progress
          :percentage="run.progress.percent || 0"
          :stroke-width="20"
          :text-inside="true"
          :status="run.status === 'success' ? 'success' : run.status === 'failed' ? 'exception' : ''"
          style="margin-bottom: 12px"
        />
        <el-descriptions :column="3" size="small" border>
          <el-descriptions-item label="当前/总量">
            {{ run.progress.current || 0 }} / {{ run.progress.total || 0 }}
          </el-descriptions-item>
          <el-descriptions-item label="预计剩余">
            {{ run.progress.eta_sec ? run.progress.eta_sec + ' 秒' : '—' }}
          </el-descriptions-item>
          <el-descriptions-item label="消息">
            {{ run.progress.message || '—' }}
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- 失败快照 -->
      <el-card
        shadow="never"
        style="margin-top: 16px"
        v-if="run.status === 'failed' && run.failure_summary"
      >
        <template #header>
          <div class="card-header">
            <el-icon><WarningFilled /></el-icon>
            <span style="color: #ef4444">失败快照</span>
            <el-button size="small" style="margin-left: auto" @click="copyFailureSummary">
              <el-icon><CopyDocument /></el-icon> 复制摘要
            </el-button>
          </div>
        </template>
        <div class="failure-info">
          <p><strong>退出码：</strong><span class="exit-err">{{ run.failure_summary.exit_code }}</span></p>
          <p><strong>最后日志：</strong></p>
          <pre class="failure-log">{{ (run.failure_summary.last_lines || []).join('\n') }}</pre>
        </div>
      </el-card>

      <!-- 产物文件 -->
      <el-card shadow="never" style="margin-top: 16px">
        <template #header>
          <div class="card-header">
            <el-icon><FolderOpened /></el-icon>
            <span>产物目录</span>
            <el-button
              v-if="run.output_dir"
              size="small"
              style="margin-left: auto"
              @click="openOutputDir"
            >
              <el-icon><Folder /></el-icon> 打开目录
            </el-button>
          </div>
        </template>
        <div v-if="run.output_dir">
          <span class="mono">{{ run.output_dir }}</span>
        </div>
        <el-empty v-else description="暂无产物" :image-size="48" />
      </el-card>

      <!-- 日志文件 -->
      <el-card shadow="never" style="margin-top: 16px">
        <template #header>
          <div class="card-header">
            <el-icon><Document /></el-icon>
            <span>日志文件</span>
            <el-tag
              v-if="run.log_truncated"
              type="warning"
              size="small"
              effect="plain"
              style="margin-left: 8px"
            >
              日志已截断
            </el-tag>
            <span v-if="run.log_size_bytes" class="log-size">
              {{ (run.log_size_bytes / 1024).toFixed(1) }} KB
            </span>
          </div>
        </template>
        <div v-if="run.log_path">
          <span class="mono">{{ run.log_path }}</span>
          <p class="log-hint">实时日志查看将在第 5 天实现（SSE 推送）</p>
        </div>
        <el-empty v-else description="暂无日志" :image-size="48" />
      </el-card>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getRun, stopRun, forceKillRun, restartRun } from '../api/runs'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const run = ref(null)

const statusMap = {
  running: '运行中', success: '成功', failed: '失败',
  stopped: '已停止', skipped: '已跳过', pending: '等待中',
}
const triggerMap = { manual: '手动', cron: '定时', interval: '周期', startup: '开机' }

async function loadRun() {
  loading.value = true
  try {
    run.value = await getRun(route.params.id)
  } catch {
    ElMessage.error('运行记录不存在')
    router.push('/runs')
  } finally {
    loading.value = false
  }
}

async function handleStop() {
  try {
    await stopRun(run.value.run_id)
    ElMessage.success('停止指令已发送')
    setTimeout(() => loadRun(), 1500)
  } catch {}
}

async function handleKill() {
  try {
    await ElMessageBox.confirm('强制终止会立即杀死整个进程树，可能丢失数据。确定？', '强制终止', { type: 'warning' })
    await forceKillRun(run.value.run_id)
    ElMessage.success('已强制终止')
    setTimeout(() => loadRun(), 1500)
  } catch {}
}

async function handleRestart() {
  try {
    const res = await restartRun(run.value.run_id)
    ElMessage.success('已重新运行')
    router.replace(`/runs/${res.run_id}`)
  } catch {}
}

function openOutputDir() {
  // 前端无法直接打开本地目录，提示用户路径
  ElMessage.info(`产物路径: ${run.value.output_dir}`)
}

function copyFailureSummary() {
  const summary = run.value.failure_summary
  const text = [
    `Run ID: ${run.value.run_id}`,
    `任务: ${run.value.task_name}`,
    `退出码: ${summary.exit_code}`,
    `最终命令: ${run.value.final_command}`,
    `开始: ${run.value.started_at}`,
    `结束: ${run.value.ended_at}`,
    `--- 最后日志 ---`,
    ...(summary.last_lines || []),
  ].join('\n')
  navigator.clipboard.writeText(text).then(() => {
    ElMessage.success('已复制到剪贴板')
  })
}

function formatDT(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('zh-CN')
}

onMounted(() => { loadRun() })

// 路由参数变化时重新加载（重新运行场景）
watch(() => route.params.id, (newId, oldId) => {
  if (newId && newId !== oldId) {
    run.value = null
    loadRun()
  }
})
</script>

<style scoped>
.run-detail { max-width: 1200px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.header-left { display: flex; align-items: center; gap: 12px; }
.header-left h2 { margin: 0; font-size: 20px; color: #1e293b; }
.header-actions { display: flex; gap: 8px; }

.card-header { display: flex; align-items: center; gap: 8px; font-weight: 600; color: #1e293b; }

.mono { font-family: 'Cascadia Code','Consolas',monospace; font-size: 13px; color: #475569; }
.command-code {
  font-family: 'Cascadia Code','Consolas',monospace; font-size: 13px;
  background: #f1f5f9; padding: 4px 8px; border-radius: 4px;
  display: inline-block; max-width: 100%; word-break: break-all;
}
.exit-err { color: #ef4444; font-weight: 600; }

.status-badge {
  margin-left: auto; display: flex; align-items: center; gap: 6px;
  padding: 4px 12px; border-radius: 12px; font-size: 13px; font-weight: 500;
}
.badge-dot { width: 8px; height: 8px; border-radius: 50%; }
.badge-running { background: #f0fdf4; color: #22c55e; }
.badge-running .badge-dot { background: #22c55e; box-shadow: 0 0 6px rgba(34,197,94,0.5); }
.badge-success { background: #f0fdf4; color: #22c55e; }
.badge-success .badge-dot { background: #22c55e; }
.badge-failed { background: #fef2f2; color: #ef4444; }
.badge-failed .badge-dot { background: #ef4444; }
.badge-stopped { background: #f8fafc; color: #94a3b8; }
.badge-stopped .badge-dot { background: #94a3b8; }
.badge-skipped { background: #fffbeb; color: #f59e0b; }
.badge-skipped .badge-dot { background: #f59e0b; }

.failure-info p { margin: 0 0 8px; font-size: 14px; }
.failure-log {
  background: #0f172a; color: #e2e8f0; padding: 12px 16px;
  border-radius: 8px; font-family: 'Cascadia Code','Consolas',monospace;
  font-size: 12px; line-height: 1.5; max-height: 300px; overflow-y: auto;
  white-space: pre-wrap; word-break: break-all;
}

.log-size { margin-left: 8px; font-size: 12px; color: #94a3b8; font-weight: 400; }
.log-hint { margin-top: 8px; font-size: 12px; color: #94a3b8; }
</style>