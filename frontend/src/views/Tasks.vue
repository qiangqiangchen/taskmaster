<template>
    <div class="tasks-page">
        <!-- 页头 -->
        <div class="page-header">
            <h2>任务管理</h2>
            <el-button type="primary" @click="openCreateDialog">
                <el-icon>
                    <Plus/>
                </el-icon>
                新建任务
            </el-button>
        </div>

        <!-- 筛选栏 -->
        <el-card shadow="never" class="filter-card">
            <div class="filter-row">
                <el-input
                        v-model="filters.search"
                        placeholder="搜索任务名称..."
                        prefix-icon="Search"
                        clearable
                        style="width: 260px"
                        @input="loadTasks"
                />
                <el-select
                        v-model="filters.type"
                        placeholder="任务类型"
                        clearable
                        style="width: 160px"
                        @change="loadTasks"
                >
                    <el-option label="命令行" value="command"/>
                    <el-option label="Python 脚本" value="python_script"/>
                    <el-option label="多文件项目" value="project"/>
                    <el-option label="EXE 程序" value="executable"/>
                </el-select>
                <el-select
                        v-model="filters.status"
                        placeholder="运行状态"
                        clearable
                        style="width: 140px"
                        @change="loadTasks"
                >
                    <el-option label="运行中" value="running"/>
                    <el-option label="空闲" value="idle"/>
                    <el-option label="已停用" value="disabled"/>
                    <el-option label="失败" value="failed"/>
                </el-select>
                <el-button @click="resetFilters" text>
                    <el-icon>
                        <RefreshRight/>
                    </el-icon>
                    重置
                </el-button>
            </div>
        </el-card>

        <!-- 任务列表 -->
        <el-card shadow="never" style="margin-top: 16px">
            <el-table
                    :data="taskList"
                    v-loading="loading"
                    empty-text="暂无任务，点击「新建任务」开始"
                    @row-click="goDetail"
                    row-class-name="clickable-row"
            >
                <el-table-column label="任务名称" min-width="200">
                    <template #default="{ row }">
                        <div class="task-name-cell">
                            <el-icon :size="22" :color="typeMeta[row.type].color">
                                <component :is="typeMeta[row.type].icon"/>
                            </el-icon>
                            <span class="task-name">{{ row.name }}</span>
                            <el-tag
                                    v-if="!row.has_script && row.type !== 'command'"
                                    type="warning"
                                    size="small"
                                    effect="plain"
                            >
                                未上传脚本
                            </el-tag>
                        </div>
                    </template>
                </el-table-column>

                <el-table-column label="类型" width="130" align="center">
                    <template #default="{ row }">
                        <el-tag :color="typeMeta[row.type].bgColor"
                                :style="{ color: typeMeta[row.type].color, border: 'none' }" size="small">
                            {{ typeMeta[row.type].label }}
                        </el-tag>
                    </template>
                </el-table-column>

                <el-table-column label="标签" min-width="150">
                    <template #default="{ row }">
                        <el-tag
                                v-for="tag in (row.tags || []).slice(0, 3)"
                                :key="tag"
                                size="small"
                                effect="plain"
                                style="margin-right: 4px"
                        >
                            {{ tag }}
                        </el-tag>
                        <span v-if="(row.tags || []).length > 3" class="more-tags">
              +{{ row.tags.length - 3 }}
            </span>
                    </template>
                </el-table-column>

                <el-table-column label="状态" width="110" align="center">
                    <template #default="{ row }">
                        <div class="status-cell">
                            <span :class="['status-dot', `dot-${row.run_status}`]"></span>
                            <span :class="[`status-text-${row.run_status}`]">
                {{ statusLabel[row.run_status] }}
              </span>
                        </div>
                    </template>
                </el-table-column>

                <el-table-column label="最后运行" width="180">
                    <template #default="{ row }">
                        <template v-if="row.last_run">
                            <div class="last-run-cell">
                <span :class="['run-result', `result-${row.last_run.status}`]">
                  {{ runResultLabel[row.last_run.status] }}
                </span>
                                <span class="run-time">{{ formatTime(row.last_run.started_at) }}</span>
                            </div>
                        </template>
                        <span v-else class="no-run">—</span>
                    </template>
                </el-table-column>

                <el-table-column label="操作" width="200" align="center" fixed="right">
                    <template #default="{ row }">
                        <el-button-group>
                            <el-tooltip content="运行" placement="top">
                                <el-button size="small" type="success" @click.stop="handleRun(row)">
                                    <el-icon>
                                        <VideoPlay/>
                                    </el-icon>
                                </el-button>
                            </el-tooltip>
                            <el-tooltip v-if="row.run_status === 'running'" content="停止" placement="top">
                                <el-button size="small" type="warning" @click.stop="handleStop(row)">
                                    <el-icon>
                                        <VideoPause/>
                                    </el-icon>
                                </el-button>
                            </el-tooltip>
                            <el-tooltip content="编辑" placement="top">
                                <el-button size="small" @click.stop="openEditDialog(row)">
                                    <el-icon>
                                        <Edit/>
                                    </el-icon>
                                </el-button>
                            </el-tooltip>
                            <el-tooltip :content="row.enabled ? '停用' : '启用'" placement="top">
                                <el-button size="small" @click.stop="handleToggle(row)">
                                    <el-icon>
                                        <component :is="row.enabled ? 'Switch' : 'Open'"/>
                                    </el-icon>
                                </el-button>
                            </el-tooltip>
                            <el-tooltip content="复制" placement="top">
                                <el-button size="small" @click.stop="handleCopy(row)">
                                    <el-icon>
                                        <CopyDocument/>
                                    </el-icon>
                                </el-button>
                            </el-tooltip>
                            <el-tooltip content="删除" placement="top">
                                <el-button size="small" type="danger" @click.stop="handleDelete(row)">
                                    <el-icon>
                                        <Delete/>
                                    </el-icon>
                                </el-button>
                            </el-tooltip>
                        </el-button-group>
                    </template>
                </el-table-column>
            </el-table>
        </el-card>

        <!-- 新建/编辑弹窗 -->
        <el-dialog
                v-model="dialogVisible"
                :title="isEdit ? '编辑任务' : '新建任务'"
                width="680px"
                :close-on-click-modal="false"
                destroy-on-close
        >
            <el-form
                    ref="formRef"
                    :model="form"
                    :rules="formRules"
                    label-width="110px"
                    label-position="right"
            >
                <!-- 基本信息 -->
                <el-divider content-position="left">基本信息</el-divider>

                <el-form-item label="任务名称" prop="name">
                    <el-input v-model="form.name" placeholder="输入任务名称" maxlength="100" show-word-limit/>
                </el-form-item>

                <el-form-item label="任务类型" prop="type">
                    <el-radio-group v-model="form.type" :disabled="isEdit" @change="onTypeChange">
                        <el-radio-button value="command">
                            <el-icon>
                                <Monitor/>
                            </el-icon>
                            命令行
                        </el-radio-button>
                        <el-radio-button value="python_script">
                            <el-icon>
                                <Document/>
                            </el-icon>
                            Python
                        </el-radio-button>
                        <el-radio-button value="project">
                            <el-icon>
                                <Folder/>
                            </el-icon>
                            多文件项目
                        </el-radio-button>
                        <el-radio-button value="executable">
                            <el-icon>
                                <Cpu/>
                            </el-icon>
                            EXE
                        </el-radio-button>
                    </el-radio-group>
                </el-form-item>

                <el-form-item label="标签">
                    <div class="tags-editor">
                        <el-tag
                                v-for="(tag, idx) in form.tags"
                                :key="idx"
                                closable
                                @close="removeTag(idx)"
                                style="margin-right: 6px; margin-bottom: 4px"
                        >
                            {{ tag }}
                        </el-tag>
                        <el-input
                                v-if="tagInputVisible"
                                ref="tagInputRef"
                                v-model="tagInputValue"
                                size="small"
                                style="width: 120px"
                                @keyup.enter="addTag"
                                @blur="addTag"
                        />
                        <el-button v-else size="small" @click="showTagInput">
                            <el-icon>
                                <Plus/>
                            </el-icon>
                            添加标签
                        </el-button>
                    </div>
                </el-form-item>

                <!-- 类型特定配置 -->
                <el-divider content-position="left">
                    {{ typeMeta[form.type].label }} 配置
                </el-divider>

                <!-- 命令行 -->
                <template v-if="form.type === 'command'">
                    <el-form-item label="命令模板" prop="command_template">
                        <el-input
                                v-model="form.command_template"
                                type="textarea"
                                :rows="4"
                                placeholder="输入命令模板，如：python script.py --url {url} --count {count}"
                        />
                    </el-form-item>
                </template>

                <!-- Python 单脚本 -->
                <template v-if="form.type === 'python_script'">
                    <el-form-item label="脚本文件">
                        <div class="upload-area">
                            <el-upload
                                    :auto-upload="false"
                                    :limit="1"
                                    accept=".py"
                                    :on-change="onFileChange"
                                    :file-list="uploadFileList"
                                    :on-remove="onFileRemove"
                            >
                                <el-button size="small">
                                    <el-icon>
                                        <Upload/>
                                    </el-icon>
                                    选择 .py 文件
                                </el-button>
                            </el-upload>
                            <span v-if="isEdit && editingTask?.has_script" class="upload-hint success">
                已有脚本文件，重新上传将覆盖
              </span>
                            <span v-else-if="!uploadFile" class="upload-hint warning">
                尚未上传脚本文件
              </span>
                        </div>
                    </el-form-item>
                    <el-form-item label="命令模板">
                        <el-input
                                v-model="form.command_template"
                                type="textarea"
                                :rows="3"
                                placeholder="如：{python} script.py --url {url}（留空则自动生成）"
                        />
                    </el-form-item>
                    <el-form-item label="Python 解释器">
                        <el-input
                                v-model="form.entry_config.python_path"
                                placeholder="默认使用系统 python（可在设置中修改全局默认）"
                        />
                    </el-form-item>
                </template>

                <!-- 多文件项目 -->
                <template v-if="form.type === 'project'">
                    <el-form-item label="项目压缩包">
                        <div class="upload-area">
                            <el-upload
                                    :auto-upload="false"
                                    :limit="1"
                                    accept=".zip"
                                    :on-change="onFileChange"
                                    :file-list="uploadFileList"
                                    :on-remove="onFileRemove"
                            >
                                <el-button size="small">
                                    <el-icon>
                                        <Upload/>
                                    </el-icon>
                                    选择 .zip 文件
                                </el-button>
                            </el-upload>
                            <span v-if="isEdit && editingTask?.has_script" class="upload-hint success">
                已有项目文件，重新上传将覆盖
              </span>
                            <span v-else-if="!uploadFile" class="upload-hint warning">
                尚未上传项目文件
              </span>
                        </div>
                    </el-form-item>
                    <el-form-item label="入口命令模板" prop="command_template">
                        <el-input
                                v-model="form.command_template"
                                type="textarea"
                                :rows="3"
                                placeholder="如：python main.py --input {input_file}"
                        />
                    </el-form-item>
                </template>

                <!-- EXE -->
                <template v-if="form.type === 'executable'">
                    <el-form-item label="EXE 文件">
                        <div class="upload-area">
                            <el-upload
                                    :auto-upload="false"
                                    :limit="1"
                                    accept=".exe"
                                    :on-change="onFileChange"
                                    :file-list="uploadFileList"
                                    :on-remove="onFileRemove"
                            >
                                <el-button size="small">
                                    <el-icon>
                                        <Upload/>
                                    </el-icon>
                                    选择 .exe 文件
                                </el-button>
                            </el-upload>
                            <span v-if="isEdit && editingTask?.has_script" class="upload-hint success">
                已有 EXE 文件，重新上传将覆盖
              </span>
                            <span v-else-if="!uploadFile" class="upload-hint warning">
                尚未上传 EXE 文件
              </span>
                        </div>
                    </el-form-item>
                    <el-form-item label="启动参数">
                        <el-input
                                v-model="form.command_template"
                                type="textarea"
                                :rows="3"
                                placeholder="如：--input {input_file} --output {output_dir}"
                        />
                    </el-form-item>
                    <el-form-item label="隐藏窗口">
                        <el-switch v-model="form.entry_config.no_window"/>
                        <span class="form-hint">后台静默运行，不弹出控制台窗口</span>
                    </el-form-item>
                </template>

                <!-- 工作目录 -->
                <el-divider content-position="left">其他</el-divider>
                <el-form-item label="工作目录">
                    <el-input v-model="form.work_dir" placeholder="留空则使用工作区根目录"/>
                </el-form-item>
            </el-form>

            <template #footer>
                <el-button @click="dialogVisible = false">取消</el-button>
                <el-button type="primary" :loading="submitting" @click="handleSubmit">
                    {{ isEdit ? '保存' : '创建' }}
                </el-button>
            </template>
        </el-dialog>
        <!-- 运行参数弹窗 -->
        <el-dialog
                v-model="runDialogVisible"
                :title="`运行 - ${runTaskName}`"
                width="600px"
                :close-on-click-modal="false"
                destroy-on-close
        >
            <el-form label-width="100px">
                <ParamFormRenderer
                        ref="runFormRef"
                        :schema="runParamSchema"
                        v-model="runParamValues"
                />
            </el-form>
            <template #footer>
                <el-button @click="runDialogVisible = false">取消</el-button>
                <el-button type="success" :loading="runStarting" @click="confirmRun">
                    <el-icon>
                        <VideoPlay/>
                    </el-icon>
                    运行
                </el-button>
            </template>
        </el-dialog>
    </div>
