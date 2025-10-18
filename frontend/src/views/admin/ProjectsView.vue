<template>
  <div class="projects-view">
    <div class="page-header">
      <h1 class="page-title">项目管理</h1>
      <p class="page-description">以项目为中心查看审查记录并维护对应的 Webhook 配置</p>
    </div>

    <el-card class="project-list-card">
      <template #header>
        <div class="card-header">
          <el-icon><Collection /></el-icon>
          <span>项目列表</span>
          <div class="header-actions">
            <el-button
              type="success"
              size="small"
              :icon="Download"
              @click="openImportDialog"
            >
              从 GitLab 导入
            </el-button>
            <el-button
              type="primary"
              size="small"
              :icon="RefreshRight"
              plain
              @click="loadProjects"
              :loading="overviewLoading"
            >
              刷新
            </el-button>
          </div>
        </div>
      </template>

      <el-input
        v-model="searchKeyword"
        placeholder="按项目名称或 URL 标识搜索"
        class="search-input"
        clearable
        @keyup.enter="handleSearch"
      >
        <template #append>
          <el-button :icon="Search" @click="handleSearch" />
        </template>
      </el-input>

      <el-table
        :data="projectOverview"
        v-loading="overviewLoading"
        style="width: 100%; margin-top: 12px;"
        empty-text="暂无项目"
      >
        <el-table-column prop="project_name" label="项目" min-width="200" show-overflow-tooltip />
        <el-table-column prop="total_review_count" label="审查数" width="120" align="center" />
        <el-table-column
          prop="last_review_at"
          label="最近审查"
          width="180"
          show-overflow-tooltip
        >
          <template #default="{ row }">
            {{ formatTimestamp(row.last_review_at) }}
          </template>
        </el-table-column>
        <el-table-column label="Webhook" width="200">
          <template #default="{ row }">
            <div class="channel-tags">
              <el-tag
                v-for="channel in row.webhook_enabled_channels"
                :key="channel"
                size="small"
                :type="getChannelTagType(channel)"
              >
                {{ renderChannelName(channel) }}
              </el-tag>
              <span v-if="!row.webhook_enabled_channels.length" class="channel-empty">未启用</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" align="center" fixed="right">
          <template #default="{ row }">
            <el-button
              type="primary"
              size="small"
              @click="handleViewDetail(row)"
            >
              查看详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-if="projectsTotal > 0"
        class="projects-pagination"
        :current-page="projectsPage"
        :page-size="projectsPageSize"
        :total="projectsTotal"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleProjectsPageSizeChange"
        @current-change="handleProjectsPageChange"
      />
    </el-card>

    <ProjectDetailDialog
      v-model:visible="detailDialogVisible"
      :project-name="selectedProjectName"
      @edit-webhook="handleDetailDialogEditWebhook"
    />

    <ProjectWebhookDialog
      v-model:visible="webhookDialogVisible"
      :mode="webhookDialogMode"
      :initial-config="webhookDialogConfig"
      @saved="handleWebhookDialogSaved"
    />

    <!-- 从 GitLab 导入项目对话框 -->
    <el-dialog v-model="importDialogVisible" title="从 GitLab 导入项目" width="900px" :close-on-click-modal="false">
      <el-form :model="importForm" label-width="120px">
        <el-form-item label="来源类型">
          <el-radio-group v-model="importForm.source_type">
            <el-radio value="user">我的项目</el-radio>
            <el-radio value="group">组织项目</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item v-if="importForm.source_type === 'group'" label="组织 ID/路径">
          <el-input
            v-model="importForm.group_id"
            placeholder="例如: mygroup 或组织 ID"
          />
          <div class="form-tip">输入 GitLab 组织的路径或 ID</div>
        </el-form-item>

        <el-form-item label="项目搜索">
          <el-input
            v-model="importForm.search"
            placeholder="输入项目名称关键字搜索（可选）"
            clearable
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          <div class="form-tip">
            <el-icon style="vertical-align: middle;"><InfoFilled /></el-icon>
            推荐使用搜索功能精确定位项目，避免加载过多数据
          </div>
        </el-form-item>

        <el-form-item label="最大获取数量">
          <el-input-number
            v-model="importForm.max_results"
            :min="10"
            :max="500"
            :step="10"
            placeholder="默认 200"
          />
          <div class="form-tip">使用搜索时可设置较小值（如 50），不搜索时建议 100-200</div>
        </el-form-item>

        <el-form-item label="GitLab URL">
          <el-input
            v-model="importForm.gitlab_url"
            placeholder="选填，默认从系统环境变量读取"
          />
        </el-form-item>

        <el-form-item label="GitLab Token">
          <el-input
            v-model="importForm.gitlab_token"
            type="password"
            placeholder="选填，默认从系统环境变量读取"
            show-password
          />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="fetchGitLabProjects" :loading="gitlabProjectsLoading">
            获取项目列表
          </el-button>
          <span v-if="gitlabProjectsLoading" class="loading-tip">
            正在获取项目列表，请耐心等待...
          </span>
        </el-form-item>
      </el-form>

      <div v-if="gitlabProjects.length > 0" class="gitlab-projects-container">
        <div class="projects-header">
          <span>找到 {{ gitlabProjects.length }} 个项目，请选择要导入的项目：</span>
          <el-button size="small" @click="toggleSelectAll">
            {{ isAllSelected ? '取消全选' : '全选' }}
          </el-button>
        </div>
        
        <el-table
          :data="gitlabProjects"
          style="width: 100%"
          max-height="400"
          @selection-change="handleSelectionChange"
        >
          <el-table-column type="selection" width="55" />
          <el-table-column prop="name" label="项目名称" min-width="150" show-overflow-tooltip />
          <el-table-column prop="path_with_namespace" label="路径" min-width="200" show-overflow-tooltip />
          <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip>
            <template #default="{ row }">
              <span>{{ row.description || '无描述' }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="visibility" label="可见性" width="100">
            <template #default="{ row }">
              <el-tag :type="row.visibility === 'public' ? 'success' : 'info'" size="small">
                {{ row.visibility }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <template #footer>
        <el-button @click="importDialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          @click="handleImportProjects"
          :loading="importLoading"
          :disabled="selectedGitLabProjects.length === 0"
        >
          导入选中的项目 ({{ selectedGitLabProjects.length }})
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Collection,
  RefreshRight,
  Search,
  Download,
  InfoFilled
} from '@element-plus/icons-vue'
import {
  getProjectsOverview,
  getGitLabProjects,
  importProjectsFromGitLab,
  type ProjectOverview,
  type ProjectSummary,
  type GitLabProject
} from '@/api/projects'
import { type ProjectWebhookConfig } from '@/api/settings'
import ProjectWebhookDialog from '@/components/ProjectWebhookDialog.vue'
import ProjectDetailDialog from '@/components/ProjectDetailDialog.vue'

const overviewLoading = ref(false)
const projectOverview = ref<ProjectOverview[]>([])
const projectsTotal = ref(0)
const projectsPage = ref(1)
const projectsPageSize = ref(20)
const searchKeyword = ref('')
const selectedProjectName = ref<string>('')

const detailDialogVisible = ref(false)

const webhookDialogVisible = ref(false)
const webhookDialogMode = ref<'create' | 'edit'>('create')
const webhookDialogConfig = ref<ProjectWebhookConfig | null>(null)

// 导入相关状态
const importDialogVisible = ref(false)
const gitlabProjectsLoading = ref(false)
const importLoading = ref(false)
const gitlabProjects = ref<GitLabProject[]>([])
const selectedGitLabProjects = ref<GitLabProject[]>([])
const importForm = reactive({
  source_type: 'user' as 'user' | 'group',
  group_id: '',
  search: '',
  max_results: 200,
  gitlab_url: '',
  gitlab_token: ''
})

const isAllSelected = computed(() => {
  return gitlabProjects.value.length > 0 &&
    selectedGitLabProjects.value.length === gitlabProjects.value.length
})

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

const renderChannelName = (channel: string) => {
  const map: Record<string, string> = {
    dingtalk: '钉钉',
    wecom: '企业微信',
    feishu: '飞书',
    extra: '自定义'
  }
  return map[channel] || channel
}

const getChannelTagType = (channel: string) => {
  const typeMap: Record<string, 'success' | 'warning' | 'info' | 'danger'> = {
    dingtalk: 'success',
    wecom: 'warning',
    feishu: 'info',
    extra: 'danger'
  }
  return typeMap[channel] || 'info'
}

const loadProjects = async () => {
  overviewLoading.value = true
  try {
    const keyword = searchKeyword.value.trim()
    const response = await getProjectsOverview(
      keyword || undefined,
      projectsPage.value,
      projectsPageSize.value
    )
    projectOverview.value = response.data
    projectsTotal.value = response.total
  } catch (error) {
    // 错误提示由拦截器处理
  } finally {
    overviewLoading.value = false
  }
}

const handleViewDetail = (row: ProjectOverview) => {
  if (!row?.project_name) {
    return
  }
  selectedProjectName.value = row.project_name
  detailDialogVisible.value = true
}

const handleSearch = () => {
  projectsPage.value = 1 // 搜索时重置到第一页
  loadProjects()
}

const handleProjectsPageChange = async (page: number) => {
  projectsPage.value = page
  await loadProjects()
}

const handleProjectsPageSizeChange = async (pageSize: number) => {
  projectsPageSize.value = pageSize
  projectsPage.value = 1 // 改变页大小时重置到第一页
  await loadProjects()
}

const handleDetailDialogEditWebhook = (projectName: string, summary: ProjectSummary | null) => {
  const config = summary?.webhook_config
  if (config) {
    webhookDialogMode.value = 'edit'
    webhookDialogConfig.value = { ...config }
  } else {
    webhookDialogMode.value = 'create'
    webhookDialogConfig.value = {
      project_name: projectName,
      url_slug: null,
      dingtalk_enabled: 0,
      wecom_enabled: 0,
      feishu_enabled: 0,
      extra_webhook_enabled: 0
    }
  }
  webhookDialogVisible.value = true
}

const handleWebhookDialogSaved = async () => {
  await loadProjects()
  // 如果详情对话框是打开的，需要刷新它
  // ProjectDetailDialog 会自动重新加载数据
}

// 导入相关方法
const openImportDialog = () => {
  importDialogVisible.value = true
  gitlabProjects.value = []
  selectedGitLabProjects.value = []
  Object.assign(importForm, {
    source_type: 'user',
    group_id: '',
    search: '',
    max_results: 200,
    gitlab_url: '',
    gitlab_token: ''
  })
}

const fetchGitLabProjects = async () => {
  try {
    gitlabProjectsLoading.value = true
    const startTime = Date.now()
    const projects = await getGitLabProjects({
      source_type: importForm.source_type,
      group_id: importForm.group_id || undefined,
      search: importForm.search || undefined,
      max_results: importForm.max_results,
      gitlab_url: importForm.gitlab_url || undefined,
      gitlab_token: importForm.gitlab_token || undefined
    })
    gitlabProjects.value = projects
    selectedGitLabProjects.value = []
    const elapsed = ((Date.now() - startTime) / 1000).toFixed(1)
    const searchInfo = importForm.search ? ` (搜索: ${importForm.search})` : ''
    ElMessage.success(`获取到 ${projects.length} 个项目${searchInfo}（耗时 ${elapsed}s）`)
  } catch (error: any) {
    // 错误已由拦截器处理
    if (error?.message?.includes('timeout')) {
      ElMessage.warning('获取项目列表超时，请尝试减少"最大获取数量"或检查网络连接')
    }
  } finally {
    gitlabProjectsLoading.value = false
  }
}

const handleSelectionChange = (selection: GitLabProject[]) => {
  selectedGitLabProjects.value = selection
}

const toggleSelectAll = () => {
  if (isAllSelected.value) {
    selectedGitLabProjects.value = []
  } else {
    selectedGitLabProjects.value = [...gitlabProjects.value]
  }
}

const handleImportProjects = async () => {
  if (selectedGitLabProjects.value.length === 0) {
    ElMessage.warning('请选择要导入的项目')
    return
  }

  try {
    importLoading.value = true
    const result = await importProjectsFromGitLab({
      projects: selectedGitLabProjects.value.map(p => ({
        name: p.name,
        path_with_namespace: p.path_with_namespace
      }))
    })
    
    importDialogVisible.value = false
    await loadProjects()
    
    if (result.errors.length > 0) {
      ElMessage.warning(`导入完成：成功 ${result.imported} 个，失败 ${result.errors.length} 个`)
    } else {
      ElMessage.success(`成功导入 ${result.imported} 个项目`)
    }
  } catch (error) {
    // 错误已由拦截器处理
  } finally {
    importLoading.value = false
  }
}

onMounted(() => {
  loadProjects()
})
</script>

<style scoped>
.projects-view {
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

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.header-actions {
  margin-left: auto;
  display: flex;
  gap: 8px;
}

.search-input {
  margin-bottom: 8px;
}

.projects-pagination {
  margin-top: 16px;
  display: flex;
  justify-content: center;
}

.channel-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.channel-empty {
  font-size: 12px;
  color: #909399;
}

.gitlab-projects-container {
  margin-top: 20px;
  border-top: 1px solid #e5e7eb;
  padding-top: 16px;
}

.projects-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  font-size: 14px;
  color: #606266;
}

.form-tip {
  margin-top: 4px;
  font-size: 12px;
  color: #909399;
  line-height: 1.5;
}

.loading-tip {
  margin-left: 12px;
  font-size: 13px;
  color: #409eff;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}
</style>
