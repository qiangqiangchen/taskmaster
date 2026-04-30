<template>
    <div class="task-detail" v-loading="loading">
        <!-- 页头 -->
        <div class="page-header">
            <div class="header-left">
                <el-button @click="$router.push('/tasks')" text>
                    <el-icon>
                        <ArrowLeft/>
                    </el-icon>
                    返回列表
                </el-button>
                <h2 v-if="task">{{ task.name }}</h2>
            </div>
            <div class="header-actions" v-if="task">
                <el-button type="success" @click="openRunDialog">
                    <el-icon>
                        <VideoPlay/>
                    </el-icon>
                    运行
                </el-button>
                <el-button
                        v-if="task.run_status === 'running'"
                        type="warning"
                        @click="handleStopRun"
                >
                    <el-icon>
                        <VideoPause/>
                    </el-icon>
                    停止
                </el-button>
                <el-button @click="openEditDialog">
                    <el-icon>
                        <Edit/>
                    </el-icon>
                    编辑
                </el-button>
                <el-button
                        :type="task.enabled ? 'warning' : 'success'"
                        @click="handleToggle"
                >
                    {{ task.enabled ? '停用' : '启用' }}
                </el-button>
                <el-button type="danger" @click="handleDelete">
                    <el-icon>
                        <Delete/>
                    </el-icon>
                    删除
                </el-button>
            </div>
        </div>

        <template v-if="task">
            <!-- 基本信息卡片 -->
            <el-card shadow="never">
                <template #header>
                    <div class="card-header">
                        <el-icon>
                            <InfoFilled/>
                        </el-icon>
                        <span>基本信息</span>
                    </div>
                </template>
                <el-descriptions :column="2" border>
                    <el-descriptions-item label="任务 ID">
                        <span class="mono">{{ task.task_id }}</span>
                    </el-descriptions-item>
                    <el-descriptions-item label="类型">
                        <el-tag
                                :color="typeMeta[task.type].bgColor"
                                :style="{ color: typeMeta[task.type].color, border: 'none' }"
                                size="small"
                        >
                            {{ typeMeta[task.type].label }}
                        </el-tag>
                    </el-descriptions-item>
                    <el-descriptions-item label="状态">
                        <div class="status-cell">
                            <span :class="['status-dot', `dot-${task.run_status}`]"></span>
                            <span>{{ statusLabel[task.run_status] }}</span>
                        </div>
                    </el-descriptions-item>
                    <el-descriptions-item label="脚本文件">
                        <div class="script-file-cell">
                            <el-tag
                                    v-if="task.has_script"
                                    type="success"
                                    size="small"
                                    effect="plain"
                            >已上传
                            </el-tag>
                            <el-tag v-else type="info" size="small" effect="plain">未上传</el-tag>
                            <el-button
                                    v-if="task.type !== 'command'"
                                    size="small"
                                    text
                                    type="primary"
                                    @click="uploadDialogVisible = true"
                            >
                                {{ task.has_script ? '替换文件' : '上传文件' }}
                            </el-button>
                        </div>
                    </el-descriptions-item>
                    <el-descriptions-item label="命令模板" :span="2">
                        <code class="command-code">{{ task.command_template || '—' }}</code>
                    </el-descriptions-item>
                    <el-descriptions-item label="工作目录" :span="2">
                        <span class="mono">{{ task.work_dir || '工作区根目录' }}</span>
                    </el-descriptions-item>
                    <el-descriptions-item label="标签" :span="2">
                        <el-tag
                                v-for="tag in task.tags"
                                :key="tag"
                                size="small"
                                effect="plain"
                                style="margin-right: 4px"
                        >{{ tag }}
                        </el-tag>
                        <span v-if="!task.tags?.length" class="no-data">—</span>
                    </el-descriptions-item>
                    <el-descriptions-item label="创建时间">
                        {{ formatDateTime(task.created_at) }}
                    </el-descriptions-item>
                    <el-descriptions-item label="更新时间">
                        {{ formatDateTime(task.updated_at) }}
                    </el-descriptions-item>
                </el-descriptions>
            </el-card>

            <!-- 参数配置卡片 -->
            <el-card shadow="never" style="margin-top: 16px">
                <template #header>
                    <div class="card-header">
                        <el-icon>
                            <Grid/>
                        </el-icon>
                        <span>参数配置</span>
                        <el-tag
                                :type="paramsData?.mode === 'advanced' ? 'warning' : ''"
                                size="small"
                                effect="plain"
                                style="margin-left: 8px"
                        >
                            {{ paramsData?.mode === 'advanced' ? '高级模式' : '简单模式' }}
                        </el-tag>
                        <div class="card-header-actions">
                            <el-button size="small" @click="openParamsEditDialog">
                                <el-icon>
                                    <Edit/>
                                </el-icon>
                                编辑参数
                            </el-button>
                            <el-button size="small" type="primary" @click="openPreviewDialog">
                                <el-icon>
                                    <View/>
                                </el-icon>
                                预览命令
                            </el-button>
                        </div>
                    </div>
                </template>

                <div v-if="paramsData?.schema?.params?.length">
                    <el-table :data="paramsData.schema.params" size="small" border>
                        <el-table-column label="参数名" prop="name" width="160">
                            <template #default="{ row }">
                                <span class="mono">{{ row.name }}</span>
                            </template>
                        </el-table-column>
                        <el-table-column label="显示名" prop="display_name" width="140"/>
                        <el-table-column label="类型" width="110" align="center">
                            <template #default="{ row }">
                                <el-tag size="small" effect="plain">{{ typeLabels[row.type] || row.type }}</el-tag>
                            </template>
                        </el-table-column>
                        <el-table-column label="必填" width="70" align="center">
                            <template #default="{ row }">
                                <el-icon v-if="row.required" color="#22c55e">
                                    <Check/>
                                </el-icon>
                                <span v-else class="no-data">—</span>
                            </template>
                        </el-table-column>
                        <el-table-column label="默认值" min-width="150">
                            <template #default="{ row }">
                <span v-if="row.default !== undefined && row.default !== ''" class="mono">
                  {{ row.sensitive ? '••••••' : row.default }}
                </span>
                                <span v-else class="no-data">—</span>
                            </template>
                        </el-table-column>
                        <el-table-column
                                v-if="paramsData.mode === 'advanced'"
                                label="拼接规则"
                                width="130"
                                align="center"
                        >
                            <template #default="{ row }">
                                <el-tag v-if="row.concat_rule" size="small" effect="plain" type="info">
                                    {{ concatRuleLabels[row.concat_rule] || row.concat_rule }}
                                </el-tag>
                                <span v-else class="no-data">—</span>
                            </template>
                        </el-table-column>
                        <el-table-column
                                v-if="paramsData.mode === 'advanced'"
                                label="拼接键"
                                width="140"
                        >
                            <template #default="{ row }">
                                <span v-if="row.concat_key" class="mono">{{ row.concat_key }}</span>
                                <span v-else class="no-data">—</span>
                            </template>
                        </el-table-column>
                        <el-table-column
                                v-if="paramsData.mode === 'advanced'"
                                label="标记"
                                width="100"
                                align="center"
                        >
                            <template #default="{ row }">
                                <el-tag v-if="row.sensitive" size="small" type="danger" effect="plain">敏感</el-tag>
                                <el-tag v-if="row.hidden" size="small" type="info" effect="plain">隐藏</el-tag>
                                <span v-if="!row.sensitive && !row.hidden" class="no-data">—</span>
                            </template>
                        </el-table-column>
                    </el-table>
                </div>
                <el-empty v-else description="暂无参数配置" :image-size="60">
                    <el-button size="small" @click="openParamsEditDialog">
                        配置参数
                    </el-button>
                </el-empty>
            </el-card>

            <!-- 入口配置 -->
            <el-card shadow="never" style="margin-top: 16px">
                <template #header>
                    <div class="card-header">
                        <el-icon>
                            <Setting/>
                        </el-icon>
                        <span>入口配置</span>
                    </div>
                </template>
                <el-descriptions :column="1" border>
                    <el-descriptions-item
                            v-for="(val, key) in task.entry_config"
                            :key="key"
                            :label="entryLabelMap[String(key)] || String(key)"
                    >
                        <span class="mono">{{ typeof val === 'object' ? JSON.stringify(val) : val }}</span>
                    </el-descriptions-item>
                    <el-descriptions-item v-if="!Object.keys(task.entry_config || {}).length">
                        <span class="no-data">暂无配置</span>
                    </el-descriptions-item>
                </el-descriptions>
            </el-card>

            <!-- 守护配置 -->
            <el-card shadow="never" style="margin-top: 16px">
                <template #header>
                    <div class="card-header">
                        <el-icon>
                            <Shield/>
                        </el-icon>
                        <span>守护与健康检查</span>
                    </div>
                </template>
                <el-descriptions :column="2" border>
                    <el-descriptions-item label="守护开启">
                        <el-tag
                                :type="task.daemon_config?.enabled ? 'success' : 'info'"
                                size="small"
                                effect="plain"
                        >{{ task.daemon_config?.enabled ? '已开启' : '未开启' }}
                        </el-tag>
                    </el-descriptions-item>
                    <el-descriptions-item label="重启间隔">
                        {{ task.daemon_config?.restart_interval || '—' }}秒
                    </el-descriptions-item>
                    <el-descriptions-item label="最大重启次数">
                        {{ task.daemon_config?.max_restarts ?? '—' }}
                    </el-descriptions-item>
                    <el-descriptions-item label="熔断重置时间">
                        {{ task.daemon_config?.reset_time || '—' }}秒
                    </el-descriptions-item>
                    <el-descriptions-item label="健康检查类型">
                        {{
                        task.health_check_config?.type === 'http'
                            ? 'HTTP 探活'
                            : task.health_check_config?.type === 'process'
                                ? '进程存活'
                                : '未配置'
                        }}
                    </el-descriptions-item>
                    <el-descriptions-item
                            v-if="task.health_check_config?.type === 'http'"
                            label="探活 URL"
                    >
                        <span class="mono">{{ task.health_check_config?.url || '—' }}</span>
                    </el-descriptions-item>
                </el-descriptions>
            </el-card>

            <!-- 环境变量 -->
            <el-card shadow="never" style="margin-top: 16px">
                <template #header>
                    <div class="card-header">
                        <el-icon>
                            <Key/>
                        </el-icon>
                        <span>自定义环境变量</span>
                    </div>
                </template>
                <el-descriptions :column="1" border>
                    <el-descriptions-item
                            v-for="(val, key) in task.env_vars"
                            :key="key"
                            :label="String(key)"
                    >
                        <span class="mono">{{ val }}</span>
                    </el-descriptions-item>
                    <el-descriptions-item v-if="!Object.keys(task.env_vars || {}).length">
                        <span class="no-data">暂无环境变量</span>
                    </el-descriptions-item>
                </el-descriptions>
            </el-card>

            <!-- 最近运行 -->
            <el-card shadow="never" style="margin-top: 16px">
                <template #header>
                    <div class="card-header">
                        <el-icon>
                            <VideoPlay/>
                        </el-icon>
                        <span>最近运行</span>
                    </div>
                </template>
                <el-table
                        :data="task.recent_runs || []"
                        empty-text="暂无运行记录"
                        size="small"
                        @row-click="(row) => $router.push(`/runs/${row.run_id}`)"
                        row-class-name="clickable-row"
                >
                    <el-table-column prop="run_id" label="Run ID" width="300">
                        <template #default="{ row }">
                            <span class="mono">{{ row.run_id.slice(0, 8) }}...</span>
                        </template>
                    </el-table-column>
                    <el-table-column label="状态" width="100" align="center">
                        <template #default="{ row }">
              <span :class="['run-result', `result-${row.status}`]">
                {{ runStatusLabel[row.status] || row.status }}
              </span>
                        </template>
                    </el-table-column>
                    <el-table-column label="触发方式" width="100" align="center">
                        <template #default="{ row }">
                            {{ triggerLabel[row.trigger_type] || row.trigger_type }}
                        </template>
                    </el-table-column>
                    <el-table-column label="开始时间" width="180">
                        <template #default="{ row }">{{ formatDateTime(row.started_at) }}</template>
                    </el-table-column>
                    <el-table-column label="耗时" width="120">
                        <template #default="{ row }">
                            {{ row.duration_ms ? (row.duration_ms / 1000).toFixed(1) + 's' : '—' }}
                        </template>
                    </el-table-column>
                    <el-table-column label="退出码" width="90" align="center">
                        <template #default="{ row }">
              <span :class="{ 'exit-error': row.exit_code && row.exit_code !== 0 }">
                {{ row.exit_code ?? '—' }}
              </span>
                        </template>
                    </el-table-column>
                </el-table>
            </el-card>
        </template>

        <!-- ========== 编辑任务弹窗 ========== -->
        <el-dialog
                v-model="editDialogVisible"
                title="编辑任务"
                width="680px"
                :close-on-click-modal="false"
                destroy-on-close
        >
            <el-form
                    ref="editFormRef"
                    :model="editForm"
                    :rules="editFormRules"
                    label-width="110px"
                    label-position="right"
            >
                <el-divider content-position="left">基本信息</el-divider>
                <el-form-item label="任务名称" prop="name">
                    <el-input v-model="editForm.name" placeholder="输入任务名称" maxlength="100" show-word-limit/>
                </el-form-item>
                <el-form-item label="任务类型">
                    <el-tag :color="typeMeta[task?.type]?.bgColor"
                            :style="{ color: typeMeta[task?.type]?.color, border: 'none' }">
                        {{ typeMeta[task?.type]?.label }}
                    </el-tag>
                    <span class="form-hint">类型创建后不可修改</span>
                </el-form-item>
                <el-form-item label="标签">
                    <div class="tags-editor">
                        <el-tag
                                v-for="(tag, idx) in editForm.tags"
                                :key="idx"
                                closable
                                @close="removeTag(idx)"
                                style="margin-right: 6px; margin-bottom: 4px"
                        >{{ tag }}
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

                <el-divider content-position="left">{{ typeMeta[task?.type]?.label }} 配置</el-divider>
                <el-form-item
                        label="命令模板"
                        :prop="task?.type === 'command' || task?.type === 'project' ? 'command_template' : ''"
                >
                    <el-input
                            v-model="editForm.command_template"
                            type="textarea"
                            :rows="4"
                            :placeholder="commandPlaceholder"
                    />
                </el-form-item>
                <template v-if="task?.type === 'python_script'">
                    <el-form-item label="Python 解释器">
                        <el-input v-model="editForm.entry_config.python_path" placeholder="留空使用全局默认"/>
                    </el-form-item>
                </template>
                <template v-if="task?.type === 'executable'">
                    <el-form-item label="隐藏窗口">
                        <el-switch v-model="editForm.entry_config.no_window"/>
                        <span class="form-hint">后台静默运行</span>
                    </el-form-item>
                </template>

                <el-divider content-position="left">其他</el-divider>
                <el-form-item label="工作目录">
                    <el-input v-model="editForm.work_dir" placeholder="留空则使用工作区根目录"/>
                </el-form-item>

                <!-- 守护配置 -->
                <el-divider content-position="left">守护配置</el-divider>
                <el-form-item label="守护开启">
                    <el-switch v-model="editForm.daemon_config.enabled"/>
                </el-form-item>
                <template v-if="editForm.daemon_config.enabled">
                    <el-form-item label="重启间隔(秒)">
                        <el-input-number v-model="editForm.daemon_config.restart_interval" :min="1" :max="3600"/>
                    </el-form-item>
                    <el-form-item label="最大重启次数">
                        <el-input-number v-model="editForm.daemon_config.max_restarts" :min="1" :max="100"/>
                    </el-form-item>
                    <el-form-item label="熔断重置(秒)">
                        <el-input-number v-model="editForm.daemon_config.reset_time" :min="10" :max="86400"/>
                    </el-form-item>
                </template>

                <!-- 健康检查 -->
                <el-divider content-position="left">健康检查</el-divider>
                <el-form-item label="检查类型">
                    <el-radio-group v-model="editForm.health_check_config.type">
                        <el-radio value="process">进程存活</el-radio>
                        <el-radio value="http">HTTP 探活</el-radio>
                    </el-radio-group>
                </el-form-item>
                <template v-if="editForm.health_check_config.type === 'http'">
                    <el-form-item label="探活 URL">
                        <el-input v-model="editForm.health_check_config.url"
                                  placeholder="http://127.0.0.1:8080/health"/>
                    </el-form-item>
                    <el-form-item label="探活间隔(秒)">
                        <el-input-number v-model="editForm.health_check_config.interval" :min="5" :max="300"/>
                    </el-form-item>
                    <el-form-item label="超时(秒)">
                        <el-input-number v-model="editForm.health_check_config.timeout" :min="1" :max="30"/>
                    </el-form-item>
                    <el-form-item label="连续失败次数">
                        <el-input-number v-model="editForm.health_check_config.fail_count" :min="1" :max="10"/>
                    </el-form-item>
                </template>

                <!-- 环境变量 -->
                <el-divider content-position="left">自定义环境变量</el-divider>
                <div class="env-vars-editor">
                    <div v-for="(item, idx) in editForm.env_vars_list" :key="idx" class="env-var-row">
                        <el-input v-model="item.key" placeholder="变量名" style="width: 200px"/>
                        <span class="env-eq">=</span>
                        <el-input v-model="item.value" placeholder="变量值" style="flex: 1"/>
                        <el-button type="danger" text @click="editForm.env_vars_list.splice(idx, 1)">
                            <el-icon>
                                <Delete/>
                            </el-icon>
                        </el-button>
                    </div>
                    <el-button size="small" @click="editForm.env_vars_list.push({ key: '', value: '' })">
                        <el-icon>
                            <Plus/>
                        </el-icon>
                        添加变量
                    </el-button>
                </div>
            </el-form>

            <template #footer>
                <el-button @click="editDialogVisible = false">取消</el-button>
                <el-button type="primary" :loading="submitting" @click="handleEditSubmit">保存</el-button>
            </template>
        </el-dialog>

        <!-- ========== 参数编辑弹窗 ========== -->
        <el-dialog
                v-model="paramsEditVisible"
                title="参数配置"
                width="780px"
                :close-on-click-modal="false"
                destroy-on-close
        >
            <!-- 模式切换 -->
            <div class="mode-switch">
                <span class="mode-label">模式：</span>
                <el-radio-group v-model="paramsEditMode" @change="onModeChange">
                    <el-radio-button value="simple">
                        简单模式
                        <el-tooltip content="从命令模板 {param} 占位符自动生成表单" placement="top">
                            <el-icon style="margin-left: 4px">
                                <QuestionFilled/>
                            </el-icon>
                        </el-tooltip>
                    </el-radio-button>
                    <el-radio-button value="advanced">
                        高级模式
                        <el-tooltip content="手工定义参数 Schema，支持多种拼接规则" placement="top">
                            <el-icon style="margin-left: 4px">
                                <QuestionFilled/>
                            </el-icon>
                        </el-tooltip>
                    </el-radio-button>
                </el-radio-group>
                <el-button
                        v-if="paramsEditMode === 'simple'"
                        size="small"
                        @click="handleReParse"
                        :loading="parsing"
                        style="margin-left: 12px"
                >
                    <el-icon>
                        <Refresh/>
                    </el-icon>
                    从模板重新解析
                </el-button>
            </div>

            <!-- 参数列表 -->
            <div class="params-list">
                <div
                        v-for="(p, idx) in paramsEditSchema"
                        :key="idx"
                        class="param-card"
                >
                    <div class="param-card-header">
            <span class="param-card-name">
              <el-icon v-if="p.sensitive" color="#ef4444"><Lock/></el-icon>
              <el-icon v-if="p.hidden" color="#94a3b8"><Hide/></el-icon>
              {{ p.name || `参数 ${idx + 1}` }}
            </span>
                        <div class="param-card-actions">
                            <el-button size="small" text type="primary" @click="toggleParamExpand(idx)">
                                {{ expandedParams.has(idx) ? '收起' : '展开' }}
                            </el-button>
                            <el-button
                                    size="small"
                                    text
                                    type="danger"
                                    @click="paramsEditSchema.splice(idx, 1)"
                            >
                                <el-icon>
                                    <Delete/>
                                </el-icon>
                            </el-button>
                        </div>
                    </div>

                    <!-- 展开的详细编辑 -->
                    <div v-if="expandedParams.has(idx)" class="param-card-body">
                        <el-form label-width="100px" size="small">
                            <el-row :gutter="16">
                                <el-col :span="12">
                                    <el-form-item label="参数名">
                                        <el-input v-model="p.name" placeholder="英文名，如 url"
                                                  :disabled="paramsEditMode === 'simple'"/>
                                    </el-form-item>
                                </el-col>
                                <el-col :span="12">
                                    <el-form-item label="显示名">
                                        <el-input v-model="p.display_name" placeholder="UI 展示名称"/>
                                    </el-form-item>
                                </el-col>
                            </el-row>

                            <el-row :gutter="16">
                                <el-col :span="12">
                                    <el-form-item label="类型">
                                        <el-select v-model="p.type" style="width: 100%">
                                            <el-option label="字符串 (string)" value="string"/>
                                            <el-option label="数字 (number)" value="number"/>
                                            <el-option label="布尔 (boolean)" value="boolean"/>
                                            <el-option label="下拉选择 (select)" value="select"/>
                                            <el-option label="文件 (file)" value="file"/>
                                            <el-option label="目录 (directory)" value="directory"/>
                                        </el-select>
                                    </el-form-item>
                                </el-col>
                                <el-col :span="12">
                                    <el-form-item label="必填">
                                        <el-switch v-model="p.required"/>
                                    </el-form-item>
                                </el-col>
                            </el-row>

                            <el-form-item label="默认值">
                                <el-switch v-if="p.type === 'boolean'" v-model="p.default"/>
                                <el-input-number
                                        v-else-if="p.type === 'number'"
                                        v-model="p.default"
                                        controls-position="right"
                                        style="width: 100%"
                                />
                                <el-input v-else v-model="p.default" placeholder="默认值"/>
                            </el-form-item>

                            <el-form-item label="提示文案">
                                <el-input v-model="p.placeholder" placeholder="placeholder"/>
                            </el-form-item>

                            <!-- select 选项 -->
                            <el-form-item v-if="p.type === 'select'" label="下拉选项">
                                <div class="select-options-editor">
                                    <el-tag
                                            v-for="(opt, oi) in p.select_options"
                                            :key="oi"
                                            closable
                                            @close="p.select_options.splice(oi, 1)"
                                            style="margin-right: 4px; margin-bottom: 4px"
                                    >{{ opt }}
                                    </el-tag>
                                    <el-input
                                            v-if="selectInputVisible[`${idx}`]"
                                            :ref="el => { if (el) selectInputRefs[idx] = el }"
                                            v-model="selectInputVal"
                                            size="small"
                                            style="width: 120px"
                                            @keyup.enter="addSelectOption(p, idx)"
                                            @blur="addSelectOption(p, idx)"
                                    />
                                    <el-button v-else size="small" @click="showSelectInput(idx)">
                                        <el-icon>
                                            <Plus/>
                                        </el-icon>
                                    </el-button>
                                </div>
                            </el-form-item>

                            <!-- 高级模式额外字段 -->
                            <template v-if="paramsEditMode === 'advanced'">
                                <el-divider content-position="left">拼接规则</el-divider>
                                <el-row :gutter="16">
                                    <el-col :span="12">
                                        <el-form-item label="拼接规则">
                                            <el-select v-model="p.concat_rule" style="width: 100%">
                                                <el-option label="--key value" value="--key value"/>
                                                <el-option label="--key=value" value="--key=value"/>
                                                <el-option label="flag（布尔标志）" value="flag"/>
                                                <el-option label="仅值" value="value_only"/>
                                                <el-option label="环境变量注入" value="env_var"/>
                                            </el-select>
                                        </el-form-item>
                                    </el-col>
                                    <el-col :span="12">
                                        <el-form-item
                                                label="拼接键"
                                                v-if="!['flag', 'value_only', 'env_var'].includes(p.concat_rule)"
                                        >
                                            <el-input v-model="p.concat_key" :placeholder="`--${p.name}`"/>
                                        </el-form-item>
                                        <el-form-item label="标志文本" v-if="p.concat_rule === 'flag'">
                                            <el-input v-model="p.concat_key" placeholder="--force"/>
                                        </el-form-item>
                                    </el-col>
                                </el-row>
                                <el-row :gutter="16">
                                    <el-col :span="12">
                                        <el-form-item label="敏感值">
                                            <el-switch v-model="p.sensitive"/>
                                            <span class="field-hint">密码/Token，输入框遮罩，日志脱敏</span>
                                        </el-form-item>
                                    </el-col>
                                    <el-col :span="12">
                                        <el-form-item label="默认隐藏">
                                            <el-switch v-model="p.hidden"/>
                                            <span class="field-hint">高级参数，默认折叠</span>
                                        </el-form-item>
                                    </el-col>
                                </el-row>
                            </template>
                        </el-form>
                    </div>
                </div>

                <!-- 添加参数按钮（高级模式） -->
                <el-button
                        v-if="paramsEditMode === 'advanced'"
                        class="add-param-btn"
                        @click="addAdvancedParam"
                >
                    <el-icon>
                        <Plus/>
                    </el-icon>
                    添加参数
                </el-button>
            </div>

            <template #footer>
                <el-button @click="paramsEditVisible = false">取消</el-button>
                <el-button type="primary" :loading="savingParams" @click="handleSaveParams">
                    保存参数配置
                </el-button>
            </template>
        </el-dialog>

        <!-- ========== 命令预览弹窗 ========== -->
        <el-dialog
                v-model="previewVisible"
                title="预览最终命令"
                width="720px"
                :close-on-click-modal="false"
                destroy-on-close
        >
            <div class="preview-content">
                <div class="preview-form">
                    <h4>填写参数值</h4>
                    <el-form label-width="140px" size="default">
                        <ParamFormRenderer
                                :schema="paramsData?.schema || { params: [] }"
                                v-model="previewValues"
                        />
                    </el-form>
                </div>

                <el-divider/>

                <div class="preview-result">
                    <div class="preview-result-header">
                        <h4>最终命令</h4>
                        <el-button size="small" @click="doRender" :loading="rendering">
                            <el-icon>
                                <Refresh/>
                            </el-icon>
                            刷新
                        </el-button>
                    </div>
                    <div class="preview-command-box">
                        <code v-if="renderedCommand">{{ renderedCommand }}</code>
                        <span v-else class="no-data">点击「刷新」生成命令</span>
                    </div>
                    <div v-if="renderedEnvVars && Object.keys(renderedEnvVars).length" class="preview-env">
                        <h4>注入环境变量</h4>
                        <el-descriptions :column="1" size="small" border>
                            <el-descriptions-item
                                    v-for="(v, k) in renderedEnvVars"
                                    :key="k"
                                    :label="k"
                            >
                                <span class="mono">{{ v }}</span>
                            </el-descriptions-item>
                        </el-descriptions>
                    </div>
                </div>
            </div>

            <template #footer>
                <el-button @click="previewVisible = false">关闭</el-button>
            </template>
        </el-dialog>

        <!-- ========== 上传文件弹窗 ========== -->
        <el-dialog
                v-model="uploadDialogVisible"
                title="上传脚本文件"
                width="480px"
                :close-on-click-modal="false"
                destroy-on-close
        >
            <div class="upload-dialog-content">
                <el-upload
                        :auto-upload="false"
                        :limit="1"
                        :accept="uploadAccept"
                        :on-change="onUploadFileChange"
                        :file-list="uploadFileList"
                        :on-remove="onUploadFileRemove"
                        drag
                >
                    <el-icon :size="48" color="#c0c4cc">
                        <UploadFilled/>
                    </el-icon>
                    <div style="margin-top: 8px">
                        将{{ uploadFileTypeLabel }}文件拖到此处，或<em>点击上传</em>
                    </div>
                    <template #tip>
                        <div class="upload-tip">{{ uploadTip }}</div>
                    </template>
                </el-upload>
            </div>
            <template #footer>
                <el-button @click="uploadDialogVisible = false">取消</el-button>
                <el-button type="primary" :loading="uploading" :disabled="!uploadFile" @click="handleUpload">
                    上传
                </el-button>
            </template>
        </el-dialog>
        <!-- ========== 运行参数弹窗 ========== -->
        <el-dialog
                v-model="runDialogVisible"
                :title="`运行 - ${task?.name || ''}`"
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
import {ref, reactive, computed, nextTick, onMounted} from 'vue'
import {useRoute, useRouter} from 'vue-router'
import {ElMessage, ElMessageBox} from 'element-plus'
import {
    getTask, updateTask, deleteTask, toggleTask, uploadScript,
} from '../api/tasks'
import {
    getParams, saveParams, parseParams, renderCommand,
} from '../api/params'
import {startRun, stopRun, getRuns} from '../api/runs'
import ParamFormRenderer from '../components/ParamFormRenderer.vue'