</template>

<script setup>
import ParamFormRenderer from '../components/ParamFormRenderer.vue'
import {ref, reactive, nextTick, onMounted} from 'vue'
import {useRouter} from 'vue-router'
import {ElMessage, ElMessageBox} from 'element-plus'
import {
    getTasks, createTask, updateTask, deleteTask,
    toggleTask, copyTask, uploadScript,
} from '../api/tasks'
import {startRun, stopRun} from '../api/runs'
import {getParams} from '../api/params'

const router = useRouter()

// ========== 列表数据 ==========
const loading = ref(false)
const taskList = ref([])

const filters = reactive({
    search: '',
    type: null,
    status: null,
})

const typeMeta = {
    command: {label: '命令行', icon: 'Monitor', color: '#3b82f6', bgColor: '#eff6ff'},
    python_script: {label: 'Python', icon: 'Document', color: '#22c55e', bgColor: '#f0fdf4'},
    project: {label: '多文件', icon: 'Folder', color: '#f59e0b', bgColor: '#fffbeb'},
    executable: {label: 'EXE', icon: 'Cpu', color: '#8b5cf6', bgColor: '#f5f3ff'},
}

const statusLabel = {
    running: '运行中',
    idle: '空闲',
    disabled: '已停用',
    failed: '失败',
}

