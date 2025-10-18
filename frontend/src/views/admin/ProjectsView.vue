<template>
  <div class="projects-view">
    <div class="page-header">
      <h1 class="page-title">项目管理</h1>
      <p class="page-description">以项目为中心查看审查记录并维护对应的 Webhook 配置</p>
    </div>

    <el-row :gutter="20">
      <el-col :xs="24" :lg="8">
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
            highlight-current-row
            style="width: 100%; margin-top: 12px;"
            :current-row="currentProjectRow"
            @row-click="handleProjectRowClick"
            empty-text="暂无项目"
          >
            <el-table-column prop="project_name" label="项目" min-width="160" show-overflow-tooltip />
            <el-table-column prop="total_review_count" label="审查数" width="100" align="center" />
            <el-table-column
              prop="last_review_at"
              label="最近审查"
              width="160"
              show-overflow-tooltip
            >
              <template #default="{ row }">
                {{ formatTimestamp(row.last_review_at) }}
              </template>
            </el-table-column>
            <el-table-column label="Webhook" width="150">
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
      </el-col>

      <el-col :xs="24" :lg="16">
        <el-card
          v-if="selectedProject"
          class="project-detail-card"
          :body-style="{ padding: '16px' }"
        >
          <template #header>
            <div class="card-header detail-header">
              <div class="detail-title">
                <el-icon><FolderOpened /></el-icon>
                <span>{{ selectedProject.project_name }}</span>
                <el-tag v-if="summary?.total_review_count" size="small" type="success">
                  共 {{ summary?.total_review_count }} 条
                </el-tag>
              </div>
              <div class="detail-actions">
                <el-button
                  size="small"
                  :icon="RefreshRight"
                  @click="refreshProjectDetail"
                  :loading="summaryLoading"
                  plain
                >
                  刷新
                </el-button>
                <el-button
                  size="small"
                  type="primary"
                  :icon="BellFilled"
                  @click="openWebhookDialog"
                >
                  {{ summary?.webhook_config ? '编辑 Webhook' : '配置 Webhook' }}
                </el-button>
              </div>
            </div>
          </template>

          <el-skeleton :loading="summaryLoading" animated :rows="5">
            <template #template>
              <el-skeleton-item variant="text" style="width: 80%; margin: 8px 0;" />
              <el-skeleton-item variant="text" style="width: 60%; margin: 8px 0;" />
              <el-skeleton-item variant="text" style="width: 90%; margin: 8px 0;" />
            </template>
            <template #default>
              <div class="summary-section">
                <el-descriptions :column="2" border size="small" class="summary-descriptions">
                  <el-descriptions-item label="合并请求审查">
                    {{ summary?.mr_review_count ?? 0 }}
                  </el-descriptions-item>
                  <el-descriptions-item label="代码推送审查">
                    {{ summary?.push_review_count ?? 0 }}
                  </el-descriptions-item>
                  <el-descriptions-item label="最近审查时间">
                    {{ formatTimestamp(summary?.last_review_at) }}
                  </el-descriptions-item>
                  <el-descriptions-item label="启用渠道">
                    <template v-if="summary?.webhook_enabled_channels?.length">
                      <el-tag
                        v-for="channel in summary?.webhook_enabled_channels"
                        :key="channel"
                        size="small"
                        :type="getChannelTagType(channel)"
                        style="margin-right: 6px;"
                      >
                        {{ renderChannelName(channel) }}
                      </el-tag>
                    </template>
                    <span v-else>未启用</span>
                  </el-descriptions-item>
                </el-descriptions>

                <el-divider content-position="left">Webhook 配置</el-divider>
                <el-descriptions :column="1" border size="small" class="webhook-descriptions">
                  <el-descriptions-item label="URL 标识">
                    {{ summary?.webhook_config?.url_slug || '-' }}
                  </el-descriptions-item>
                  <el-descriptions-item label="钉钉 Webhook">
                    {{ summary?.webhook_config?.dingtalk_webhook_url || '-' }}
                  </el-descriptions-item>
                  <el-descriptions-item label="企业微信 Webhook">
                    {{ summary?.webhook_config?.wecom_webhook_url || '-' }}
                  </el-descriptions-item>
                  <el-descriptions-item label="飞书 Webhook">
                    {{ summary?.webhook_config?.feishu_webhook_url || '-' }}
                  </el-descriptions-item>
                  <el-descriptions-item label="自定义 Webhook">
                    {{ summary?.webhook_config?.extra_webhook_url || '-' }}
                  </el-descriptions-item>
                </el-descriptions>
              </div>

              <el-divider content-position="left">审查记录</el-divider>
              <el-tabs v-model="activeTab">
                <el-tab-pane label="合并请求" name="mr">
                  <ReviewDataTable
                    :data="mrState.data"
                    :loading="mrState.loading"
                    :total="mrState.total"
                    type="mr"
                  />
                  <el-pagination
                    v-if="mrState.total > mrState.pageSize"
                    class="pagination"
                    background
                    layout="prev, pager, next, total"
                    :current-page="mrState.page"
                    :page-size="mrState.pageSize"
                    :total="mrState.total"
                    @current-change="handleMRPageChange"
                  />
                </el-tab-pane>
                <el-tab-pane label="代码推送" name="push">
                  <ReviewDataTable
                    :data="pushState.data"
                    :loading="pushState.loading"
                    :total="pushState.total"
                    type="push"
                  />
                  <el-pagination
                    v-if="pushState.total > pushState.pageSize"
                    class="pagination"
                    background
                    layout="prev, pager, next, total"
                    :current-page="pushState.page"
                    :page-size="pushState.pageSize"
                    :total="pushState.total"
                    @current-change="handlePushPageChange"
                  />
                </el-tab-pane>
              </el-tabs>
            </template>
          </el-skeleton>
        </el-card>

        <el-card v-else class="project-detail-card empty-card">
          <el-empty description="请选择左侧的项目查看详情" />
        </el-card>
      </el-col>
    </el-row>

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
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Collection,
  RefreshRight,
  Search,
  FolderOpened,
  BellFilled,
  Download
} from '@element-plus/icons-vue'
import {
  getProjectsOverview,
  getProjectSummary,
  getGitLabProjects,
  importProjectsFromGitLab,
  type ProjectOverview,
  type ProjectSummary,
  type GitLabProject
} from '@/api/projects'
import { getMRReviews, getPushReviews, type ReviewData } from '@/api/reviews'
import type { ReviewFilters } from '@/api/reviews'
import { type ProjectWebhookConfig } from '@/api/settings'
import ReviewDataTable from '@/components/ReviewDataTable.vue'
import ProjectWebhookDialog from '@/components/ProjectWebhookDialog.vue'

