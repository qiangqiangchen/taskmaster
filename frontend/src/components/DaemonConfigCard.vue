<template>
  <div class="daemon-config">
    <el-form label-width="140px" size="default">
      <el-form-item label="自动重启">
        <el-switch v-model="form.auto_restart" active-text="崩溃后自动重启" />
      </el-form-item>

      <template v-if="form.auto_restart">
        <el-form-item label="最大重启次数">
          <el-input-number v-model="form.max_restarts" :min="1" :max="100" controls-position="right" />
          <span class="hint">超过后不再重启，直到重置窗口过期</span>
        </el-form-item>

        <el-form-item label="重置窗口">
          <el-input-number v-model="resetValue" :min="1" :max="1440" controls-position="right" />
          <el-select v-model="resetUnit" style="width: 80px; margin-left: 8px">
            <el-option label="分钟" value="min" />
            <el-option label="小时" value="hour" />
          </el-select>
          <span class="hint">窗口期内重启次数达到上限后停止，窗口过期后重新计数</span>
        </el-form-item>
      </template>

      <el-divider content-position="left">停止策略</el-divider>

      <el-form-item label="停止超时">
        <el-input-number v-model="form.stop_timeout" :min="1" :max="60" controls-position="right" />
        <span class="hint">秒。优雅停止后等待的超时时间，超时后强制终止</span>
      </el-form-item>

      <el-form-item label="手动冲突策略">
        <el-select v-model="form.manual_conflict" style="width: 200px">
          <el-option label="重启（停旧启新）" value="restart" />
          <el-option label="拒绝（提示正在运行）" value="reject" />
        </el-select>
        <span class="hint">手动运行时，任务已有运行中实例的处理方式</span>
      </el-form-item>

      <el-form-item label="自动冲突策略">
        <el-select v-model="form.auto_conflict" style="width: 200px">
          <el-option label="跳过（不触发）" value="skip" />
          <el-option label="重启（停旧启新）" value="restart" />
        </el-select>
        <span class="hint">定时调度触发时的处理方式</span>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, nextTick } from 'vue'

const props = defineProps({
  modelValue: { type: Object, default: () => ({}) },
})

const emit = defineEmits(['update:modelValue'])

const form = ref({
  auto_restart: false,
  max_restarts: 5,
  reset_time: 600,
  stop_timeout: 5,
  manual_conflict: 'restart',
  auto_conflict: 'skip',
})

const resetValue = ref(10)
const resetUnit = ref('min')

// 防止 watch 死循环
let skipPropWatch = false

function applyProps(v) {
  if (!v || Object.keys(v).length === 0) return
  form.value = {
    auto_restart: !!v.auto_restart,
    max_restarts: v.max_restarts || 5,
    reset_time: v.reset_time || 600,
    stop_timeout: v.stop_timeout || 5,
    manual_conflict: v.manual_conflict || 'restart',
    auto_conflict: v.auto_conflict || 'skip',
  }
  const rt = form.value.reset_time
  if (rt >= 3600 && rt % 3600 === 0) {
    resetValue.value = rt / 3600
    resetUnit.value = 'hour'
  } else {
    resetValue.value = Math.max(1, Math.round(rt / 60))
    resetUnit.value = 'min'
  }
}

onMounted(() => applyProps(props.modelValue))

// 监听 props 变化（外部加载完成时）
watch(() => props.modelValue, (v) => {
  if (skipPropWatch) return
  applyProps(v)
}, { deep: true })

// 重置窗口输入变化 → 同步到 form 并通知
watch([resetValue, resetUnit], () => {
  if (resetUnit.value === 'hour') {
    form.value.reset_time = resetValue.value * 3600
  } else {
    form.value.reset_time = resetValue.value * 60
  }
  skipPropWatch = true
  emit('update:modelValue', { ...form.value })
  nextTick(() => { skipPropWatch = false })
})

// 表单字段变化 → 通知父组件
watch(
  () => [
    form.value.auto_restart,
    form.value.max_restarts,
    form.value.stop_timeout,
    form.value.manual_conflict,
    form.value.auto_conflict,
  ],
  () => {
    skipPropWatch = true
    emit('update:modelValue', { ...form.value })
    nextTick(() => { skipPropWatch = false })
  },
)
</script>

<style scoped>
.daemon-config { padding: 4px 0; }
.hint { margin-left: 12px; font-size: 12px; color: #94a3b8; }
</style>