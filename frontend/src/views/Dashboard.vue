<template>
  <div class="dashboard-page">
    <div class="page-header">
      <h2>仪表盘</h2>
      <el-button @click="loadData" text>
        <el-icon><Refresh /></el-icon> 刷新
      </el-button>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-row">
      <el-card shadow="never" class="stat-card">
        <div class="stat-icon tasks-icon">
          <el-icon :size="26"><List /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stats?.total_tasks || 0 }}</div>
          <div class="stat-label">总任务</div>
        </div>
      </el-card>
      <el-card shadow="never" class="stat-card">
        <div class="stat-icon running-icon">
          <el-icon :size="26"><VideoPlay /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value running">{{ stats?.running_runs || 0 }}</div>
          <div class="stat-label">运行中</div>
        </div>
      </el-card>
      <el-card shadow="never" class="stat-card">
        <div class="stat-icon success-icon">
          <el-icon :size="26"><CircleCheckFilled /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value success">{{ stats?.success_rate || 0 }}%</div>
          <div class="stat-label">成功率</div>
        </div>
      </el-card>
      <el-card shadow="never" class="stat-card">
        <div class="stat-icon failed-icon">
          <el-icon :size="26"><CircleCloseFilled /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value failed">{{ stats?.failed_24h || 0 }}</div>
          <div class="stat-label">24h 失败</div>
        </div>
      </el-card>
      <el-card shadow="never" class="stat-card">
        <div class="stat-icon total-icon">
          <el-icon :size="26"><DataLine /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stats?.total_runs || 0 }}</div>
          <div class="stat-label">总运行</div>
        </div>
      </el-card>
    </div>

    <!-- 最近运行 -->
    <el-card shadow="never" style="margin-top: 24px">
      <template #header>
        <div class="card-header">
          <el-icon><VideoPlay /></el-icon>
          <span>最近运行</span>
          <el-button text type="primary" style="margin-left: auto" @click="$router.push('/runs')">
            查看全部 →
          </el-button>
        </div>
      </template>
      <el-table :data="recentRuns" v-loading="loading" empty-text="暂无运行记录">
        <el-table-column label="任务名称" min-width="180">
          <template #default="{ row }">
            <span class="clickable" @click="$router.push(`/tasks/${row.task_id}`)">
              {{ row.task_name || '—' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110" align="center">
          <template #default="{ row }">
            <span class="status-dot" :class="row.status"></span>
            <el-tag :type="statusTagType(row.status)" size="small" effect="light">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="触发方式" width="100" align="center">
          <template #default="{ row }">{{ triggerLabel(row.trigger_type) }}</template>
        </el-table-column>
        <el-table-column label="开始时间" width="180">
          <template #default="{ row }">{{ formatDT(row.started_at) }}</template>
        </el-table-column>
        <el-table-column label="耗时" width="120" align="right">
          <template #default="{ row }">
            <span v-if="row.duration_ms" class="mono">{{ formatDuration(row.duration_ms) }}</span>
            <span v-else style="color: #cbd5e1">—</span>
          </template>
        </el-table-column>
        <el-table-column label="退出码" width="80" align="center">
          <template #default="{ row }">
            <span v-if="row.exit_code != null" :class="['mono', row.exit_code !== 0 ? 'exit-err' : 'exit-ok']">
              {{ row.exit_code }}
            </span>
            <span v-else style="color: #cbd5e1">—</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80" align="center">
          <template #default="{ row }">
            <el-button v-if="row.status !== 'skipped'" size="small" text type="primary"
              @click="$router.push(`/runs/${row.run_id}`)">详情</el-button>
            <span v-else style="color: #cbd5e1">—</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getDashboardStats, getRecentRuns } from '../api/dashboard'

const loading = ref(false)
const stats = ref(null)
const recentRuns = ref([])

const statusMap = {
  running: '运行中', success: '成功', failed: '失败',
  stopped: '已停止', skipped: '已跳过', pending: '等待中',
}
const statusTagMap = {
  running: '', success: 'success', failed: 'danger',
  stopped: 'info', skipped: 'warning', pending: 'info',
}
const triggerMap = { manual: '手动', cron: '定时', interval: '周期', startup: '开机', daemon_restart: '守护' }

function statusLabel(s) { return statusMap[s] || s }
function statusTagType(s) { return statusTagMap[s] || 'info' }
function triggerLabel(t) { return triggerMap[t] || t }

function formatDT(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('zh-CN')
}

function formatDuration(ms) {
  const sec = ms / 1000
  if (sec < 60) return `${sec.toFixed(1)}s`
  const min = Math.floor(sec / 60)
  return `${min}m ${(sec % 60).toFixed(0)}s`
}

async function loadData() {
  loading.value = true
  try {
    const [statsData, runsData] = await Promise.all([
      getDashboardStats(),
      getRecentRuns(10),
    ])
    stats.value = statsData
    recentRuns.value = runsData.items || []
  } catch {} finally {
    loading.value = false
  }
}

onMounted(() => loadData())
</script>

<style scoped>
.stats-row {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 16px;
}

.stat-card :deep(.el-card__body) {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
}

.stat-icon {
  width: 50px;
  height: 50px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.tasks-icon  { background: #eff6ff; color: #3b82f6; }
.running-icon { background: #f0fdf4; color: #22c55e; }
.success-icon { background: #f0fdf4; color: #22c55e; }
.failed-icon  { background: #fef2f2; color: #ef4444; }
.total-icon   { background: #f1f5f9; color: #64748b; }

.stat-info { flex: 1; min-width: 0; }

.stat-value {
  font-size: 26px;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.2;
}
.stat-value.running { color: #22c55e; }
.stat-value.success { color: #22c55e; }
.stat-value.failed  { color: #ef4444; }

.stat-label {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 4px;
}

.exit-ok  { color: #22c55e; }
.exit-err { color: #ef4444; font-weight: 600; }
</style>