const overviewLoading = ref(false)
const projectOverview = ref<ProjectOverview[]>([])
const projectsTotal = ref(0)
const projectsPage = ref(1)
const projectsPageSize = ref(20)
const searchKeyword = ref('')
const selectedProjectName = ref<string>('')
const summaryLoading = ref(false)
const summary = ref<ProjectSummary | null>(null)

const activeTab = ref<'mr' | 'push'>('mr')

const mrState = reactive({
  data: [] as ReviewData[],
  loading: false,
  page: 1,
  pageSize: 10,
  total: 0
})

const pushState = reactive({
  data: [] as ReviewData[],
  loading: false,
  page: 1,
  pageSize: 10,
  total: 0
})

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
  gitlab_url: '',
  gitlab_token: ''
})

const isAllSelected = computed(() => {
  return gitlabProjects.value.length > 0 && 
    selectedGitLabProjects.value.length === gitlabProjects.value.length
})

const selectedProject = computed<ProjectOverview | null>(() => {
  if (!selectedProjectName.value) {
    return null
  }
  return projectOverview.value.find(item => item.project_name === selectedProjectName.value) ?? null
})

const currentProjectRow = computed(() => selectedProject.value)

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

    if (!response.data.length) {
      selectedProjectName.value = ''
      summary.value = null
      mrState.data = []
      mrState.total = 0
      pushState.data = []
      pushState.total = 0
      return
    }

    const exists = response.data.some(item => item.project_name === selectedProjectName.value)
    if (!exists) {
      selectedProjectName.value = response.data[0].project_name
    }
  } catch (error) {
    // 错误提示由拦截器处理
  } finally {
    overviewLoading.value = false
  }
}

const loadProjectSummary = async (projectName: string) => {
  if (!projectName) {
    summary.value = null
    return
  }
  summaryLoading.value = true
  try {
    summary.value = await getProjectSummary(projectName)
  } catch (error) {
    summary.value = null
  } finally {
    summaryLoading.value = false
  }
}

