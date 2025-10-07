<template>
  <div class="settings-view">
    <div class="page-header">
      <h1 class="page-title">系统设置</h1>
      <p class="page-description">配置系统参数和用户偏好</p>
    </div>

    <el-row :gutter="20">
      <!-- 基本设置 -->
      <el-col :xs="24" :lg="12">
        <el-card class="settings-card">
          <template #header>
            <div class="card-header">
              <el-icon><Setting /></el-icon>
              <span>基本设置</span>
            </div>
          </template>
          
          <el-form :model="basicSettings" label-width="120px" class="settings-form">
            <el-form-item label="系统名称">
              <el-input v-model="basicSettings.systemName" placeholder="请输入系统名称" />
            </el-form-item>
            
            <el-form-item label="默认语言">
              <el-select v-model="basicSettings.language" placeholder="选择语言">
                <el-option label="简体中文" value="zh-CN" />
                <el-option label="English" value="en-US" />
              </el-select>
            </el-form-item>
            
            <el-form-item label="时区">
              <el-select v-model="basicSettings.timezone" placeholder="选择时区">
                <el-option label="北京时间 (UTC+8)" value="Asia/Shanghai" />
                <el-option label="UTC" value="UTC" />
                <el-option label="纽约时间 (UTC-5)" value="America/New_York" />
              </el-select>
            </el-form-item>
            
            <el-form-item label="每页显示">
              <el-input-number
                v-model="basicSettings.pageSize"
                :min="10"
                :max="100"
                :step="10"
              />
            </el-form-item>
            
            <el-form-item>
              <el-button type="primary" @click="saveBasicSettings" :loading="saving">
                保存设置
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
      
      <!-- 项目Webhook配置 -->
      <el-col :xs="24" :lg="24">
        <el-card class="settings-card project-webhook-card">
          <template #header>
            <div class="card-header">
              <el-icon><Bell /></el-icon>
              <span>项目Webhook配置</span>
              <el-button type="primary" size="small" @click="showAddProjectDialog" style="margin-left: auto;">
                添加项目配置
              </el-button>
            </div>
          </template>

          <!-- 项目列表 -->
          <el-table :data="projectWebhookConfigs" v-loading="loadingConfigs" style="width: 100%">
            <el-table-column prop="project_name" label="项目名称" width="200" />
            <el-table-column prop="url_slug" label="URL标识" width="180" />
            <el-table-column label="钉钉" width="80">
              <template #default="scope">
                <el-tag :type="scope.row.dingtalk_enabled ? 'success' : 'info'" size="small">
                  {{ scope.row.dingtalk_enabled ? '启用' : '禁用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="企业微信" width="80">
              <template #default="scope">
                <el-tag :type="scope.row.wecom_enabled ? 'success' : 'info'" size="small">
                  {{ scope.row.wecom_enabled ? '启用' : '禁用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="飞书" width="80">
              <template #default="scope">
                <el-tag :type="scope.row.feishu_enabled ? 'success' : 'info'" size="small">
                  {{ scope.row.feishu_enabled ? '启用' : '禁用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="自定义" width="80">
              <template #default="scope">
                <el-tag :type="scope.row.extra_webhook_enabled ? 'success' : 'info'" size="small">
                  {{ scope.row.extra_webhook_enabled ? '启用' : '禁用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="更新时间" width="150">
              <template #default="scope">
                {{ formatTimestamp(scope.row.updated_at) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="150" fixed="right">
              <template #default="scope">
                <el-button type="primary" size="small" @click="editProjectConfig(scope.row)">
                  编辑
                </el-button>
                <el-button type="danger" size="small" @click="deleteProjectConfig(scope.row.project_name)">
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <!-- 通知设置 -->
      <el-col :xs="24" :lg="12">
        <el-card class="settings-card">
          <template #header>
            <div class="card-header">
              <el-icon><Bell /></el-icon>
              <span>通知设置</span>
            </div>
          </template>
          
          <el-form :model="notificationSettings" label-width="120px" class="settings-form">
            <el-form-item label="邮件通知">
              <el-switch v-model="notificationSettings.emailEnabled" />
            </el-form-item>
            
            <el-form-item label="浏览器通知">
              <el-switch v-model="notificationSettings.browserEnabled" />
            </el-form-item>
            
            <el-form-item label="审查完成通知">
              <el-switch v-model="notificationSettings.reviewCompleted" />
            </el-form-item>
            
            <el-form-item label="系统更新通知">
              <el-switch v-model="notificationSettings.systemUpdates" />
            </el-form-item>
            
            <el-form-item>
              <el-button type="primary" @click="saveNotificationSettings" :loading="saving">
                保存设置
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
      
      <!-- 审查设置 -->
      <el-col :xs="24" :lg="12">
        <el-card class="settings-card">
          <template #header>
            <div class="card-header">
              <el-icon><DocumentChecked /></el-icon>
              <span>审查设置</span>
            </div>
          </template>
          
          <el-form :model="reviewSettings" label-width="120px" class="settings-form">
            <el-form-item label="自动审查">
              <el-switch v-model="reviewSettings.autoReview" />
            </el-form-item>
            
            <el-form-item label="审查阈值">
              <el-slider
                v-model="reviewSettings.scoreThreshold"
                :min="0"
                :max="100"
                show-stops
                :marks="{ 60: '及格', 80: '良好' }"
              />
            </el-form-item>
            
            <el-form-item label="审查超时(分钟)">
              <el-input-number
                v-model="reviewSettings.timeoutMinutes"
                :min="1"
                :max="60"
              />
            </el-form-item>
            
            <el-form-item label="并发审查数">
              <el-input-number
                v-model="reviewSettings.concurrentReviews"
                :min="1"
                :max="10"
              />
            </el-form-item>
            
            <el-form-item>
              <el-button type="primary" @click="saveReviewSettings" :loading="saving">
                保存设置
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
      
      <!-- 安全设置 -->
      <el-col :xs="24" :lg="12">
        <el-card class="settings-card">
          <template #header>
            <div class="card-header">
              <el-icon><Lock /></el-icon>
              <span>安全设置</span>
            </div>
          </template>
          
          <el-form :model="securitySettings" label-width="120px" class="settings-form">
            <el-form-item label="会话超时(小时)">
              <el-input-number
                v-model="securitySettings.sessionTimeout"
                :min="1"
                :max="24"
              />
            </el-form-item>
            
            <el-form-item label="密码强度">
              <el-select v-model="securitySettings.passwordStrength">
                <el-option label="低" value="low" />
                <el-option label="中" value="medium" />
                <el-option label="高" value="high" />
              </el-select>
            </el-form-item>
            
            <el-form-item label="双因子认证">
              <el-switch v-model="securitySettings.twoFactorAuth" />
            </el-form-item>
            
            <el-form-item label="IP白名单">
              <el-switch v-model="securitySettings.ipWhitelist" />
            </el-form-item>
            
            <el-form-item>
              <el-button type="primary" @click="saveSecuritySettings" :loading="saving">
                保存设置
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
    </el-row>

    <!-- 系统信息 -->
    <el-card class="system-info-card">
      <template #header>
        <div class="card-header">
          <el-icon><InfoFilled /></el-icon>
          <span>系统信息</span>
        </div>
      </template>
      
      <el-descriptions :column="2" border>
        <el-descriptions-item label="系统版本">{{ systemInfo.version }}</el-descriptions-item>
        <el-descriptions-item label="构建时间">{{ systemInfo.buildTime }}</el-descriptions-item>
        <el-descriptions-item label="运行时间">{{ systemInfo.uptime }}</el-descriptions-item>
        <el-descriptions-item label="数据库状态">
          <el-tag :type="systemInfo.dbStatus === 'connected' ? 'success' : 'danger'">
            {{ systemInfo.dbStatus === 'connected' ? '已连接' : '未连接' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="Redis状态">
          <el-tag :type="systemInfo.redisStatus === 'connected' ? 'success' : 'danger'">
            {{ systemInfo.redisStatus === 'connected' ? '已连接' : '未连接' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="LLM状态">
          <el-tag :type="systemInfo.llmStatus === 'connected' ? 'success' : 'danger'">
            {{ systemInfo.llmStatus === 'connected' ? '已连接' : '未连接' }}
          </el-tag>
        </el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>

  <ProjectWebhookDialog
    v-model:visible="webhookDialogVisible"
    :mode="webhookDialogMode"
    :initial-config="editingProjectConfig"
    @saved="handleWebhookSaved"
  />
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Setting, Bell, DocumentChecked, Lock, InfoFilled
} from '@element-plus/icons-vue'
import {
  fetchProjectWebhookConfigs,
  removeProjectWebhookConfig,
  type ProjectWebhookConfig
} from '@/api/settings'
import ProjectWebhookDialog from '@/components/ProjectWebhookDialog.vue'

// 数据状态
const saving = ref(false)
const projectWebhookConfigs = ref<ProjectWebhookConfig[]>([])
const loadingConfigs = ref(false)
const webhookDialogVisible = ref(false)
const webhookDialogMode = ref<'create' | 'edit'>('create')
const editingProjectConfig = ref<ProjectWebhookConfig | null>(null)

const loadProjectWebhookConfigs = async () => {
  loadingConfigs.value = true
  try {
    const configs = await fetchProjectWebhookConfigs()
    projectWebhookConfigs.value = configs.map((item) => ({
      ...item,
      dingtalk_enabled: item.dingtalk_enabled ?? 0,
      wecom_enabled: item.wecom_enabled ?? 0,
      feishu_enabled: item.feishu_enabled ?? 0,
      extra_webhook_enabled: item.extra_webhook_enabled ?? 0
    }))
  } catch (error) {
    ElMessage.error('加载项目Webhook配置失败')
  } finally {
    loadingConfigs.value = false
  }
}

const showAddProjectDialog = () => {
  webhookDialogMode.value = 'create'
  editingProjectConfig.value = null
  webhookDialogVisible.value = true
}

const editProjectConfig = (config: ProjectWebhookConfig) => {
  webhookDialogMode.value = 'edit'
  editingProjectConfig.value = { ...config }
  webhookDialogVisible.value = true
}

const deleteProjectConfig = async (projectName: string) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除项目 ${projectName} 的Webhook配置吗？`,
      '删除确认',
      {
        type: 'warning',
        confirmButtonText: '删除',
        cancelButtonText: '取消'
      }
    )
    await removeProjectWebhookConfig(projectName)
    ElMessage.success('删除成功')
    await loadProjectWebhookConfigs()
  } catch (error: any) {
    if (error === 'cancel' || error === 'close' || error?.message === 'cancel' || error?.message === 'close') {
      return
    }
  }
}

const handleWebhookSaved = async () => {
  await loadProjectWebhookConfigs()
}

const formatTimestamp = (timestamp?: number | null) => {
  if (!timestamp) {
    return '-'
  }
  const date = new Date(timestamp * 1000)
  if (Number.isNaN(date.getTime())) {
    return '-'
  }

  const pad = (value: number) => value.toString().padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

// 基本设置
const basicSettings = reactive({
  systemName: 'AI代码审查系统',
  language: 'zh-CN',
  timezone: 'Asia/Shanghai',
  pageSize: 20
})

// 通知设置
const notificationSettings = reactive({
  emailEnabled: true,
  browserEnabled: true,
  reviewCompleted: true,
  systemUpdates: false
})

// 审查设置
const reviewSettings = reactive({
  autoReview: true,
  scoreThreshold: 60,
  timeoutMinutes: 30,
  concurrentReviews: 3
})

// 安全设置
const securitySettings = reactive({
  sessionTimeout: 8,
  passwordStrength: 'medium',
  twoFactorAuth: false,
  ipWhitelist: false
})

// 系统信息
const systemInfo = reactive({
  version: '1.0.0',
  buildTime: '2025-09-29 07:40:00',
  uptime: '2小时30分钟',
  dbStatus: 'connected',
  redisStatus: 'connected',
  llmStatus: 'connected'
})

// 保存基本设置
const saveBasicSettings = async () => {
  saving.value = true
  try {
    // 这里应该调用API保存设置
    await new Promise(resolve => setTimeout(resolve, 1000)) // 模拟API调用
    ElMessage.success('基本设置保存成功')
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

// 保存通知设置
const saveNotificationSettings = async () => {
  saving.value = true
  try {
    await new Promise(resolve => setTimeout(resolve, 1000))
    ElMessage.success('通知设置保存成功')
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

// 保存审查设置
const saveReviewSettings = async () => {
  saving.value = true
  try {
    await new Promise(resolve => setTimeout(resolve, 1000))
    ElMessage.success('审查设置保存成功')
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

// 保存安全设置
const saveSecuritySettings = async () => {
  saving.value = true
  try {
    await new Promise(resolve => setTimeout(resolve, 1000))
    ElMessage.success('安全设置保存成功')
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

// 加载设置
const loadSettings = async () => {
  try {
    // 这里应该从API加载设置
    // const settings = await getSettings()
    // Object.assign(basicSettings, settings.basic)
    // ...
  } catch (error) {
    ElMessage.error('加载设置失败')
  }
}

// 更新系统信息
const updateSystemInfo = () => {
  // 更新运行时间等动态信息
  const startTime = new Date('2025-09-29T05:10:00')
  const now = new Date()
  const diff = now.getTime() - startTime.getTime()
  const hours = Math.floor(diff / (1000 * 60 * 60))
  const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60))
  systemInfo.uptime = `${hours}小时${minutes}分钟`
}

onMounted(() => {
  loadSettings()
  updateSystemInfo()
  loadProjectWebhookConfigs()
  
  // 每分钟更新一次系统信息
  setInterval(updateSystemInfo, 60000)
})
</script>

<style scoped>
.settings-view {
  padding: 0;
}

.page-header {
  margin-bottom: 24px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #1f2937;
  margin: 0 0 8px 0;
}

.page-description {
  color: #6b7280;
  margin: 0;
}

.settings-card,
.system-info-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.settings-form {
  padding: 0;
}

.settings-form .el-form-item {
  margin-bottom: 20px;
}

.system-info-card {
  margin-top: 20px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .settings-card {
    margin-bottom: 16px;
  }
  
  .settings-form .el-form-item {
    margin-bottom: 16px;
  }
}
</style>
