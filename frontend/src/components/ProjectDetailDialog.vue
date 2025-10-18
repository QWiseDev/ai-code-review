<template>
  <el-dialog
    :model-value="visible"
    :title="dialogTitle"
    width="90%"
    top="5vh"
    @close="handleClose"
    :close-on-click-modal="false"
  >
    <el-skeleton :loading="loading" animated :rows="5">
      <template #template>
        <el-skeleton-item variant="text" style="width: 80%; margin: 8px 0;" />
        <el-skeleton-item variant="text" style="width: 60%; margin: 8px 0;" />
        <el-skeleton-item variant="text" style="width: 90%; margin: 8px 0;" />
      </template>
      <template #default>
        <div v-if="summary" class="detail-content">
          <div class="summary-section">
            <el-descriptions :column="2" border size="small" class="summary-descriptions">
              <el-descriptions-item label="合并请求审查">
                {{ summary.mr_review_count ?? 0 }}
              </el-descriptions-item>
              <el-descriptions-item label="代码推送审查">
                {{ summary.push_review_count ?? 0 }}
              </el-descriptions-item>
              <el-descriptions-item label="最近审查时间">
                {{ formatTimestamp(summary.last_review_at) }}
              </el-descriptions-item>
              <el-descriptions-item label="启用渠道">
                <template v-if="summary.webhook_enabled_channels?.length">
                  <el-tag
                    v-for="channel in summary.webhook_enabled_channels"
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

            <el-divider content-position="left">
              Webhook 配置
              <el-button
                size="small"
                type="primary"
                style="margin-left: 12px;"
                @click="handleEditWebhook"
              >
                {{ summary.webhook_config ? '编辑配置' : '配置 Webhook' }}
              </el-button>
            </el-divider>
            <el-descriptions :column="1" border size="small" class="webhook-descriptions">
              <el-descriptions-item label="URL 标识">
                {{ summary.webhook_config?.url_slug || '-' }}
              </el-descriptions-item>
              <el-descriptions-item label="钉钉 Webhook">
                {{ summary.webhook_config?.dingtalk_webhook_url || '-' }}
              </el-descriptions-item>
              <el-descriptions-item label="企业微信 Webhook">
                {{ summary.webhook_config?.wecom_webhook_url || '-' }}
              </el-descriptions-item>
              <el-descriptions-item label="飞书 Webhook">
                {{ summary.webhook_config?.feishu_webhook_url || '-' }}
              </el-descriptions-item>
              <el-descriptions-item label="自定义 Webhook">
                {{ summary.webhook_config?.extra_webhook_url || '-' }}
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
        </div>
      </template>
    </el-skeleton>

    <template #footer>
      <el-button @click="handleClose">关闭</el-button>
      <el-button type="primary" :icon="RefreshRight" @click="handleRefresh" :loading="loading">
        刷新
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { RefreshRight } from '@element-plus/icons-vue'
import { getProjectSummary, type ProjectSummary } from '@/api/projects'
import { getMRReviews, getPushReviews, type ReviewData, type ReviewFilters } from '@/api/reviews'
import ReviewDataTable from '@/components/ReviewDataTable.vue'

interface Props {
  visible: boolean
  projectName: string
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (event: 'update:visible', value: boolean): void
  (event: 'edit-webhook', projectName: string, summary: ProjectSummary | null): void
}>()

const loading = ref(false)
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

const dialogTitle = computed(() => `项目详情 - ${props.projectName}`)

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

const loadProjectSummary = async (projectName: string) => {
  if (!projectName) {
    summary.value = null
    return
  }
  loading.value = true
  try {
    summary.value = await getProjectSummary(projectName)
  } catch (error) {
    summary.value = null
  } finally {
    loading.value = false
  }
}

const loadMRReviews = async () => {
  const projectName = props.projectName
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
  const projectName = props.projectName
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

const loadData = async () => {
  if (!props.projectName) {
    return
  }
  await loadProjectSummary(props.projectName)
  mrState.page = 1
  pushState.page = 1
  await Promise.all([loadMRReviews(), loadPushReviews()])
}

const handleMRPageChange = async (page: number) => {
  mrState.page = page
  await loadMRReviews()
}

const handlePushPageChange = async (page: number) => {
  pushState.page = page
  await loadPushReviews()
}

const handleRefresh = async () => {
  await loadData()
}

const handleEditWebhook = () => {
  emit('edit-webhook', props.projectName, summary.value)
}

const handleClose = () => {
  emit('update:visible', false)
}

watch(
  () => props.visible,
  async (val) => {
    if (val && props.projectName) {
      await loadData()
    } else {
      // 关闭时重置数据
      summary.value = null
      mrState.data = []
      mrState.total = 0
      pushState.data = []
      pushState.total = 0
      activeTab.value = 'mr'
    }
  }
)

watch(
  () => props.projectName,
  async (newName) => {
    if (props.visible && newName) {
      await loadData()
    }
  }
)
</script>

<style scoped>
.detail-content {
  min-height: 400px;
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
</style>
