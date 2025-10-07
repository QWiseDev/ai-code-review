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
  BellFilled
} from '@element-plus/icons-vue'
import {
  getProjectsOverview,
  getProjectSummary,
  type ProjectOverview,
  type ProjectSummary
} from '@/api/projects'
import { getMRReviews, getPushReviews, type ReviewData } from '@/api/reviews'
import type { ReviewFilters } from '@/api/reviews'
import { type ProjectWebhookConfig } from '@/api/settings'
import ReviewDataTable from '@/components/ReviewDataTable.vue'
import ProjectWebhookDialog from '@/components/ProjectWebhookDialog.vue'

const overviewLoading = ref(false)
const projectOverview = ref<ProjectOverview[]>([])
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
    const data = await getProjectsOverview(keyword || undefined)
    projectOverview.value = data

    if (!data.length) {
      selectedProjectName.value = ''
      summary.value = null
      mrState.data = []
      mrState.total = 0
      pushState.data = []
      pushState.total = 0
      return
    }

    const exists = data.some(item => item.project_name === selectedProjectName.value)
    if (!exists) {
      selectedProjectName.value = data[0].project_name
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
  loadProjects()
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
</style>
