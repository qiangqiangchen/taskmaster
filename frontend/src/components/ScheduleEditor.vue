<template>
  <div class="schedule-editor">
    <!-- 启用开关 -->
    <div class="schedule-toggle">
      <el-switch v-model="form.enabled" active-text="启用定时调度" />
    </div>

    <template v-if="form.enabled">
      <!-- 类型选择 -->
      <div class="schedule-type">
        <el-radio-group v-model="form.schedule_type">
          <el-radio-button value="cron">
            <el-icon><Timer /></el-icon> Cron 表达式
          </el-radio-button>
          <el-radio-button value="interval">
            <el-icon><Clock /></el-icon> 固定间隔
          </el-radio-button>
        </el-radio-group>
      </div>

      <!-- Cron 模式 -->
      <template v-if="form.schedule_type === 'cron'">
        <div class="cron-section">
          <!-- 预设 -->
          <div class="cron-presets">
            <span class="preset-label">常用预设：</span>
            <el-button
              v-for="p in presets"
              :key="p.expression"
              size="small"
              :type="form.cron_expression === p.expression ? 'primary' : ''"
              @click="applyPreset(p)"
            >
              {{ p.name }}
            </el-button>
          </div>

          <!-- 表达式输入 -->
          <el-form-item label="Cron 表达式" class="cron-input-item">
            <el-input
              v-model="form.cron_expression"
              placeholder="* * * * *（分 时 日 月 周）"
              @input="onCronInput"
            >
              <template #append>
                <el-button @click="doValidateCron" :loading="validating">
                  校验
                </el-button>
              </template>
            </el-input>
            <div class="cron-hint">
              <span>格式：分 时 日 月 周</span>
              <span v-if="cronValidation" :class="['cron-result', cronValidation.valid ? 'valid' : 'invalid']">
                <el-icon><component :is="cronValidation.valid ? 'CircleCheckFilled' : 'CircleCloseFilled'" /></el-icon>
                {{ cronValidation.valid ? `下次执行: ${cronValidation.next_run_readable}` : cronValidation.error }}
              </span>
            </div>
          </el-form-item>

          <!-- 字段说明 -->
          <div class="cron-fields">
            <el-tag
              v-for="(f, i) in cronFields"
              :key="i"
              :type="f.active ? 'primary' : 'info'"
              size="small"
              effect="plain"
            >
              {{ f.label }} ({{ f.value }})
            </el-tag>
          </div>
        </div>
      </template>

      <!-- 间隔模式 -->
      <template v-if="form.schedule_type === 'interval'">
        <div class="interval-section">
          <el-form-item label="执行间隔">
            <el-input-number
              v-model="intervalValue"
              :min="1"
              :max="9999"
              controls-position="right"
              @change="onIntervalChange"
            />
            <el-select v-model="intervalUnit" style="width: 100px; margin-left: 8px" @change="onIntervalChange">
              <el-option label="秒" value="seconds" />
              <el-option label="分钟" value="minutes" />
              <el-option label="小时" value="hours" />
            </el-select>
            <span class="interval-hint">最小 10 秒</span>
          </el-form-item>
        </div>
      </template>

      <!-- 下次执行信息 -->
      <div v-if="scheduleData?.next_run_at" class="next-run-info">
        <el-icon><Clock /></el-icon>
        <span>下次执行: {{ formatDT(scheduleData.next_run_at) }}</span>
        <span v-if="scheduleData.next_run_readable" class="next-run-readable">
          ({{ scheduleData.next_run_readable }})
        </span>
      </div>

      <!-- 上次执行信息 -->
      <div v-if="scheduleData?.last_run_at" class="last-run-info">
        <el-icon><Finished /></el-icon>
        <span>上次执行: {{ formatDT(scheduleData.last_run_at) }}</span>
      </div>
    </template>

    <!-- 保存按钮 -->
    <div class="schedule-actions">
      <el-button type="primary" :loading="saving" @click="handleSave">
        保存调度配置
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getSchedule, saveSchedule, validateCron, getCronPresets } from '../api/scheduler'

const props = defineProps({
  taskId: { type: String, required: true },
})

const scheduleData = ref(null)
const presets = ref([])
const saving = ref(false)
const validating = ref(false)
const cronValidation = ref(null)
const intervalValue = ref(5)
const intervalUnit = ref('minutes')

const form = reactive({
  enabled: false,
  schedule_type: 'cron',
  cron_expression: '',
  interval_seconds: 0,
})