const runResultLabel = {
    success: '成功',
    failed: '失败',
    stopped: '已停止',
    running: '运行中',
}

async function loadTasks() {
    loading.value = true
    try {
        const res = await getTasks(filters)
        taskList.value = res.items || []
    } catch {
        // 错误已由拦截器处理
    } finally {
        loading.value = false
    }
}

function resetFilters() {
    filters.search = ''
    filters.type = null
    filters.status = null
    loadTasks()
}

function goDetail(row) {
    router.push(`/tasks/${row.task_id}`)
}

function formatTime(isoStr) {
    if (!isoStr) return ''
    const d = new Date(isoStr)
    const now = new Date()
    const diffMs = now - d
    const diffMin = Math.floor(diffMs / 60000)
    if (diffMin < 1) return '刚刚'
    if (diffMin < 60) return `${diffMin} 分钟前`
    const diffH = Math.floor(diffMin / 60)
    if (diffH < 24) return `${diffH} 小时前`
    const diffD = Math.floor(diffH / 24)
    if (diffD < 30) return `${diffD} 天前`
    return d.toLocaleDateString('zh-CN')
}

// ========== 弹窗 ==========
const dialogVisible = ref(false)
const isEdit = ref(false)
const editingTask = ref(null)
const submitting = ref(false)
const formRef = ref()
const uploadFile = ref(null)
const uploadFileList = ref([])

