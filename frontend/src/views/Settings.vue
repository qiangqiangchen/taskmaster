<template>
  <div>
    <div class="page-header">
      <h2>系统设置</h2>
    </div>
    <el-card shadow="never">
      <el-empty description="系统设置功能将在第 9 天实现">
        <template #image>
          <el-icon :size="64" color="#c0c4cc"><Setting /></el-icon>
        </template>
      </el-empty>
    </el-card>
  </div>
</template>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.page-header h2 { margin: 0; font-size: 20px; color: #1e293b; }
</style>