const loadMRReviews = async () => {
  const projectName = selectedProjectName.value
  if (!projectName) {
    mrState.data = []
    mrState.total = 0
    return
  }
  mrState.loading = true
  try {
    const filters: ReviewFilters = {
      project_names: [projectName],
      page: mrState.page,
      page_size: mrState.pageSize
    }
    const response = await getMRReviews(filters)
    mrState.data = response.data
    mrState.total = response.total
  } catch (error) {
    mrState.data = []
    mrState.total = 0
  } finally {
    mrState.loading = false
  }
}

const loadPushReviews = async () => {
  const projectName = selectedProjectName.value
  if (!projectName) {
    pushState.data = []
    pushState.total = 0
    return
  }
  pushState.loading = true
  try {
    const filters: ReviewFilters = {
      project_names: [projectName],
      page: pushState.page,
      page_size: pushState.pageSize
    }
    const response = await getPushReviews(filters)
    pushState.data = response.data
    pushState.total = response.total
  } catch (error) {
    pushState.data = []
    pushState.total = 0
  } finally {
    pushState.loading = false
  }
}

const refreshProjectDetail = async () => {
  const projectName = selectedProjectName.value
  if (!projectName) {
    return
  }
  await loadProjectSummary(projectName)
  mrState.page = 1
  pushState.page = 1
  await Promise.all([loadMRReviews(), loadPushReviews()])
}

const handleProjectRowClick = (row: ProjectOverview) => {
  if (!row?.project_name) {
    return
  }
  selectedProjectName.value = row.project_name
}

const handleMRPageChange = async (page: number) => {
  mrState.page = page
  await loadMRReviews()
}

const handlePushPageChange = async (page: number) => {
  pushState.page = page
  await loadPushReviews()
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

const openWebhookDialog = () => {
  const project = selectedProject.value
  if (!project) {
    ElMessage.warning('请先选择项目')
    return
  }
  const config = summary.value?.webhook_config
  if (config) {
    webhookDialogMode.value = 'edit'
    webhookDialogConfig.value = { ...config }
  } else {
    webhookDialogMode.value = 'create'
    webhookDialogConfig.value = {
      project_name: project.project_name,
      url_slug: summary.value?.webhook_config?.url_slug ?? project.webhook_config?.url_slug ?? null,
      dingtalk_enabled: 0,
      wecom_enabled: 0,
      feishu_enabled: 0,
      extra_webhook_enabled: 0
    }
  }
  webhookDialogVisible.value = true
}

const handleWebhookDialogSaved = async () => {
  await Promise.all([refreshProjectDetail(), loadProjects()])
}

// 导入相关方法
const openImportDialog = () => {
  importDialogVisible.value = true
  gitlabProjects.value = []
  selectedGitLabProjects.value = []
  Object.assign(importForm, {
    source_type: 'user',
    group_id: '',
    gitlab_url: '',
    gitlab_token: ''
  })
}

const fetchGitLabProjects = async () => {
  try {
    gitlabProjectsLoading.value = true
    const projects = await getGitLabProjects({
      source_type: importForm.source_type,
      group_id: importForm.group_id || undefined,
      gitlab_url: importForm.gitlab_url || undefined,
      gitlab_token: importForm.gitlab_token || undefined
    })
    gitlabProjects.value = projects
    selectedGitLabProjects.value = []
    ElMessage.success(`获取到 ${projects.length} 个项目`)
  } catch (error) {
    // 错误已由拦截器处理
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

watch(selectedProjectName, async () => {
  if (!selectedProjectName.value) {
    summary.value = null
    mrState.data = []
    mrState.total = 0
    pushState.data = []
    pushState.total = 0
    return
  }
  await refreshProjectDetail()
})

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

.detail-header {
  justify-content: space-between;
  align-items: center;
}

.detail-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.detail-actions {
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

.summary-section {
  margin-bottom: 16px;
}

.summary-descriptions,
.webhook-descriptions {
  margin-bottom: 16px;
}

.pagination {
  margin-top: 12px;
  text-align: right;
}

.project-detail-card {
  min-height: 480px;
}

.empty-card {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 480px;
}

@media (max-width: 768px) {
  .project-detail-card {
    margin-top: 16px;
  }
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
</style>
