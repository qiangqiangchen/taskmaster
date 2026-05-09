<template>
  <div class="audit-page">
    <div class="page-header">
      <h2>审计日志</h2>
    </div>

    <el-card shadow="never" class="filter-card">
      <div class="filter-row">
        <el-select v-model="filters.action" placeholder="操作类型" clearable style="width: 180px" @change="loadLogs">
          <el-option label="创建任务" value="create_task" />
          <el-option label="更新任务" value="update_task" />
          <el-option label="删除任务" value="delete_task" />
          <el-option label="启用任务" value="enable_task" />
          <el-option label="停用任务" value="disable_task" />
          <el-option label="复制任务" value="duplicate_task" />
          <el-option label="启动运行" value="start_run" />
          <el-option label="停止运行" value="stop_run" />
          <el-option label="强制终止" value="force_kill_run" />
          <el-option label="重启运行" value="restart_run" />
          <el-option label="更新参数" value="update_params" />
          <el-option label="更新调度" value="update_schedule" />
          <el-option label="更新设置" value="update_settings" />
          <el-option label="用户登录" value="login" />
        </el-select>
        <el-input v-model="filters.username" placeholder="用户名" clearable style="width: 140px" @clear="loadLogs" @keyup.enter="loadLogs" />
        <el-button @click="loadLogs" text>
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>
      </div>
    </el-card>

    <el-card shadow="never" style="margin-top: 16px">
      <el-table :data="logs" v-loading="loading" empty-text="暂无审计记录">
        <el-table-column label="时间" width="180">
          <template #default="{ row }">{{ formatDT(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="用户" width="120">
          <template #default="{ row }">{{ row.username || '—' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-tag :type="actionTagType(row.action)" size="small" effect="light">
              {{ actionLabel(row.action) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="目标类型" width="100" align="center">
          <template #default="{ row }">{{ targetLabel(row.target_type) }}</template>
        </el-table-column>
        <el-table-column label="目标" min-width="200">
          <template #default="{ row }">
            <span v-if="row.target_type === 'task'" class="mono clickable" @click="goTarget(row)">
              {{ row.detail?.task_name || row.target_id?.slice(0, 8) || '—' }}
            </span>
            <span v-else-if="row.target_type === 'run'" class="mono clickable" @click="goTarget(row)">
              {{ row.target_id?.slice(0, 8) || '—' }}...
            </span>
            <span v-else class="mono">{{ row.target_id || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="详情" min-width="200">
          <template #default="{ row }">
            <span class="detail-text">{{ formatDetail(row.detail) }}</span>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="loadLogs"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getAuditLogs } from '../api/audit'

const router = useRouter()
const loading = ref(false)
const logs = ref([])
const page = ref(1)
const pageSize = 20
const total = ref(0)

const filters = reactive({ action: '', username: '' })

const actionLabels = {
  create_task: '创建任务', update_task: '更新任务', delete_task: '删除任务',
  enable_task: '启用任务', disable_task: '停用任务', duplicate_task: '复制任务',
  start_run: '启动运行', stop_run: '停止运行', force_kill_run: '强制终止',
  restart_run: '重启运行', update_params: '更新参数', update_schedule: '更新调度',
  update_settings: '更新设置', login: '用户登录',
}

const actionTagTypes = {
  create_task: 'success', delete_task: 'danger', update_task: '',
  enable_task: 'success', disable_task: 'warning', duplicate_task: 'info',
  start_run: 'success', stop_run: 'warning', force_kill_run: 'danger',
  restart_run: '', update_params: 'info', update_schedule: 'info',
  update_settings: 'info', login: '',
}

function actionLabel(action) { return actionLabels[action] || action }
function actionTagType(action) { return actionTagTypes[action] || '' }

function targetLabel(type) {
  const map = { task: '任务', run: '运行', system: '系统', user: '用户' }
  return map[type] || type || '—'
}

function formatDT(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('zh-CN')
}

function formatDetail(detail) {
  if (!detail) return '—'
  if (typeof detail === 'string') return detail
  const parts = []
  if (detail.task_name) parts.push(detail.task_name)
  if (detail.old_run_id) parts.push(`旧run: ${detail.old_run_id.slice(0, 8)}`)
  if (detail.new_run_id) parts.push(`新run: ${detail.new_run_id.slice(0, 8)}`)
  if (detail.source_task_id) parts.push(`源: ${detail.source_task_id.slice(0, 8)}`)
  return parts.length ? parts.join(' | ') : JSON.stringify(detail)
}

function goTarget(row) {
  if (row.target_type === 'task') router.push(`/tasks/${row.target_id}`)
  else if (row.target_type === 'run') router.push(`/runs/${row.target_id}`)
}

async function loadLogs() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize, ...filters }
    const res = await getAuditLogs(params)
    logs.value = (res.items || []).map(l => ({
      ...l,
      detail: typeof l.detail === 'string' ? JSON.parse(l.detail || '{}') : (l.detail || {}),
    }))
    total.value = res.total || 0
  } catch {} finally {
    loading.value = false
  }
}

onMounted(() => loadLogs())
</script>

<style scoped>
.audit-page {  }
.page-header { margin-bottom: 20px; }
.page-header h2 { margin: 0; font-size: 20px; color: #1e293b; }

.filter-card :deep(.el-card__body) { padding: 14px 20px; }
.filter-row { display: flex; align-items: center; gap: 12px; }

.detail-text {
  font-size: 12px;
  color: #64748b;
  font-family: 'Cascadia Code', 'Consolas', monospace;
}

.mono { font-family: 'Cascadia Code','Consolas',monospace; font-size: 13px; color: #475569; }
.clickable { cursor: pointer; color: #409eff; }
.clickable:hover { text-decoration: underline; }

.detail-text { font-size: 12px; color: #64748b; }

.pagination-wrap { display: flex; justify-content: flex-end; margin-top: 16px; }
</style>