const route = useRoute()
const router = useRouter()

// ========== 数据 ==========
const loading = ref(false)
const task = ref(null)
const paramsData = ref(null)

const typeMeta = {
    command: {label: '命令行', color: '#3b82f6', bgColor: '#eff6ff'},
    python_script: {label: 'Python', color: '#22c55e', bgColor: '#f0fdf4'},
    project: {label: '多文件', color: '#f59e0b', bgColor: '#fffbeb'},
    executable: {label: 'EXE', color: '#8b5cf6', bgColor: '#f5f3ff'},
}

const statusLabel = {running: '运行中', idle: '空闲', disabled: '已停用', failed: '失败'}
const runStatusLabel = {
    success: '成功', failed: '失败', stopped: '已停止',
    running: '运行中', pending: '等待中', skipped: '已跳过',
}
const triggerLabel = {manual: '手动', cron: '定时', interval: '周期', startup: '开机'}
const entryLabelMap = {
    script_path: '脚本路径', project_dir: '项目目录', exe_path: 'EXE 路径',
    python_path: 'Python 解释器', no_window: '隐藏窗口',
}

const typeLabels = {
    string: '字符串', number: '数字', boolean: '布尔',
    select: '选择', file: '文件', directory: '目录',
}

const concatRuleLabels = {
    '--key value': 'K V', '--key=value': 'K=V', flag: '标志',
    value_only: '仅值', env_var: '环境变量',
}

