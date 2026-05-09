<template>
  <div class="settings-page">
    <div class="page-header">
      <h2>系统设置</h2>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-row" v-if="stats">
      <el-card shadow="never" class="stat-card">
        <div class="stat-icon tasks-icon"><el-icon :size="26"><List /></el-icon></div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.total_tasks }}</div>
          <div class="stat-label">总任务数</div>
        </div>
      </el-card>
      <el-card shadow="never" class="stat-card">
        <div class="stat-icon enabled-icon"><el-icon :size="26"><CircleCheckFilled /></el-icon></div>
        <div class="stat-info">
          <div class="stat-value success">{{ stats.enabled_tasks }}</div>
          <div class="stat-label">已启用</div>
        </div>
      </el-card>
      <el-card shadow="never" class="stat-card">
        <div class="stat-icon total-icon"><el-icon :size="26"><DataLine /></el-icon></div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.total_runs }}</div>
          <div class="stat-label">总运行次数</div>
        </div>
      </el-card>
      <el-card shadow="never" class="stat-card">
        <div class="stat-icon running-icon"><el-icon :size="26"><VideoPlay /></el-icon></div>
        <div class="stat-info">
          <div class="stat-value running">{{ stats.running_runs }}</div>
          <div class="stat-label">运行中</div>
        </div>
      </el-card>
      <el-card shadow="never" class="stat-card">
        <div class="stat-icon failed-icon"><el-icon :size="26"><CircleCloseFilled /></el-icon></div>
        <div class="stat-info">
          <div class="stat-value failed">{{ stats.failed_runs_24h }}</div>
          <div class="stat-label">24h 失败</div>
        </div>
      </el-card>
    </div>

    <!-- 设置表单 -->
    <el-card shadow="never" style="margin-top: 20px">
      <template #header>
        <div class="card-header">
          <el-icon><Setting /></el-icon>
          <span>全局配置</span>
        </div>
      </template>
      <el-form label-width="180px" v-loading="loading">
        <el-form-item label="日志文件大小上限">
          <el-input-number v-model="form.log_max_size_mb" :min="10" :max="1000" controls-position="right" />
          <span class="hint">MB。超过后日志截断</span>
        </el-form-item>

        <el-form-item label="最大并发运行数">
          <el-input-number v-model="form.max_concurrent_runs" :min="1" :max="50" controls-position="right" />
          <span class="hint">同时运行的任务实例上限</span>
        </el-form-item>

        <el-form-item label="默认停止超时">
          <el-input-number v-model="form.default_stop_timeout" :min="1" :max="60" controls-position="right" />
          <span class="hint">秒。优雅停止后的等待时间</span>
        </el-form-item>

        <el-form-item label="守护检查间隔">
          <el-input-number v-model="form.daemon_check_interval" :min="5" :max="60" controls-position="right" />
          <span class="hint">秒。守护管理器检查失败实例的间隔</span>
        </el-form-item>
      </el-form>

      <div class="form-actions">
        <el-button type="primary" :loading="saving" @click="handleSave">
          保存设置
        </el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getSettings, updateSettings, getSystemStats } from '../api/settings'

const loading = ref(false)
const saving = ref(false)
const stats = ref(null)

const form = reactive({
  log_max_size_mb: 100,
  max_concurrent_runs: 10,
  default_stop_timeout: 5,
  daemon_check_interval: 10,
})

async function loadData() {
  loading.value = true
  try {
    const [settings, statsData] = await Promise.all([
      getSettings(),
      getSystemStats(),
    ])
    stats.value = statsData
    if (settings.log_max_size_mb) form.log_max_size_mb = parseInt(settings.log_max_size_mb)
    if (settings.max_concurrent_runs) form.max_concurrent_runs = parseInt(settings.max_concurrent_runs)
    if (settings.default_stop_timeout) form.default_stop_timeout = parseInt(settings.default_stop_timeout)
    if (settings.daemon_check_interval) form.daemon_check_interval = parseInt(settings.daemon_check_interval)
  } catch {} finally {
    loading.value = false
  }
}

async function handleSave() {
  saving.value = true
  try {
    await updateSettings({
      log_max_size_mb: String(form.log_max_size_mb),
      max_concurrent_runs: String(form.max_concurrent_runs),
      default_stop_timeout: String(form.default_stop_timeout),
      daemon_check_interval: String(form.daemon_check_interval),
    })
    ElMessage.success('设置已保存')
  } catch {} finally {
    saving.value = false
  }
}

onMounted(() => loadData())
</script>

<style scoped>
.settings-page {}
.page-header { margin-bottom: 20px; }
.page-header h2 { margin: 0; font-size: 20px; color: #1e293b; }

.stats-row {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 16px;
}

.stat-card {
  text-align: center;
}

.stat-card :deep(.el-card__body) {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
}

.stat-icon {
  width: 50px; height: 50px; border-radius: 12px;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.tasks-icon  { background: #eff6ff; color: #3b82f6; }
.enabled-icon { background: #f0fdf4; color: #22c55e; }
.total-icon   { background: #f1f5f9; color: #64748b; }
.running-icon { background: #f0fdf4; color: #22c55e; }
.failed-icon  { background: #fef2f2; color: #ef4444; }

.stat-info { flex: 1; min-width: 0; }
.stat-value { font-size: 26px; font-weight: 700; color: #0f172a; line-height: 1.2; }
.stat-value.success { color: #22c55e; }
.stat-value.running { color: #22c55e; }
.stat-value.failed  { color: #ef4444; }
.stat-label { font-size: 12px; color: #94a3b8; margin-top: 4px; }

.form-actions {
  padding-top: 20px;
  border-top: 1px solid #f1f5f9;
  display: flex;
  justify-content: flex-end;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #1e293b;
}

.stat-value.running { color: #22c55e; }
.stat-value.failed { color: #ef4444; }

.stat-label {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 4px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: #1e293b;
}

.hint {
  margin-left: 12px;
  font-size: 12px;
  color: #94a3b8;
}

.form-actions {
  padding-top: 16px;
  border-top: 1px solid #e4e7ed;
  display: flex;
  justify-content: flex-end;
}
</style>