const cronFields = computed(() => {
  const parts = form.cron_expression.split(/\s+/)
  const labels = ['分', '时', '日', '月', '周']
  const defaults = ['0-59', '0-23', '1-31', '1-12', '0-6']
  return labels.map((label, i) => ({
    label,
    value: parts[i] || defaults[i],
    active: parts[i] && parts[i] !== '*',
  }))
})

async function loadSchedule() {
  try {
    const data = await getSchedule(props.taskId)
    scheduleData.value = data
    form.enabled = data.enabled
    form.schedule_type = data.schedule_type || 'cron'
    form.cron_expression = data.cron_expression || ''
    form.interval_seconds = data.interval_seconds || 0

    // 反推间隔显示值
    if (data.interval_seconds) {
      const sec = data.interval_seconds
      if (sec >= 3600 && sec % 3600 === 0) {
        intervalValue.value = sec / 3600
        intervalUnit.value = 'hours'
      } else if (sec >= 60 && sec % 60 === 0) {
        intervalValue.value = sec / 60
        intervalUnit.value = 'minutes'
      } else {
        intervalValue.value = sec
        intervalUnit.value = 'seconds'
      }
    }
  } catch {}
}

async function loadPresets() {
  try {
    const res = await getCronPresets()
    presets.value = res.presets || []
  } catch {}
}

function applyPreset(preset) {
  form.cron_expression = preset.expression
  cronValidation.value = null
}

let cronTimer = null
function onCronInput() {
  cronValidation.value = null
  clearTimeout(cronTimer)
  if (form.cron_expression.trim().split(/\s+/).length === 5) {
    cronTimer = setTimeout(() => doValidateCron(), 800)
  }
}

async function doValidateCron() {
  if (!form.cron_expression.trim()) return
  validating.value = true
  try {
    const res = await validateCron(props.taskId, form.cron_expression)
    cronValidation.value = res
  } catch {} finally {
    validating.value = false
  }
}

function onIntervalChange() {
  form.interval_seconds = calcSeconds()
}

function calcSeconds() {
  const v = intervalValue.value || 0
  if (intervalUnit.value === 'hours') return v * 3600
  if (intervalUnit.value === 'minutes') return v * 60
  return v
}

async function handleSave() {
  // 校验
  if (form.enabled) {
    if (form.schedule_type === 'cron' && !form.cron_expression.trim()) {
      ElMessage.warning('请输入 Cron 表达式')
      return
    }
    if (form.schedule_type === 'interval') {
      const sec = calcSeconds()
      if (sec < 10) {
        ElMessage.warning('间隔不能小于 10 秒')
        return
      }
      form.interval_seconds = sec
    }
  }

  saving.value = true
  try {
    const res = await saveSchedule(props.taskId, {
      enabled: form.enabled,
      schedule_type: form.schedule_type,
      cron_expression: form.cron_expression,
      interval_seconds: form.interval_seconds,
    })
    ElMessage.success('调度配置已保存')
    loadSchedule()
  } catch {} finally {
    saving.value = false
  }
}

function formatDT(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString('zh-CN')
}

onMounted(() => {
  loadSchedule()
  loadPresets()
})

watch(() => props.taskId, () => loadSchedule())
</script>

<style scoped>
.schedule-editor {
  padding: 8px 0;
}

.schedule-toggle {
  margin-bottom: 16px;
}

.schedule-type {
  margin-bottom: 16px;
}

.cron-section {
  padding-left: 4px;
}

.cron-presets {
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
}

.preset-label {
  font-size: 13px;
  color: #64748b;
  font-weight: 500;
  margin-right: 4px;
}

.cron-input-item :deep(.el-input-group__append) {
  padding: 0;
}

.cron-hint {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 6px;
  font-size: 12px;
  color: #94a3b8;
}

.cron-result {
  display: flex;
  align-items: center;
  gap: 4px;
  font-weight: 500;
}
.cron-result.valid { color: #22c55e; }
.cron-result.invalid { color: #ef4444; }

.cron-fields {
  display: flex;
  gap: 6px;
  margin-top: 8px;
}

.interval-section {
  padding-left: 4px;
}

.interval-hint {
  margin-left: 12px;
  font-size: 12px;
  color: #94a3b8;
}

.next-run-info, .last-run-info {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 12px;
  font-size: 13px;
  color: #1e293b;
}

.next-run-readable {
  color: #64748b;
  font-size: 12px;
}

.last-run-info {
  color: #64748b;
}

.schedule-actions {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid #e4e7ed;
}
</style>