const form = reactive({
    name: '',
    type: 'command',
    command_template: '',
    entry_config: {},
    work_dir: '',
    tags: [],
    enabled: true,
})

const formRules = {
    name: [{required: true, message: '请输入任务名称', trigger: 'blur'}],
    type: [{required: true, message: '请选择任务类型', trigger: 'change'}],
    command_template: [
        {
            validator: (rule, value, callback) => {
                if (form.type === 'command' && !value.trim()) {
                    callback(new Error('命令行任务必须填写命令模板'))
                } else if (form.type === 'project' && !value.trim()) {
                    callback(new Error('多文件项目必须填写入口命令模板'))
                } else {
                    callback()
                }
            },
            trigger: 'blur',
        },
    ],
}

// 标签编辑
const tagInputVisible = ref(false)
const tagInputValue = ref('')
const tagInputRef = ref()

function showTagInput() {
    tagInputVisible.value = true
    nextTick(() => tagInputRef.value?.focus())
}

function addTag() {
    const val = tagInputValue.value.trim()
    if (val && !form.tags.includes(val)) {
        form.tags.push(val)
    }
    tagInputVisible.value = false
    tagInputValue.value = ''
}

function removeTag(idx) {
    form.tags.splice(idx, 1)
}

function onTypeChange() {
    form.command_template = ''
    form.entry_config = {}
    uploadFile.value = null
    uploadFileList.value = []
}

