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
        <el-table-column label="操作" width="320" fixed="right" align="center">
          <template #default="{ row }">
            <el-button type="primary" link @click="openEditDialog(row)">编辑</el-button>
            <el-button type="success" link @click="openMemberDialog(row)">成员管理</el-button>
            <el-button type="warning" link @click="openSyncDialog(row)">从 GitLab 同步</el-button>
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

    <el-dialog v-model="membersDialogVisible" :title="memberDialogTitle" width="800px">
      <div v-if="currentTeam">
        <p class="dialog-tip">
          已加入团队的人员列表如下。从 GitLab 同步的成员会显示详细信息，手动添加的成员仅显示用户名。
        </p>
        
        <div class="members-container" v-if="currentTeam.members?.length">
          <div class="member-card" v-for="member in currentTeam.members" :key="getMemberKey(member)">
            <div class="member-info">
              <el-avatar :size="48" :src="getMemberAvatar(member)" class="member-avatar">
                {{ getMemberInitial(member) }}
              </el-avatar>
              <div class="member-details">
                <div class="member-name">
                  <span class="name-text">{{ getMemberName(member) }}</span>
                  <el-tag v-if="getMemberRole(member)" size="small" type="info" class="role-tag">
                    {{ getMemberRole(member) }}
                  </el-tag>
                </div>
                <div class="member-username">@{{ getMemberUsername(member) }}</div>
                <div v-if="getMemberEmail(member)" class="member-email">
                  <el-icon><Message /></el-icon>
                  {{ getMemberEmail(member) }}
                </div>
              </div>
            </div>
            <el-button 
              type="danger" 
              size="small" 
              :icon="Delete" 
              circle 
              @click="handleRemoveMember(getMemberUsername(member))"
              title="移除成员"
            />
          </div>
        </div>
        <el-empty v-else description="尚未添加成员" />

        <el-divider />

        <el-form label-width="100px" class="member-form">
          <el-form-item label="批量添加">
            <el-input
              v-model="memberInput"
              type="textarea"
              :rows="4"
              placeholder="一次可输入多位成员，换行或使用逗号、分号分隔"
            />
            <div class="form-tip">手动添加的成员仅保存用户名，建议使用"从 GitLab 同步"功能获取完整信息</div>
          </el-form-item>
        </el-form>
      </div>

      <template #footer>
        <el-button @click="membersDialogVisible = false">关闭</el-button>
        <el-button type="primary" :loading="memberLoading" @click="handleAddMembers">批量添加成员</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="syncDialogVisible" title="从 GitLab 同步成员" width="600px">
      <div v-if="currentTeam">
        <p class="dialog-tip">
          从 GitLab 项目或组织同步成员到当前团队。系统将自动获取活跃成员的用户名并添加到团队中。
        </p>
        <el-form ref="syncFormRef" :model="syncForm" :rules="syncFormRules" label-width="120px">
          <el-form-item label="来源类型" prop="source_type">
            <el-radio-group v-model="syncForm.source_type">
              <el-radio value="project">项目 (Project)</el-radio>
              <el-radio value="group">组织 (Group)</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item 
            :label="syncForm.source_type === 'project' ? '项目 ID/路径' : '组织 ID/路径'" 
            prop="source_id"
          >
            <el-input
              v-model="syncForm.source_id"
              :placeholder="syncForm.source_type === 'project' ? '例如: mygroup/myproject 或项目 ID' : '例如: mygroup 或组织 ID'"
            />
            <div class="form-tip">支持使用项目/组织的完整路径或数字 ID</div>
          </el-form-item>
          <el-form-item label="合并策略" prop="merge_strategy">
            <el-radio-group v-model="syncForm.merge_strategy">
              <el-radio value="replace">替换 (清空现有成员)</el-radio>
              <el-radio value="merge">合并 (保留现有成员)</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="GitLab URL">
            <el-input
              v-model="syncForm.gitlab_url"
              placeholder="选填，默认从系统环境变量读取"
            />
            <div class="form-tip">例如: https://gitlab.example.com</div>
          </el-form-item>
          <el-form-item label="GitLab Token">
            <el-input
              v-model="syncForm.gitlab_token"
              type="password"
              placeholder="选填，默认从系统环境变量读取"
              show-password
            />
            <div class="form-tip">需要有访问项目/组织成员的权限</div>
          </el-form-item>
        </el-form>
      </div>

      <template #footer>
        <el-button @click="syncDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="syncLoading" @click="handleSyncFromGitLab">开始同步</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Plus, Delete, Message } from '@element-plus/icons-vue'