async function loadTask() {
    loading.value = true
    try {
        task.value = await getTask(route.params.id)
        // 同时加载参数配置
        try {
            paramsData.value = await getParams(route.params.id)
        } catch {
            paramsData.value = null
        }
    } catch {
        ElMessage.error('任务不存在')
        router.push('/tasks')
    } finally {
        loading.value = false
    }
}

function formatDateTime(isoStr) {
    if (!isoStr) return '—'
    return new Date(isoStr).toLocaleString('zh-CN')
}

// ========== 启用/停用 ==========
async function handleToggle() {
    try {
        const res = await toggleTask(task.value.task_id)
        ElMessage.success(res.message)
        loadTask()
    } catch {
    }
}

// ========== 删除 ==========
async function handleDelete() {
    try {
        await ElMessageBox.confirm(
            `确定要删除任务「${task.value.name}」吗？该操作不可恢复。`,
            '删除任务',
            {
                type: 'warning',
                confirmButtonText: '删除',
                cancelButtonText: '取消',
                confirmButtonClass: 'el-button--danger'
            }
        )
        await deleteTask(task.value.task_id)
        ElMessage.success('任务已删除')
        router.push('/tasks')
    } catch {
    }
}

// ========== 运行控制 ==========
const runDialogVisible = ref(false)
const runParamSchema = ref({params: []})
const runParamValues = ref({})
const runStarting = ref(false)
const runFormRef = ref()