function onFileChange(file) {
    uploadFile.value = file.raw
    uploadFileList.value = [file]
}

function onFileRemove() {
    uploadFile.value = null
    uploadFileList.value = []
}

function openCreateDialog() {
    isEdit.value = false
    editingTask.value = null
    Object.assign(form, {
        name: '',
        type: 'command',
        command_template: '',
        entry_config: {},
        work_dir: '',
        tags: [],
        enabled: true,
    })
    uploadFile.value = null
    uploadFileList.value = []
    dialogVisible.value = true
}

function openEditDialog(task) {
    isEdit.value = true
    editingTask.value = task
    Object.assign(form, {
        name: task.name,
        type: task.type,
        command_template: task.command_template || '',
        entry_config: {...task.entry_config},
        work_dir: task.work_dir || '',
        tags: [...(task.tags || [])],
        enabled: task.enabled,
    })
    uploadFile.value = null
    uploadFileList.value = []
    dialogVisible.value = true
}

async function handleSubmit() {
    await formRef.value.validate()
    submitting.value = true
    try {
        const payload = {
            name: form.name,
            type: form.type,
            command_template: form.command_template,
            entry_config: form.entry_config || {},
            work_dir: form.work_dir,
            tags: form.tags,
            enabled: form.enabled,
        }

        let taskId
        if (isEdit.value) {
            taskId = editingTask.value.task_id
            await updateTask(taskId, payload)
            ElMessage.success('任务更新成功')
        } else {
            const res = await createTask(payload)
            taskId = res.task_id
            ElMessage.success('任务创建成功')
        }

        // 上传文件
        if (uploadFile.value && form.type !== 'command') {
            try {
                await uploadScript(taskId, uploadFile.value)
                ElMessage.success('文件上传成功')
            } catch (e) {
                ElMessage.warning('任务已保存，但文件上传失败：' + (e.response?.data?.detail || '未知错误'))
            }
        }

        dialogVisible.value = false
        loadTasks()
    } catch {
        // 错误已由拦截器处理
    } finally {
        submitting.value = false
    }
}

// ========== 操作 ==========

async function handleToggle(task) {
    try {
        const res = await toggleTask(task.task_id)
        ElMessage.success(res.message)
        loadTasks()
    } catch {
        // 已处理
    }
}

async function handleCopy(task) {
    try {
        await ElMessageBox.confirm(
            `确定要将「${task.name}」复制为新任务吗？`,
            '复制任务',
            {type: 'info', confirmButtonText: '复制', cancelButtonText: '取消'}
        )
        const res = await copyTask(task.task_id)
        ElMessage.success(res.message)
        loadTasks()
    } catch {
        // 用户取消或请求错误
    }
}

async function handleDelete(task) {
    try {
        await ElMessageBox.confirm(
            `确定要删除任务「${task.name}」吗？该操作不可恢复，关联的脚本文件也将被删除。`,
            '删除任务',
            {
                type: 'warning',
                confirmButtonText: '删除',
                cancelButtonText: '取消',
                confirmButtonClass: 'el-button--danger'
            }
        )
        await deleteTask(task.task_id)
        ElMessage.success('任务已删除')
        loadTasks()
    } catch {
        // 用户取消或请求错误
    }
}

