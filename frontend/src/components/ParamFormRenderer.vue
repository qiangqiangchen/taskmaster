<template>
  <div class="param-form-renderer">
    <div v-for="p in visibleParams" :key="p.name" class="param-item">
      <el-form-item
        :label="p.display_name || p.name"
        :required="p.required"
        :class="{ 'param-hidden': p.hidden }"
      >
        <!-- string -->
        <el-input
          v-if="p.type === 'string'"
          v-model="innerValues[p.name]"
          :placeholder="p.placeholder || ''"
          :type="p.sensitive ? 'password' : 'text'"
          :show-password="p.sensitive"
          @input="emitUpdate"
        />

        <!-- number -->
        <el-input-number
          v-else-if="p.type === 'number'"
          v-model="innerValues[p.name]"
          controls-position="right"
          :placeholder="p.placeholder || ''"
          style="width: 100%"
          @change="emitUpdate"
        />

        <!-- boolean -->
        <el-switch
          v-else-if="p.type === 'boolean'"
          v-model="innerValues[p.name]"
          @change="emitUpdate"
        />

        <!-- select -->
        <el-select
          v-else-if="p.type === 'select'"
          v-model="innerValues[p.name]"
          :placeholder="p.placeholder || '请选择'"
          style="width: 100%"
          @change="emitUpdate"
        >
          <el-option
            v-for="opt in p.select_options || []"
            :key="opt"
            :label="opt"
            :value="opt"
          />
        </el-select>

        <!-- file -->
        <el-input
          v-else-if="p.type === 'file'"
          v-model="innerValues[p.name]"
          :placeholder="p.placeholder || '文件路径'"
          @input="emitUpdate"
        >
          <template #prefix>
            <el-icon><Document /></el-icon>
          </template>
        </el-input>

        <!-- directory -->
        <el-input
          v-else-if="p.type === 'directory'"
          v-model="innerValues[p.name]"
          :placeholder="p.placeholder || '目录路径'"
          @input="emitUpdate"
        >
          <template #prefix>
            <el-icon><FolderOpened /></el-icon>
          </template>
        </el-input>

        <!-- fallback -->
        <el-input
          v-else
          v-model="innerValues[p.name]"
          :placeholder="p.placeholder || ''"
          @input="emitUpdate"
        />
      </el-form-item>
    </div>

    <!-- 隐藏参数展开 -->
    <div v-if="hiddenParams.length" class="hidden-toggle">
      <el-button text size="small" @click="showHidden = !showHidden">
        <el-icon>
          <component :is="showHidden ? 'ArrowUp' : 'ArrowDown'" />
        </el-icon>
        {{ showHidden ? '收起高级参数' : `显示 ${hiddenParams.length} 个高级参数` }}
      </el-button>
    </div>

    <el-empty
      v-if="!schema?.params?.length"
      description="暂无参数，请在参数配置中添加"
      :image-size="60"
    />
  </div>
</template>

<script setup>
import { ref, reactive, watch, computed } from 'vue'

const props = defineProps({
  /** 参数 schema，格式 { params: [...] } */
  schema: { type: Object, default: () => ({ params: [] }) },
  /** 参数值 { name: value, ... } */
  modelValue: { type: Object, default: () => ({}) },
  /** 是否禁用 */
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue'])

const showHidden = ref(false)

// 初始化内部值：合并 schema 默认值 + 外部传入值
const innerValues = reactive({})

function initValues() {
  const vals = {}
  for (const p of props.schema?.params || []) {
    const external = props.modelValue?.[p.name]
    if (external !== undefined && external !== '') {
      vals[p.name] = external
    } else if (p.default !== undefined && p.default !== '') {
      vals[p.name] = p.default
    } else {
      vals[p.name] = p.type === 'boolean' ? false : p.type === 'number' ? undefined : ''
    }
  }
  Object.keys(innerValues).forEach(k => delete innerValues[k])
  Object.assign(innerValues, vals)
}

watch(() => props.schema, () => initValues(), { immediate: true, deep: true })
watch(() => props.modelValue, () => {
  // 外部值变化时覆盖内部值
  for (const [k, v] of Object.entries(props.modelValue)) {
    if (v !== undefined && v !== '') {
      innerValues[k] = v
    }
  }
}, { deep: true })

const visibleParams = computed(() => {
  return (props.schema?.params || []).filter(p => !p.hidden || showHidden.value)
})

const hiddenParams = computed(() => {
  return (props.schema?.params || []).filter(p => p.hidden)
})

function emitUpdate() {
  emit('update:modelValue', { ...innerValues })
}

// 暴露方法供父组件获取当前值
defineExpose({ getValues: () => ({ ...innerValues }) })
</script>

<style scoped>
.param-form-renderer {
  max-height: 60vh;
  overflow-y: auto;
  padding-right: 4px;
}

.param-item {
  margin-bottom: 4px;
}

.param-hidden :deep(.el-form-item__label) {
  color: #94a3b8;
}

.hidden-toggle {
  text-align: center;
  padding: 8px 0;
  border-top: 1px dashed #e4e7ed;
  margin-top: 8px;
}
</style>