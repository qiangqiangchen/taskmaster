<template>
  <div class="health-check-config">
    <el-form label-width="140px" size="default">
      <el-form-item label="检查类型">
        <el-select v-model="form.type" style="width: 200px">
          <el-option label="进程存活检测" value="process" />
          <el-option label="HTTP 端点检测" value="http" />
        </el-select>
      </el-form-item>

      <el-form-item v-if="form.type === 'http'" label="检测 URL">
        <el-input v-model="form.url" placeholder="http://127.0.0.1:8080/health" />
      </el-form-item>

      <el-form-item label="检查间隔">
        <el-input-number v-model="form.interval" :min="5" :max="300" controls-position="right" />
        <span class="hint">秒</span>
      </el-form-item>

      <el-form-item label="超时时间">
        <el-input-number v-model="form.timeout" :min="1" :max="30" controls-position="right" />
        <span class="hint">秒</span>
      </el-form-item>

      <el-form-item label="连续失败次数">
        <el-input-number v-model="form.fail_count" :min="1" :max="10" controls-position="right" />
        <span class="hint">连续失败达到此次数后判定为不健康</span>
      </el-form-item>

      <div class="hc-note">
        <el-icon><InfoFilled /></el-icon>
        <span>健康检查检测到不健康时，将停止该任务！</span>
      </div>
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
  type: 'process',
  url: '',
  interval: 30,
  timeout: 5,
  fail_count: 3,
})

let skipPropWatch = false

function applyProps(v) {
  if (!v || Object.keys(v).length === 0) return
  form.value = {
    type: v.type || 'process',
    url: v.url || '',
    interval: v.interval || 30,
    timeout: v.timeout || 5,
    fail_count: v.fail_count || 3,
  }
}

onMounted(() => applyProps(props.modelValue))

watch(() => props.modelValue, (v) => {
  if (skipPropWatch) return
  applyProps(v)
}, { deep: true })

watch(
  () => [
    form.value.type,
    form.value.url,
    form.value.interval,
    form.value.timeout,
    form.value.fail_count,
  ],
  () => {
    skipPropWatch = true
    emit('update:modelValue', { ...form.value })
    nextTick(() => { skipPropWatch = false })
  },
)
</script>

<style scoped>
.health-check-config { padding: 4px 0; }
.hint { margin-left: 12px; font-size: 12px; color: #94a3b8; }
.hc-note {
  display: flex; align-items: center; gap: 6px;
  padding: 8px 12px; background: #f0f9ff; border-radius: 6px;
  font-size: 12px; color: #3b82f6; margin-top: 4px;
}
</style>