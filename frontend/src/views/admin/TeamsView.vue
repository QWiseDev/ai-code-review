<template>
  <div class="teams-view">
    <div class="header">
      <div class="title">
        <h2>团队管理</h2>
        <p class="subtitle">配置团队信息并维护成员列表，支持为每个团队设置独立的工作日报 Webhook。</p>
      </div>
      <div class="actions">
        <el-button :loading="loading" @click="loadTeams">刷新</el-button>
        <el-button type="primary" @click="openCreateDialog">
          <el-icon><Plus /></el-icon>
          新建团队
        </el-button>
      </div>
    </div>

    <el-card class="table-card">
      <el-table :data="teams" stripe border v-loading="loading" empty-text="暂无团队，请先创建。">
        <el-table-column prop="name" label="团队名称" min-width="160" />
        <el-table-column label="Webhook 地址" min-width="220">
          <template #default="{ row }">
            <el-tooltip v-if="row.webhook_url" effect="dark" :content="row.webhook_url" placement="top">
              <span class="text-ellipsis">{{ row.webhook_url }}</span>
            </el-tooltip>
            <span v-else class="text-muted">未配置</span>
          </template>
        </el-table-column>
        <el-table-column label="成员人数" width="110" align="center">
          <template #default="{ row }">
            <el-tag type="info" effect="plain">{{ row.members?.length || 0 }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="200">
          <template #default="{ row }">
            <span v-if="row.description" class="text-ellipsis">{{ row.description }}</span>
            <span v-else class="text-muted">未填写</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right" align="center">
          <template #default="{ row }">
            <el-button type="primary" link @click="openEditDialog(row)">编辑</el-button>
            <el-button type="success" link @click="openMemberDialog(row)">成员管理</el-button>
            <el-button type="danger" link @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="editDialogVisible" :title="dialogMode === 'create' ? '新建团队' : '编辑团队'" width="520px">
      <el-form ref="editFormRef" :model="editForm" :rules="formRules" label-width="100px">
        <el-form-item label="团队名称" prop="name">
          <el-input v-model="editForm.name" placeholder="请输入团队名称" maxlength="50" show-word-limit />
        </el-form-item>
        <el-form-item label="Webhook 地址" prop="webhook_url">
          <el-input
            v-model="editForm.webhook_url"
            placeholder="请输入团队专属 Webhook (可为空)"
            maxlength="255"
            clearable
          />
        </el-form-item>
        <el-form-item label="团队描述" prop="description">
          <el-input
            v-model="editForm.description"
            type="textarea"
            :rows="3"
            maxlength="200"
            show-word-limit
            placeholder="记录团队职责或其他说明（可选）"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="submitEditForm">
          {{ dialogMode === 'create' ? '创建' : '保存' }}
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="membersDialogVisible" :title="memberDialogTitle" width="600px">
      <div v-if="currentTeam">
        <p class="dialog-tip">
          已加入团队的人员列表如下，可一键移除。支持批量录入，使用换行、逗号或分号分隔成员账号。
        </p>
        <div class="members-list" v-if="currentTeam.members?.length">
          <el-tag
            v-for="member in currentTeam.members"
            :key="member"
            closable
            type="info"
            effect="plain"
            @close="handleRemoveMember(member)"
          >
            {{ member }}
          </el-tag>
        </div>
        <el-empty v-else description="尚未添加成员" />

        <el-form label-width="100px" class="member-form">
          <el-form-item label="批量添加">
            <el-input
              v-model="memberInput"
              type="textarea"
              :rows="4"
              placeholder="一次可输入多位成员，换行或使用逗号、分号分隔"
            />
          </el-form-item>
        </el-form>
      </div>

      <template #footer>
        <el-button @click="membersDialogVisible = false">关闭</el-button>
        <el-button type="primary" :loading="memberLoading" @click="handleAddMembers">批量添加成员</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import {
  fetchTeams,
  createTeam,
  updateTeam,
  deleteTeam,
  addTeamMembers,
  removeTeamMember,
  type Team
} from '@/api/teams'

type DialogMode = 'create' | 'edit'

const loading = ref(false)
const submitLoading = ref(false)
const memberLoading = ref(false)
const teams = ref<Team[]>([])

const editDialogVisible = ref(false)
const dialogMode = ref<DialogMode>('create')
const editFormRef = ref<FormInstance>()
const editForm = reactive({
  id: 0,
  name: '',
  webhook_url: '',
  description: ''
})

const membersDialogVisible = ref(false)
const currentTeam = ref<Team | null>(null)
const memberInput = ref('')

const formRules: FormRules = {
  name: [
    { required: true, message: '请输入团队名称', trigger: 'blur' },
    { min: 2, max: 50, message: '名称长度需在 2~50 个字符之间', trigger: 'blur' }
  ],
  webhook_url: [
    {
      trigger: 'blur',
      validator: (_rule, value, callback) => {
        if (!value) {
          callback()
          return
        }
        const trimmed = String(value).trim()
        if (!trimmed) {
          callback()
          return
        }
        const urlPattern = /^https?:\/\/.+/
        if (!urlPattern.test(trimmed)) {
          callback(new Error('Webhook 需以 http 或 https 开头'))
        } else {
          callback()
        }
      }
    }
  ]
}

const memberDialogTitle = computed(() => {
  if (!currentTeam.value) {
    return '成员管理'
  }
  return `成员管理 - ${currentTeam.value.name}`
})

const parseAuthors = (raw: string): string[] => {
  return raw
    .split(/[\n,，;；]+/)
    .map((item) => item.trim())
    .filter((item) => item.length > 0)
}

const loadTeams = async () => {
  loading.value = true
  try {
    teams.value = await fetchTeams(true)
  } catch (error) {
    // 错误已由拦截器统一处理
  } finally {
    loading.value = false
  }
}

const openCreateDialog = () => {
  dialogMode.value = 'create'
  Object.assign(editForm, {
    id: 0,
    name: '',
    webhook_url: '',
    description: ''
  })
  editDialogVisible.value = true
}

const openEditDialog = (team: Team) => {
  dialogMode.value = 'edit'
  Object.assign(editForm, {
    id: team.id,
    name: team.name,
    webhook_url: team.webhook_url ?? '',
    description: team.description ?? ''
  })
  editDialogVisible.value = true
}

const submitEditForm = async () => {
  if (!editFormRef.value) {
    return
  }
  await editFormRef.value.validate(async (valid) => {
    if (!valid) {
      return
    }
    submitLoading.value = true
    try {
      const payload = {
        name: editForm.name.trim(),
        webhook_url: editForm.webhook_url?.trim() || null,
        description: editForm.description?.trim() || null
      }
      if (dialogMode.value === 'create') {
        await createTeam(payload)
        ElMessage.success('团队创建成功')
      } else {
        await updateTeam(editForm.id, payload)
        ElMessage.success('团队更新成功')
      }
      editDialogVisible.value = false
      await loadTeams()
    } catch (error) {
      // 交由全局错误处理
    } finally {
      submitLoading.value = false
    }
  })
}

const handleDelete = async (team: Team) => {
  try {
    await ElMessageBox.confirm(`确定删除团队「${team.name}」吗？该操作会清空成员关联。`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await deleteTeam(team.id)
    ElMessage.success('团队删除成功')
    await loadTeams()
  } catch (error) {
    // 用户取消时无需处理
  }
}

const openMemberDialog = (team: Team) => {
  currentTeam.value = { ...team }
  memberInput.value = ''
  membersDialogVisible.value = true
}

const handleAddMembers = async () => {
  if (!currentTeam.value) {
    return
  }
  const authors = parseAuthors(memberInput.value)
  if (authors.length === 0) {
    ElMessage.warning('请先输入需要添加的成员')
    return
  }

  memberLoading.value = true
  try {
    const uniqueAuthors = Array.from(new Set(authors))
    const result = await addTeamMembers(currentTeam.value.id, uniqueAuthors)
    currentTeam.value = result.team
    memberInput.value = ''
    await loadTeams()
    ElMessage.success(`成功添加 ${result.added} 位成员`)
  } catch (error) {
    // 统一错误处理
  } finally {
    memberLoading.value = false
  }
}

const handleRemoveMember = async (author: string) => {
  if (!currentTeam.value) {
    return
  }
  try {
    await ElMessageBox.confirm(`确定从团队移除「${author}」吗？`, '提醒', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    memberLoading.value = true
    const team = await removeTeamMember(currentTeam.value.id, author)
    currentTeam.value = team
    await loadTeams()
    ElMessage.success('成员移除成功')
  } catch (error) {
    // 用户取消或请求失败
  } finally {
    memberLoading.value = false
  }
}

onMounted(() => {
  loadTeams()
})
</script>

<style scoped>
.teams-view {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.title h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.subtitle {
  margin: 4px 0 0;
  color: #909399;
  font-size: 13px;
}

.actions {
  display: flex;
  gap: 8px;
}

.table-card {
  flex: 1;
}

.text-ellipsis {
  display: inline-block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.text-muted {
  color: #909399;
}

.members-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}

.dialog-tip {
  margin-bottom: 12px;
  color: #606266;
  line-height: 1.6;
}

.member-form {
  margin-top: 16px;
}
</style>