function openRunDialog() {
    runParamValues.value = {}
    runStarting.value = false
    if (paramsData.value?.schema) {
        runParamSchema.value = paramsData.value.schema
    } else {
        runParamSchema.value = {params: []}
    }
    runDialogVisible.value = true
}

async function confirmRun() {
    runStarting.value = true
    try {
        const values = runFormRef.value?.getValues?.() || {}
        const res = await startRun(task.value.task_id, values)
        ElMessage.success('运行已启动')
        runDialogVisible.value = false
        router.push(`/runs/${res.run_id}`)
    } catch {
    } finally {
        runStarting.value = false
    }
}

async function handleStopRun() {
    try {
        const res = await getRuns({task_id: task.value.task_id, status: 'running', page_size: 1})
        if (res.items?.length) {
            await stopRun(res.items[0].run_id)
            ElMessage.success('停止指令已发送')
            loadTask()
        } else {
            ElMessage.info('没有运行中的实例')
        }
    } catch {
    }
}

// ========== 编辑弹窗 ==========
const editDialogVisible = ref(false)
const submitting = ref(false)
const editFormRef = ref()
const tagInputVisible = ref(false)
const tagInputValue = ref('')
const tagInputRef = ref()

const editForm = reactive({
    name: '', command_template: '', entry_config: {}, work_dir: '', tags: [],
    daemon_config: {enabled: false, restart_interval: 5, max_restarts: 5, reset_time: 600},
    health_check_config: {type: 'process', url: '', interval: 30, timeout: 5, fail_count: 3},
    env_vars_list: [],
})

