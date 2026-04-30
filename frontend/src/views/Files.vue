<template>
  <div>
    <div class="page-header">
      <h2>文件管理</h2>
    </div>
    <el-card shadow="never">
      <el-empty description="文件管理功能将在第 8 天实现">
        <template #image>
          <el-icon :size="64" color="#c0c4cc"><FolderOpened /></el-icon>
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