import {
  fetchTeams,
  createTeam,
  updateTeam,
  deleteTeam,
  addTeamMembers,
  removeTeamMember,
  syncTeamFromGitLab,
  type Team,
  type TeamMember
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

const syncDialogVisible = ref(false)
const syncLoading = ref(false)
const syncFormRef = ref<FormInstance>()
const syncForm = reactive({
  source_type: 'project' as 'project' | 'group',
  source_id: '',
  gitlab_url: '',
  gitlab_token: '',
  merge_strategy: 'replace' as 'replace' | 'merge'
})

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

const syncFormRules: FormRules = {
  source_type: [{ required: true, message: '请选择来源类型', trigger: 'change' }],
  source_id: [
    { required: true, message: '请输入项目/组织 ID 或路径', trigger: 'blur' },
    { min: 1, message: 'ID 不能为空', trigger: 'blur' }
  ],
  merge_strategy: [{ required: true, message: '请选择合并策略', trigger: 'change' }]
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

// 成员信息辅助方法
const getMemberKey = (member: TeamMember | string): string => {
  return typeof member === 'string' ? member : member.author
}

const getMemberUsername = (member: TeamMember | string): string => {
  return typeof member === 'string' ? member : member.author
}

const getMemberName = (member: TeamMember | string): string => {
  if (typeof member === 'string') return member
  return member.name || member.author
}

const getMemberEmail = (member: TeamMember | string): string | null => {
  if (typeof member === 'string') return null
  return member.email || null
}

const getMemberAvatar = (member: TeamMember | string): string | undefined => {
  if (typeof member === 'string') return undefined
  return member.avatar_url || undefined
}

const getMemberRole = (member: TeamMember | string): string | null => {
  if (typeof member === 'string') return null
  return member.access_level_name || null
}

const getMemberInitial = (member: TeamMember | string): string => {
  const name = getMemberName(member)
  return name.charAt(0).toUpperCase()
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

const openSyncDialog = (team: Team) => {
  currentTeam.value = { ...team }
  Object.assign(syncForm, {
    source_type: 'project',
    source_id: '',
    gitlab_url: '',
    gitlab_token: '',
    merge_strategy: 'replace'
  })
  syncDialogVisible.value = true
}

const handleSyncFromGitLab = async () => {
  if (!currentTeam.value || !syncFormRef.value) {
    return
  }

  await syncFormRef.value.validate(async (valid) => {
    if (!valid) {
      return
    }

    const confirmMsg =
      syncForm.merge_strategy === 'replace'
        ? `确定从 GitLab ${syncForm.source_type === 'project' ? '项目' : '组织'} "${syncForm.source_id}" 同步成员吗？\n\n注意：替换模式将清空当前所有成员，请谨慎操作。`
        : `确定从 GitLab ${syncForm.source_type === 'project' ? '项目' : '组织'} "${syncForm.source_id}" 同步成员吗？\n\n合并模式将保留现有成员，仅添加新成员。`

    try {
      await ElMessageBox.confirm(confirmMsg, '确认同步', {
        confirmButtonText: '确定同步',
        cancelButtonText: '取消',
        type: 'warning',
        dangerouslyUseHTMLString: false
      })

      syncLoading.value = true
      const result = await syncTeamFromGitLab(currentTeam.value!.id, {
        source_type: syncForm.source_type,
        source_id: syncForm.source_id.trim(),
        gitlab_url: syncForm.gitlab_url.trim() || undefined,
        gitlab_token: syncForm.gitlab_token.trim() || undefined,
        merge_strategy: syncForm.merge_strategy
      })

      currentTeam.value = result.team
      await loadTeams()
      syncDialogVisible.value = false
      ElMessage.success({
        message: `同步成功！新增 ${result.added} 人，移除 ${result.removed} 人，当前共 ${result.total} 人`,
        duration: 5000
      })
    } catch (error) {
      // 用户取消或同步失败（错误已由拦截器处理）
    } finally {
      syncLoading.value = false
    }
  })
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

.members-container {
  max-height: 400px;
  overflow-y: auto;
  margin-bottom: 16px;
}

.member-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  margin-bottom: 12px;
  background-color: #f5f7fa;
  border-radius: 8px;
  transition: all 0.3s;
}

.member-card:hover {
  background-color: #ecf5ff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.member-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.member-avatar {
  flex-shrink: 0;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.member-details {
  flex: 1;
  min-width: 0;
}

.member-name {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.name-text {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.role-tag {
  flex-shrink: 0;
}

.member-username {
  font-size: 13px;
  color: #606266;
  margin-bottom: 2px;
}

.member-email {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #909399;
}

.member-email .el-icon {
  font-size: 14px;
}

.dialog-tip {
  margin-bottom: 16px;
  padding: 12px;
  background-color: #f0f9ff;
  border-left: 3px solid #409eff;
  color: #606266;
  line-height: 1.6;
  border-radius: 4px;
}

.member-form {
  margin-top: 0;
}

.form-tip {
  margin-top: 8px;
  font-size: 12px;
  color: #909399;
  line-height: 1.5;
}
</style>