const editFormRules = {
    name: [{required: true, message: '请输入任务名称', trigger: 'blur'}],
    command_template: [{
        validator: (rule, value, callback) => {
            const t = task.value?.type
            if ((t === 'command' || t === 'project') && !value.trim()) {
                callback(new Error('必须填写命令模板'))
            } else {
                callback()
            }
        },
        trigger: 'blur',
    }],
}

const commandPlaceholder = computed(() => {
    const t = task.value?.type
    if (t === 'command') return '如：python script.py --url {url} --count {count}'
    if (t === 'python_script') return '如：{python} script.py --url {url}（留空则自动生成）'
    if (t === 'project') return '如：python main.py --input {input_file}'
    if (t === 'executable') return '如：--input {input_file} --output {output_dir}'
    return ''
})

function showTagInput() {
    tagInputVisible.value = true;
    nextTick(() => tagInputRef.value?.focus())
}

function addTag() {
    const val = tagInputValue.value.trim()
    if (val && !editForm.tags.includes(val)) editForm.tags.push(val)
    tagInputVisible.value = false;
    tagInputValue.value = ''
}

function removeTag(idx) {
    editForm.tags.splice(idx, 1)
}

function openEditDialog() {
    const t = task.value
    if (!t) return
    editForm.name = t.name
    editForm.command_template = t.command_template || ''
    editForm.entry_config = {...(t.entry_config || {})}
    editForm.work_dir = t.work_dir || ''
    editForm.tags = [...(t.tags || [])]
    const dc = t.daemon_config || {}
    editForm.daemon_config = {
        enabled: dc.enabled || false,
        restart_interval: dc.restart_interval || 5,
        max_restarts: dc.max_restarts || 5,
        reset_time: dc.reset_time || 600
    }
    const hc = t.health_check_config || {}
    editForm.health_check_config = {
        type: hc.type || 'process',
        url: hc.url || '',
        interval: hc.interval || 30,
        timeout: hc.timeout || 5,
        fail_count: hc.fail_count || 3
    }
    editForm.env_vars_list = Object.entries(t.env_vars || {}).map(([k, v]) => ({key: k, value: v}))
    editDialogVisible.value = true
}

