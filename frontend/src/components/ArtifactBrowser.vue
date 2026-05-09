<template>
  <div class="artifact-browser">
    <!-- 工具栏 -->
    <div class="artifact-toolbar">
      <div class="toolbar-left">
        <!-- 面包屑 -->
        <el-breadcrumb separator="/">
          <el-breadcrumb-item @click="navigateTo('')">
            <el-icon><HomeFilled /></el-icon> 根目录
          </el-breadcrumb-item>
          <el-breadcrumb-item
            v-for="crumb in data.breadcrumbs"
            :key="crumb.path"
            @click="navigateTo(crumb.path)"
          >
            {{ crumb.name }}
          </el-breadcrumb-item>
        </el-breadcrumb>
      </div>
      <div class="toolbar-right">
        <el-button size="small" @click="refresh">
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>
        <el-button size="small" @click="copyOutputPath" v-if="data.output_dir">
          <el-icon><CopyDocument /></el-icon> 复制路径
        </el-button>
      </div>
    </div>

    <!-- 文件列表 -->
    <el-table
      :data="data.files"
      v-loading="loading"
      empty-text="暂无产物文件"
      size="small"
      @row-click="handleRowClick"
      row-class-name="artifact-row"
    >
      <el-table-column label="名称" min-width="260">
        <template #default="{ row }">
          <div class="file-name-cell">
            <el-icon :size="18" :color="getFileIcon(row).color">
              <component :is="getFileIcon(row).icon" />
            </el-icon>
            <span :class="{ 'file-dir': row.is_dir }">{{ row.name }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="大小" width="110" align="right">
        <template #default="{ row }">
          <span v-if="!row.is_dir" class="mono">{{ row.size_display }}</span>
          <span v-else class="dir-label">文件夹</span>
        </template>
      </el-table-column>
      <el-table-column label="修改时间" width="180">
        <template #default="{ row }">{{ formatTime(row.modified) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="140" align="center">
        <template #default="{ row }">
          <el-button
            v-if="!row.is_dir"
            size="small"
            text
            type="primary"
            @click.stop="handleDownload(row)"
          >
            <el-icon><Download /></el-icon> 下载
          </el-button>
          <el-button
            size="small"
            text
            type="danger"
            @click.stop="handleDelete(row)"
          >
            <el-icon><Delete /></el-icon>
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listArtifacts, downloadArtifact, deleteArtifact } from '../api/artifacts'

const props = defineProps({
  runId: { type: String, required: true },
})

const loading = ref(false)
const currentPath = ref('')
const data = reactive({
  files: [],
  current_path: '',
  breadcrumbs: [],
  output_dir: '',
})

async function loadData(path = '') {
  loading.value = true
  try {
    const res = await listArtifacts(props.runId, path)
    data.files = res.files || []
    data.current_path = res.current_path || ''
    data.breadcrumbs = res.breadcrumbs || []
    data.output_dir = res.output_dir || ''
    currentPath.value = path
  } catch {} finally {
    loading.value = false
  }
}

function navigateTo(path) {
  loadData(path)
}

function refresh() {
  loadData(currentPath.value)
}

function handleRowClick(row) {
  if (row.is_dir) {
    loadData(row.path)
  }
}

function handleDownload(row) {
  downloadArtifact(props.runId, row.path)
}

async function handleDelete(row) {
  const typeText = row.is_dir ? '目录' : '文件'
  try {
    await ElMessageBox.confirm(
      `确定要删除${typeText}「${row.name}」吗？`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
    await deleteArtifact(props.runId, row.path)
    ElMessage.success('已删除')
    refresh()
  } catch {}
}

function copyOutputPath() {
  navigator.clipboard.writeText(data.output_dir).then(() => {
    ElMessage.success('路径已复制')
  })
}

function getFileIcon(row) {
  if (row.is_dir) return { icon: 'Folder', color: '#f59e0b' }
  const ext = row.extension
  if (['.py', '.js', '.ts', '.json', '.yaml', '.yml', '.toml', '.xml', '.html', '.css', '.md', '.txt', '.log', '.csv'].includes(ext))
    return { icon: 'Document', color: '#3b82f6' }
  if (['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp'].includes(ext))
    return { icon: 'Picture', color: '#22c55e' }
  if (['.zip', '.rar', '.7z', '.tar', '.gz'].includes(ext))
    return { icon: 'Files', color: '#8b5cf6' }
  if (['.exe', '.msi'].includes(ext))
    return { icon: 'Cpu', color: '#8b5cf6' }
  if (['.mp4', '.avi', '.mkv', '.mp3', '.wav'].includes(ext))
    return { icon: 'VideoCamera', color: '#ef4444' }
  return { icon: 'Document', color: '#94a3b8' }
}

function formatTime(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString('zh-CN')
}

onMounted(() => loadData())

watch(() => props.runId, () => loadData())
</script>

<style scoped>
.artifact-browser {
  min-height: 120px;
}

.artifact-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.toolbar-left :deep(.el-breadcrumb) {
  font-size: 13px;
}

.toolbar-left :deep(.el-breadcrumb__item) {
  cursor: pointer;
}

.toolbar-right {
  display: flex;
  gap: 8px;
}

.file-name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.file-dir {
  color: #3b82f6;
  font-weight: 500;
}

.dir-label {
  color: #94a3b8;
  font-size: 12px;
}

.mono {
  font-family: 'Cascadia Code', 'Consolas', monospace;
  font-size: 12px;
  color: #64748b;
}

:deep(.artifact-row) {
  cursor: pointer;
}

:deep(.artifact-row:hover) {
  background: #f0f9ff;
}
</style>