<template>
  <el-container class="layout-container">
    <!-- 侧边栏 -->
    <el-aside :width="isCollapse ? '64px' : '220px'" class="layout-aside">
      <div class="logo-area">
        <span v-if="!isCollapse" class="logo-text">TaskMaster</span>
        <span v-else class="logo-text-sm">TM</span>
      </div>

      <el-menu
        :default-active="activeRoute"
        :collapse="isCollapse"
        router
        background-color="#0f172a"
        text-color="#94a3b8"
        active-text-color="#60a5fa"
      >
        <el-menu-item index="/dashboard">
          <el-icon><Monitor /></el-icon>
          <template #title>总览</template>
        </el-menu-item>
        <el-menu-item index="/tasks">
          <el-icon><List /></el-icon>
          <template #title>任务管理</template>
        </el-menu-item>
        <el-menu-item index="/runs">
          <el-icon><VideoPlay /></el-icon>
          <template #title>运行历史</template>
        </el-menu-item>
        <el-menu-item index="/files">
          <el-icon><FolderOpened /></el-icon>
          <template #title>文件管理</template>
        </el-menu-item>
        <el-menu-item index="/settings">
          <el-icon><Setting /></el-icon>
          <template #title>系统设置</template>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <!-- 右侧主体 -->
    <el-container>
      <el-header class="layout-header">
        <div class="header-left">
          <el-icon class="collapse-btn" @click="isCollapse = !isCollapse">
            <Fold v-if="!isCollapse" />
            <Expand v-else />
          </el-icon>
          <span class="page-title">{{ currentPageTitle }}</span>
        </div>
        <div class="header-right">
          <span class="username">{{ auth.username }}</span>
          <el-dropdown @command="handleCommand">
            <el-avatar :size="32" class="user-avatar">
              {{ auth.username?.charAt(0)?.toUpperCase() }}
            </el-avatar>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">
                  <el-icon><SwitchButton /></el-icon>
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="layout-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const isCollapse = ref(false)

const activeRoute = computed(() => {
  const path = route.path
  // /tasks/xxx 应该高亮 /tasks
  const parts = path.split('/')
  return '/' + (parts[1] || 'dashboard')
})

const pageTitles = {
  dashboard: '总览',
  tasks: '任务管理',
  runs: '运行历史',
  files: '文件管理',
  settings: '系统设置',
}

const currentPageTitle = computed(() => {
  const key = route.path.split('/')[1] || 'dashboard'
  return pageTitles[key] || key
})

async function handleCommand(cmd) {
  if (cmd === 'logout') {
    await auth.logout()
    ElMessage.success('已退出登录')
    router.push('/login')
  }
}
</script>

<style scoped>
.layout-container {
  height: 100vh;
}

.layout-aside {
  background: #0f172a;
  transition: width 0.3s ease;
  overflow: hidden;
  border-right: 1px solid #1e293b;
}

.logo-area {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid #1e293b;
}

.logo-text {
  font-size: 20px;
  font-weight: 800;
  color: #60a5fa;
  letter-spacing: 3px;
}

.logo-text-sm {
  font-size: 20px;
  font-weight: 800;
  color: #60a5fa;
}

.layout-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #e4e7ed;
  background: #fff;
  padding: 0 24px;
  height: 60px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.collapse-btn {
  font-size: 20px;
  cursor: pointer;
  color: #606266;
  transition: color 0.2s;
}

.collapse-btn:hover {
  color: #409eff;
}

.page-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.username {
  color: #606266;
  font-size: 14px;
}

.user-avatar {
  background: #3b82f6;
  color: #fff;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
}

.layout-main {
  background: #f1f5f9;
  overflow-y: auto;
  padding: 24px;
}

/* 覆盖 Element Plus 菜单样式 */
.el-menu {
  border-right: none;
}

:deep(.el-menu-item) {
  transition: background-color 0.2s;
}

:deep(.el-menu-item:hover) {
  background-color: #1e293b !important;
}

:deep(.el-menu-item.is-active) {
  background-color: #1e3a5f !important;
}
</style>