<template>
  <div class="layout">
    <aside class="sidebar">
      <div class="sidebar-logo">
        <el-icon :size="22"><Monitor /></el-icon>
        <span class="logo-text">TaskMaster</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        router
        class="sidebar-menu"
      >
        <el-menu-item index="/dashboard">
          <el-icon><DataLine /></el-icon>
          <span>仪表盘</span>
        </el-menu-item>
        <el-menu-item index="/tasks">
          <el-icon><List /></el-icon>
          <span>任务管理</span>
        </el-menu-item>
        <el-menu-item index="/runs">
          <el-icon><VideoPlay /></el-icon>
          <span>运行历史</span>
        </el-menu-item>
        <el-menu-item index="/audit">
          <el-icon><Document /></el-icon>
          <span>审计日志</span>
        </el-menu-item>

        <div class="sidebar-divider"></div>

        <el-menu-item index="/settings">
          <el-icon><Setting /></el-icon>
          <span>系统设置</span>
        </el-menu-item>
      </el-menu>

      <!-- 底部版本信息 -->
      <<!-- 底部 -->
      <div class="sidebar-footer">
        <div class="user-info">
          <el-icon><UserFilled /></el-icon>
          <span>{{ username }}</span>
        </div>
        <el-button text class="logout-btn" @click="handleLogout">
          <el-icon><SwitchButton /></el-icon>
          <span>退出登录</span>
        </el-button>
      </div>
    </aside>
    <main class="main-content">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" :key="$route.fullPath" />
        </transition>
      </router-view>
    </main>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const username = ref(localStorage.getItem('username') || 'admin')

const activeMenu = computed(() => {
  const path = route.path
  if (path.startsWith('/dashboard')) return '/dashboard'
  if (path.startsWith('/tasks')) return '/tasks'
  if (path.startsWith('/runs')) return '/runs'
  if (path.startsWith('/audit')) return '/audit'
  if (path.startsWith('/settings')) return '/settings'
  return '/dashboard'
})

function handleLogout() {
  localStorage.removeItem('token')
  localStorage.removeItem('username')
  router.push('/login')
}
</script>

<style scoped>
.layout {
  display: flex;
  min-height: 100vh;
}

.sidebar {
  width: 220px;
  background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  z-index: 100;
}

.sidebar-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 24px 20px;
  color: #f8fafc;
  font-size: 18px;
  font-weight: 700;
  border-bottom: 1px solid rgba(255,255,255,0.08);
}

.logo-text {
  letter-spacing: 0.5px;
}

.sidebar-menu {
  border-right: none;
  background: transparent;
  padding-top: 12px;
  flex: 1;
}

.sidebar-menu .el-menu-item {
  color: #94a3b8;
  height: 42px;
  line-height: 42px;
  margin: 2px 12px;
  border-radius: 8px;
  font-size: 14px;
  transition: all 0.15s ease;
}

.sidebar-menu .el-menu-item:hover {
  background: rgba(255,255,255,0.08);
  color: #e2e8f0;
}

.sidebar-menu .el-menu-item.is-active {
  background: #3b82f6;
  color: #ffffff;
  box-shadow: 0 2px 8px rgba(59,130,246,0.3);
}

.sidebar-divider {
  height: 1px;
  background: rgba(255,255,255,0.06);
  margin: 8px 20px;
}

.sidebar-footer {
  padding: 12px 16px;
  border-top: 1px solid rgba(255,255,255,0.06);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #94a3b8;
}

.logout-btn {
  color: #64748b !important;
  font-size: 12px;
  padding: 4px 8px;
  height: auto;
}

.logout-btn:hover {
  color: #ef4444 !important;
}

.main-content {
  flex: 1;
  margin-left: 220px;
  background: #f8fafc;
  padding: 28px 36px;
  overflow-y: auto;
  min-height: 100vh;
  min-width: 0;
  width: calc(100vw - 220px);
}
</style>