async function handleEditSubmit() {
    await editFormRef.value.validate()
    submitting.value = true
    try {
        const envVars = {}
        for (const item of editForm.env_vars_list) {
            if (item.key.trim()) envVars[item.key.trim()] = item.value
        }
        await updateTask(task.value.task_id, {
            name: editForm.name, command_template: editForm.command_template,
            entry_config: editForm.entry_config, work_dir: editForm.work_dir, tags: editForm.tags,
            daemon_config: editForm.daemon_config, health_check_config: editForm.health_check_config,
            env_vars: envVars,
        })
        ElMessage.success('任务更新成功')
        editDialogVisible.value = false
        loadTask()
    } catch {
    } finally {
        submitting.value = false
    }
}

// ========== 参数编辑弹窗 ==========
const paramsEditVisible = ref(false)
const paramsEditMode = ref('simple')
const paramsEditSchema = ref([])
const expandedParams = ref(new Set())
const savingParams = ref(false)
const parsing = ref(false)

// select 选项编辑
const selectInputVisible = reactive({})
const selectInputVal = ref('')
const selectInputRefs = reactive({})

function showSelectInput(idx) {
    selectInputVisible[`${idx}`] = true
    nextTick(() => selectInputRefs[idx]?.focus())
}

function addSelectOption(p, idx) {
    const val = selectInputVal.value.trim()
    if (val && !p.select_options.includes(val)) p.select_options.push(val)
    selectInputVisible[`${idx}`] = false
    selectInputVal.value = ''
}