// ========== 运行/停止 ==========

const runDialogVisible = ref(false)
const runTaskId = ref('')
const runTaskName = ref('')
const runParamSchema = ref({params: []})
const runParamValues = ref({})
const runStarting = ref(false)
const runFormRef = ref()

async function handleRun(task) {
    runTaskId.value = task.task_id
    runTaskName.value = task.name
    runParamValues.value = {}
    runStarting.value = false

    try {
        const params = await getParams(task.task_id)
        runParamSchema.value = params.schema || {params: []}
    } catch {
        runParamSchema.value = {params: []}
    }

    runDialogVisible.value = true
}

async function confirmRun() {
    runStarting.value = true
    try {
        const values = runFormRef.value?.getValues?.() || {}
        const res = await startRun(runTaskId.value, values)
        ElMessage.success('运行已启动')
        runDialogVisible.value = false
        router.push(`/runs/${res.run_id}`)
    } catch {
        // 已处理
    } finally {
        runStarting.value = false
    }
}

async function handleStop(task) {
  try {
    // 从运行历史找该任务运行中的记录
    const res = await getRuns({ task_id: task.task_id, status: 'running', page_size: 10 })
    const runningItems = res.items?.filter(r => r.status === 'running') || []
    if (runningItems.length === 0) {
      ElMessage.info('该任务没有运行中的实例')
      return
    }
    // 停止所有运行中的实例
    for (const item of runningItems) {
      await stopRun(item.run_id)
    }
    ElMessage.success('停止指令已发送')
    // 延迟刷新，等待进程真正退出
    setTimeout(() => loadTasks(), 2000)
  } catch {}
}

// ========== 初始化 ==========
onMounted(() => {
    loadTasks()
})
</script>

<style scoped>
.tasks-page {
    max-width: 1400px;
}

.page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
}

.page-header h2 {
    margin: 0;
    font-size: 20px;
    color: #1e293b;
}

.filter-card :deep(.el-card__body) {
    padding: 16px 20px;
}

.filter-row {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
}

/* 任务名称单元格 */
.task-name-cell {
    display: flex;
    align-items: center;
    gap: 10px;
}

.task-name {
    font-weight: 500;
    color: #1e293b;
}

.more-tags {
    color: #94a3b8;
    font-size: 12px;
}

/* 状态 */
.status-cell {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
}

.status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
}

.dot-running {
    background: #22c55e;
    box-shadow: 0 0 6px rgba(34, 197, 94, 0.5);
}

.dot-idle {
    background: #3b82f6;
}

.dot-disabled {
    background: #94a3b8;
}

.dot-failed {
    background: #ef4444;
}

.status-text-running {
    color: #22c55e;
    font-size: 13px;
}

.status-text-idle {
    color: #3b82f6;
    font-size: 13px;
}

.status-text-disabled {
    color: #94a3b8;
    font-size: 13px;
}

.status-text-failed {
    color: #ef4444;
    font-size: 13px;
}

/* 最后运行 */
.last-run-cell {
    display: flex;
    flex-direction: column;
    gap: 2px;
}

.run-result {
    font-size: 13px;
    font-weight: 500;
}

.result-success {
    color: #22c55e;
}

.result-failed {
    color: #ef4444;
}

.result-stopped {
    color: #94a3b8;
}

.result-running {
    color: #3b82f6;
}

.run-time {
    font-size: 12px;
    color: #94a3b8;
}

.no-run {
    color: #d1d5db;
}

/* 行可点击 */
:deep(.clickable-row) {
    cursor: pointer;
}

:deep(.clickable-row:hover) {
    background: #f8fafc;
}

/* 标签编辑器 */
.tags-editor {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 4px;
}

/* 上传区域 */
.upload-area {
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.upload-hint {
    font-size: 12px;
}

.upload-hint.success {
    color: #22c55e;
}

.upload-hint.warning {
    color: #f59e0b;
}

.form-hint {
    margin-left: 12px;
    font-size: 12px;
    color: #94a3b8;
}
</style>