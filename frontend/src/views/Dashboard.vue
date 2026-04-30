<template>
  <div class="dashboard">
    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stat-row">
      <el-col :span="6" v-for="card in stats" :key="card.label">
        <el-card shadow="hover" class="stat-card" :body-style="{ padding: '24px' }">
          <div class="stat-icon" :style="{ background: card.bgColor }">
            <el-icon :size="28" :color="card.color">
              <component :is="card.icon" />
            </el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value" :style="{ color: card.color }">{{ card.value }}</div>
            <div class="stat-label">{{ card.label }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 资源 & 异常 -->
    <el-row :gutter="20" style="margin-top: 24px;">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <el-icon><Cpu /></el-icon>
              <span>主机资源</span>
            </div>
          </template>
          <div class="resource-item" v-for="r in resources" :key="r.label">
            <span class="resource-label">{{ r.label }}</span>
            <el-progress
              :percentage="r.value"
              :color="r.color"
              :stroke-width="20"
              :text-inside="true"
              style="flex: 1"
            />
          </div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <el-icon><WarningFilled /></el-icon>
              <span>异常提醒</span>
            </div>
          </template>
          <el-empty description="暂无异常，一切正常" :image-size="80" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { reactive } from 'vue'

const stats = reactive([
  { label: '任务总数', value: 0, color: '#3b82f6', bgColor: '#eff6ff', icon: 'List' },
  { label: '运行中', value: 0, color: '#22c55e', bgColor: '#f0fdf4', icon: 'VideoPlay' },
  { label: '今日执行', value: 0, color: '#f59e0b', bgColor: '#fffbeb', icon: 'Timer' },
  { label: '今日失败', value: 0, color: '#ef4444', bgColor: '#fef2f2', icon: 'CircleCloseFilled' },
])

const resources = reactive([
  { label: 'CPU', value: 0, color: '#3b82f6' },
  { label: '内存', value: 0, color: '#22c55e' },
  { label: '磁盘', value: 0, color: '#f59e0b' },
])
</script>

<style scoped>
.stat-row {
  margin-top: 0;
}

.stat-card {
  display: flex;
  align-items: center;
}

.stat-card :deep(.el-card__body) {
  display: flex;
  align-items: center;
  gap: 16px;
  width: 100%;
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-value {
  font-size: 32px;
  font-weight: 800;
  line-height: 1;
}

.stat-label {
  font-size: 13px;
  color: #94a3b8;
  margin-top: 6px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: #1e293b;
}

.resource-item {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
}

.resource-item:last-child {
  margin-bottom: 0;
}

.resource-label {
  width: 40px;
  font-size: 14px;
  color: #64748b;
  font-weight: 500;
}
</style>