function toggleParamExpand(idx) {
    if (expandedParams.value.has(idx)) {
        expandedParams.value.delete(idx)
    } else {
        expandedParams.value.add(idx)
    }
    // 触发响应式
    expandedParams.value = new Set(expandedParams.value)
}

function openParamsEditDialog() {
    if (paramsData.value) {
        paramsEditMode.value = paramsData.value.mode
        paramsEditSchema.value = JSON.parse(JSON.stringify(paramsData.value.schema?.params || []))
    } else {
        paramsEditMode.value = 'simple'
        paramsEditSchema.value = []
    }
    expandedParams.value = new Set()
    paramsEditVisible.value = true
}

function onModeChange() {
    // 切换模式时保留参数，但清空高级模式专属字段
    if (paramsEditMode.value === 'simple') {
        paramsEditSchema.value.forEach(p => {
            delete p.concat_rule;
            delete p.concat_key;
            delete p.sensitive;
            delete p.hidden
        })
    }
}

async function handleReParse() {
    parsing.value = true
    try {
        const schema = await parseParams(task.value.task_id)
        paramsEditSchema.value = schema.params || []
        expandedParams.value = new Set()
        ElMessage.success(`已解析出 ${paramsEditSchema.value.length} 个参数`)
    } catch {
    } finally {
        parsing.value = false
    }
}

function addAdvancedParam() {
    paramsEditSchema.value.push({
        name: '', display_name: '', type: 'string', required: false,
        default: '', placeholder: '', select_options: [], file_scope: '',
        concat_rule: '--key value', concat_key: '', sensitive: false, hidden: false,
    })
    expandedParams.value = new Set([paramsEditSchema.value.length - 1])
}

async function handleSaveParams() {
    // 校验参数名
    for (const p of paramsEditSchema.value) {
        if (!p.name?.trim()) {
            ElMessage.warning('每个参数必须填写参数名')
            return
        }
    }
    // 检查重名
    const names = paramsEditSchema.value.map(p => p.name)
    if (new Set(names).size !== names.length) {
        ElMessage.warning('参数名不能重复')
        return
    }

    savingParams.value = true
    try {
        await saveParams(task.value.task_id, {
            mode: paramsEditMode.value,
            schema: {params: paramsEditSchema.value},
        })
        ElMessage.success('参数配置已保存')
        paramsEditVisible.value = false
        // 重新加载
        paramsData.value = await getParams(task.value.task_id)
    } catch {
    } finally {
        savingParams.value = false
    }
}

// ========== 命令预览 ==========
const previewVisible = ref(false)
const previewValues = ref({})
const renderedCommand = ref('')
const renderedEnvVars = ref({})
const rendering = ref(false)

