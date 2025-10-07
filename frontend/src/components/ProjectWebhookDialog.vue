<template>
  <el-dialog
    :model-value="visible"
    :title="dialogTitle"
    width="640px"
    @close="handleClose"
  >
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="120px"
    >
      <el-form-item label="项目名称" prop="project_name">
        <el-input
          v-model="form.project_name"
          placeholder="请输入项目名称"
          :disabled="isEditMode"
        />
      </el-form-item>

      <el-form-item label="URL标识">
        <el-input
          v-model="form.url_slug"
          placeholder="可选：GitLab/GitHub 项目的 URL slug"
          clearable
        />
        <div class="form-tip">用于按 URL Slug 匹配项目配置，可选。</div>
      </el-form-item>

      <el-form-item label="钉钉" prop="dingtalk_webhook_url">
        <div class="channel-config">
          <el-switch v-model="form.dingtalk_enabled" />
          <el-input
            v-model="form.dingtalk_webhook_url"
            placeholder="请填写钉钉Webhook地址"
            :disabled="!form.dingtalk_enabled"
            clearable
          />
        </div>
      </el-form-item>

      <el-form-item label="企业微信" prop="wecom_webhook_url">
        <div class="channel-config">
          <el-switch v-model="form.wecom_enabled" />
          <el-input
            v-model="form.wecom_webhook_url"
            placeholder="请填写企业微信Webhook地址"
            :disabled="!form.wecom_enabled"
            clearable
          />
        </div>
      </el-form-item>

      <el-form-item label="飞书" prop="feishu_webhook_url">
        <div class="channel-config">
          <el-switch v-model="form.feishu_enabled" />
          <el-input
            v-model="form.feishu_webhook_url"
            placeholder="请填写飞书Webhook地址"
            :disabled="!form.feishu_enabled"
            clearable
          />
        </div>
      </el-form-item>

      <el-form-item label="自定义" prop="extra_webhook_url">
        <div class="channel-config">
          <el-switch v-model="form.extra_webhook_enabled" />
          <el-input
            v-model="form.extra_webhook_url"
            placeholder="请填写自定义Webhook地址"
            :disabled="!form.extra_webhook_enabled"
            clearable
          />
        </div>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="handleClose">取消</el-button>
      <el-button type="primary" :loading="saving" @click="handleSubmit">
        保存
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import { ElMessage } from 'element-plus'
import { saveProjectWebhookConfig, type ProjectWebhookConfig } from '@/api/settings'

interface Props {
  visible: boolean
  mode: 'create' | 'edit'
  initialConfig?: ProjectWebhookConfig | null
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (event: 'update:visible', value: boolean): void
  (event: 'saved'): void
}>()

const formRef = ref<FormInstance>()
const saving = ref(false)

const form = reactive({
  project_name: '',
  url_slug: '',
  dingtalk_enabled: false,
  dingtalk_webhook_url: '',
  wecom_enabled: false,
  wecom_webhook_url: '',
  feishu_enabled: false,
  feishu_webhook_url: '',
  extra_webhook_enabled: false,
  extra_webhook_url: ''
})

const rules: FormRules = {
  project_name: [
    { required: true, message: '请输入项目名称', trigger: 'blur' },
    { min: 1, max: 200, message: '项目名称长度需在 1-200 个字符之间', trigger: 'blur' }
  ],
  dingtalk_webhook_url: [
    {
      validator: (_rule, value, callback) => {
        if (form.dingtalk_enabled && !value.trim()) {
          callback(new Error('请填写钉钉Webhook地址'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ],
  wecom_webhook_url: [
    {
      validator: (_rule, value, callback) => {
        if (form.wecom_enabled && !value.trim()) {
          callback(new Error('请填写企业微信Webhook地址'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ],
  feishu_webhook_url: [
    {
      validator: (_rule, value, callback) => {
        if (form.feishu_enabled && !value.trim()) {
          callback(new Error('请填写飞书Webhook地址'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ],
  extra_webhook_url: [
    {
      validator: (_rule, value, callback) => {
        if (form.extra_webhook_enabled && !value.trim()) {
          callback(new Error('请填写自定义Webhook地址'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

const isEditMode = computed(() => props.mode === 'edit')
const dialogTitle = computed(() => (isEditMode.value ? '编辑项目配置' : '添加项目配置'))
const visible = computed(() => props.visible)

const resetForm = () => {
  form.project_name = ''
  form.url_slug = ''
  form.dingtalk_enabled = false
  form.dingtalk_webhook_url = ''
  form.wecom_enabled = false
  form.wecom_webhook_url = ''
  form.feishu_enabled = false
  form.feishu_webhook_url = ''
  form.extra_webhook_enabled = false
  form.extra_webhook_url = ''
  formRef.value?.clearValidate()
}

const applyInitialConfig = () => {
  const config = props.initialConfig
  if (!config) {
    return
  }
  form.project_name = config.project_name || ''
  form.url_slug = String(config.url_slug ?? '')
  form.dingtalk_enabled = !!config.dingtalk_enabled
  form.dingtalk_webhook_url = String(config.dingtalk_webhook_url ?? '')
  form.wecom_enabled = !!config.wecom_enabled
  form.wecom_webhook_url = String(config.wecom_webhook_url ?? '')
  form.feishu_enabled = !!config.feishu_enabled
  form.feishu_webhook_url = String(config.feishu_webhook_url ?? '')
  form.extra_webhook_enabled = !!config.extra_webhook_enabled
  form.extra_webhook_url = String(config.extra_webhook_url ?? '')
}

watch(
  () => props.visible,
  (val) => {
    if (val) {
      resetForm()
      if (props.initialConfig) {
        applyInitialConfig()
      }
    } else {
      resetForm()
    }
  }
)

watch(
  () => props.initialConfig,
  (config) => {
    if (props.visible && config) {
      applyInitialConfig()
    }
  }
)

const buildPayload = () => {
  const projectName = form.project_name.trim()
  return {
    project_name: projectName,
    url_slug: form.url_slug.trim() || undefined,
    dingtalk_enabled: form.dingtalk_enabled,
    dingtalk_webhook_url: form.dingtalk_webhook_url.trim() || undefined,
    wecom_enabled: form.wecom_enabled,
    wecom_webhook_url: form.wecom_webhook_url.trim() || undefined,
    feishu_enabled: form.feishu_enabled,
    feishu_webhook_url: form.feishu_webhook_url.trim() || undefined,
    extra_webhook_enabled: form.extra_webhook_enabled,
    extra_webhook_url: form.extra_webhook_url.trim() || undefined
  }
}

const handleSubmit = async () => {
  if (!formRef.value) {
    return
  }
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  saving.value = true
  try {
    await saveProjectWebhookConfig(buildPayload())
    ElMessage.success('项目Webhook配置保存成功')
    emit('saved')
    emit('update:visible', false)
  } catch (error) {
    // 全局拦截器负责错误提示
  } finally {
    saving.value = false
  }
}

const handleClose = () => {
  if (saving.value) {
    return
  }
  emit('update:visible', false)
}
</script>

<style scoped>
.channel-config {
  display: flex;
  align-items: center;
  gap: 12px;
}

.channel-config .el-switch {
  flex-shrink: 0;
}

.channel-config .el-input {
  flex: 1;
}

.form-tip {
  margin-top: 6px;
  font-size: 12px;
  color: #909399;
}
</style>
