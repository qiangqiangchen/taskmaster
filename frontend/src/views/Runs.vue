<template>
  <div class="runs-page">
    <div class="page-header">
      <h2>运行历史</h2>
    </div>

    <!-- 筛选 -->
    <el-card shadow="never" class="filter-card">
      <div class="filter-row">
        <el-select
          v-model="filters.status"
          placeholder="状态"
          clearable
          style="width: 140px"
          @change="loadRuns"
        >
          <el-option label="运行中" value="running" />
          <el-option label="成功" value="success" />
          <el-option label="失败" value="failed" />
          <el-option label="已停止" value="stopped" />
          <el-option label="已跳过" value="skipped" />
        </el-select>
        <el-select
          v-model="filters.trigger_type"
          placeholder="触发方式"
          clearable
          style="width: 140px"
          @change="loadRuns"
        >
          <el-option label="手动" value="manual" />
          <el-option label="定时" value="cron" />
          <el-option label="周期" value="interval" />
          <el-option label="开机" value="startup" />
        </el-select>
        <el-button @click="loadRuns" text>
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>
      </div>
    </el-card>

    <!-- 列表 -->
    <el-card shadow="never" style="margin-top: 16px">
      <el-table :data="runList" v-loading="loading" empty-text="暂无运行记录">
        <el-table-column label="Run ID" width="280">
          <template #default="{ row }">
            <span class="mono clickable" @click="$router.push(`/runs/${row.run_id}`)">
              {{ row.run_id.slice(0, 8) }}...
            </span>
          </template>
        </el-table-column>
        <el-table-column label="任务" min-width="160">
          <template #default="{ row }">
            <span>{{ row.task_name || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110" align="center">
          <template #default="{ row }">
            <div class="status-cell">
              <span :class="['status-dot', `dot-${row.status}`]"></span>
              <span :class="[`st-${row.status}`]">{{ statusMap[row.status] || row.status }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="触发" width="90" align="center">
          <template #default="{ row }">{{ triggerMap[row.trigger_type] || row.trigger_type }}</template>
        </el-table-column>
        <el-table-column label="开始时间" width="180">
          <template #default="{ row }">{{ formatDT(row.started_at) }}</template>
        </el-table-column>
        <el-table-column label="耗时" width="110">
          <template #default="{ row }">
            {{ row.duration_ms ? (row.duration_ms / 1000).toFixed(1) + 's' : '—' }}
          </template>
        </el-table-column>
        <el-table-column label="退出码" width="90" align="center">
          <template #default="{ row }">
            <span :class="{ 'exit-err': row.exit_code && row.exit_code !== 0 }">
              {{ row.exit_code ?? '—' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140" align="center" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="$router.push(`/runs/${row.run_id}`)">
              详情
            </el-button>
            <el-button
              v-if="row.status === 'running'"
              size="small"
              type="warning"
              @click.stop="handleStop(row)"
            >
              停止
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="loadRuns"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getRuns, stopRun } from '../api/runs'

const loading = ref(false)
const runList = ref([])
const page = ref(1)
const pageSize = 20
const total = ref(0)

const filters = reactive({ status: null, trigger_type: null })

const statusMap = {
  running: '运行中', success: '成功', failed: '失败',
  stopped: '已停止', skipped: '已跳过', pending: '等待中',
}
const triggerMap = { manual: '手动', cron: '定时', interval: '周期', startup: '开机' }

async function loadRuns() {
  loading.value = true
  try {
    const res = await getRuns({ page: page.value, page_size: pageSize, ...filters })
    runList.value = res.items || []
    total.value = res.total || 0
  } catch {} finally { loading.value = false }
}

async function handleStop(row) {
  try {
    await stopRun(row.run_id)
    ElMessage.success('停止指令已发送')
    setTimeout(() => loadRuns(), 2000)
  } catch {}
}

function formatDT(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('zh-CN')
}

onMounted(() => { loadRuns() })
</script>

<style scoped>
.runs-page { max-width: 1400px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-header h2 { margin: 0; font-size: 20px; color: #1e293b; }
.filter-card :deep(.el-card__body) { padding: 16px 20px; }
.filter-row { display: flex; align-items: center; gap: 12px; }

.mono { font-family: 'Cascadia Code','Consolas',monospace; font-size: 13px; color: #475569; }
.clickable { cursor: pointer; color: #409eff; }
.clickable:hover { text-decoration: underline; }

.status-cell { display: flex; align-items: center; justify-content: center; gap: 6px; }
.status-dot { width: 8px; height: 8px; border-radius: 50%; }
.dot-running { background: #22c55e; box-shadow: 0 0 6px rgba(34,197,94,0.5); }
.dot-success { background: #22c55e; }
.dot-failed { background: #ef4444; }
.dot-stopped { background: #94a3b8; }
.dot-skipped { background: #f59e0b; }
.dot-pending { background: #3b82f6; }

.st-running { color: #22c55e; font-size: 13px; }
.st-success { color: #22c55e; font-size: 13px; }
.st-failed { color: #ef4444; font-size: 13px; }
.st-stopped { color: #94a3b8; font-size: 13px; }
.st-skipped { color: #f59e0b; font-size: 13px; }
.st-pending { color: #3b82f6; font-size: 13px; }

.exit-err { color: #ef4444; font-weight: 600; }

.pagination-wrap { display: flex; justify-content: flex-end; margin-top: 16px; }
</style>