function openPreviewDialog() {
    previewValues.value = {}
    renderedCommand.value = ''
    renderedEnvVars.value = {}
    previewVisible.value = true
    // 自动渲染一次
    nextTick(() => doRender())
}

async function doRender() {
    rendering.value = true
    try {
        const res = await renderCommand(task.value.task_id, previewValues.value)
        renderedCommand.value = res.command
        renderedEnvVars.value = res.env_vars || {}
    } catch {
    } finally {
        rendering.value = false
    }
}

// ========== 上传文件 ==========
const uploadDialogVisible = ref(false)
const uploading = ref(false)
const uploadFile = ref(null)
const uploadFileList = ref([])

const uploadAccept = computed(() => {
    const t = task.value?.type
    if (t === 'python_script') return '.py'
    if (t === 'project') return '.zip'
    if (t === 'executable') return '.exe'
    return ''
})
const uploadFileTypeLabel = computed(() => {
    const t = task.value?.type
    if (t === 'python_script') return '.py'
    if (t === 'project') return '.zip'
    if (t === 'executable') return '.exe'
    return ''
})
const uploadTip = computed(() => {
    const t = task.value?.type
    if (t === 'python_script') return '只能上传 .py 文件，上传后将覆盖已有脚本'
    if (t === 'project') return '只能上传 .zip 文件，上传后将覆盖已有项目目录'
    if (t === 'executable') return '只能上传 .exe 文件，上传后将覆盖已有程序'
    return ''
})

function onUploadFileChange(file) {
    uploadFile.value = file.raw;
    uploadFileList.value = [file]
}

function onUploadFileRemove() {
    uploadFile.value = null;
    uploadFileList.value = []
}

async function handleUpload() {
    if (!uploadFile.value) return
    uploading.value = true
    try {
        await uploadScript(task.value.task_id, uploadFile.value)
        ElMessage.success('文件上传成功')
        uploadDialogVisible.value = false
        uploadFile.value = null;
        uploadFileList.value = []
        loadTask()
    } catch {
    } finally {
        uploading.value = false
    }
}

// ========== 初始化 ==========
onMounted(() => {
    loadTask()
})
</script>

<style scoped>
.task-detail {
    max-width: 1200px;
}

.page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
}

.header-left {
    display: flex;
    align-items: center;
    gap: 12px;
}

.header-left h2 {
    margin: 0;
    font-size: 20px;
    color: #1e293b;
}

.header-actions {
    display: flex;
    gap: 8px;
}

.card-header {
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: 600;
    color: #1e293b;
}

.card-header-actions {
    margin-left: auto;
    display: flex;
    gap: 8px;
}

.mono {
    font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
    font-size: 13px;
    color: #475569;
}

.command-code {
    font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
    font-size: 13px;
    background: #f1f5f9;
    padding: 4px 8px;
    border-radius: 4px;
    display: inline-block;
    max-width: 100%;
    word-break: break-all;
}

.no-data {
    color: #c0c4cc;
}

.status-cell {
    display: flex;
    align-items: center;
    gap: 6px;
}

.status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
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

.script-file-cell {
    display: flex;
    align-items: center;
    gap: 8px;
}

.run-result {
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

.result-pending {
    color: #f59e0b;
}

.result-skipped {
    color: #94a3b8;
}

.exit-error {
    color: #ef4444;
    font-weight: 600;
}

:deep(.clickable-row) {
    cursor: pointer;
}

:deep(.clickable-row:hover) {
    background: #f8fafc;
}

.tags-editor {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 4px;
}

.form-hint {
    margin-left: 12px;
    font-size: 12px;
    color: #94a3b8;
}

.field-hint {
    margin-left: 8px;
    font-size: 11px;
    color: #94a3b8;
}

.env-vars-editor {
    padding-left: 10px;
}

.env-var-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
}

.env-eq {
    color: #94a3b8;
    font-weight: 600;
}

/* 参数编辑弹窗 */
.mode-switch {
    display: flex;
    align-items: center;
    margin-bottom: 20px;
}

.mode-label {
    font-weight: 600;
    color: #1e293b;
    margin-right: 8px;
}

.params-list {
    max-height: 55vh;
    overflow-y: auto;
    padding-right: 4px;
}

.param-card {
    border: 1px solid #e4e7ed;
    border-radius: 8px;
    margin-bottom: 10px;
    overflow: hidden;
    transition: border-color 0.2s;
}

.param-card:hover {
    border-color: #409eff;
}

.param-card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 16px;
    background: #f8fafc;
    cursor: pointer;
}

.param-card-name {
    font-weight: 500;
    color: #1e293b;
    font-family: 'Cascadia Code', 'Consolas', monospace;
    display: flex;
    align-items: center;
    gap: 6px;
}

.param-card-actions {
    display: flex;
    gap: 4px;
}

.param-card-body {
    padding: 16px;
    border-top: 1px solid #e4e7ed;
}

.select-options-editor {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 4px;
}

.add-param-btn {
    width: 100%;
    border-style: dashed;
    margin-top: 8px;
}

/* 命令预览 */
.preview-content {
    max-height: 65vh;
    overflow-y: auto;
}

.preview-form h4, .preview-result h4 {
    margin: 0 0 12px;
    color: #1e293b;
    font-size: 15px;
}

.preview-result-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.preview-command-box {
    background: #0f172a;
    color: #e2e8f0;
    padding: 16px;
    border-radius: 8px;
    font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
    font-size: 13px;
    line-height: 1.6;
    word-break: break-all;
    min-height: 48px;
}

.preview-env {
    margin-top: 16px;
}

/* 上传弹窗 */
.upload-dialog-content {
    display: flex;
    justify-content: center;
}

.upload-tip {
    color: #94a3b8;
    font-size: 12px;
    margin-top: 8px;
}
</style>