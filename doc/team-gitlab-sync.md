# 团队管理 - GitLab 成员同步功能

## 功能概述

团队管理模块现已支持从 GitLab 自动同步团队成员信息，可以快速导入项目或组织的成员列表，简化团队维护工作。

## 功能特性

### 后端实现

1. **GitLab API 集成**
   - 支持从 GitLab 项目 (Project) 获取成员列表
   - 支持从 GitLab 组织 (Group) 获取成员列表
   - 自动处理分页，最多支持 1000 个成员
   - 支持自定义 GitLab URL 和访问令牌

2. **数据同步逻辑**
   - 自动过滤活跃 (active) 状态的成员
   - 支持两种合并策略：
     - **替换模式 (replace)**：清空当前所有成员，用 GitLab 成员完全替换
     - **合并模式 (merge)**：保留现有成员，仅添加 GitLab 中的新成员
   - 记录同步结果：新增人数、移除人数、总人数

3. **GitLab 角色映射**
   - Owner (50)
   - Maintainer (40)
   - Developer (30)
   - Reporter (20)
   - Guest (10)

### 前端实现

1. **用户界面**
   - 在团队列表中添加"从 GitLab 同步"按钮
   - 配置对话框支持设置：
     - 来源类型：项目 (Project) 或组织 (Group)
     - 项目/组织 ID 或路径
     - 合并策略：替换或合并
     - 可选：自定义 GitLab URL
     - 可选：自定义 GitLab Token
   - 实时显示同步结果和状态

## 使用方法

### API 端点

**POST** `/api/teams/{team_id}/sync-from-gitlab`

**请求参数：**

```json
{
  "source_type": "project",        // 必填: "project" 或 "group"
  "source_id": "mygroup/myproject", // 必填: 项目/组织的 ID 或路径
  "merge_strategy": "replace",      // 可选: "replace" 或 "merge"，默认 "replace"
  "gitlab_url": "",                 // 可选: 自定义 GitLab URL，默认从环境变量读取
  "gitlab_token": ""                // 可选: 自定义 Token，默认从环境变量读取
}
```

**响应示例：**

```json
{
  "success": true,
  "data": {
    "success": true,
    "added": 5,
    "removed": 2,
    "total": 10,
    "team": {
      "id": 1,
      "name": "开发团队",
      "members": ["user1", "user2", "user3", "..."],
      "...": "..."
    },
    "sync_source": {
      "type": "project",
      "id": "mygroup/myproject"
    }
  },
  "message": "同步成功：新增 5 人，移除 2 人，当前共 10 人"
}
```

### 前端使用

1. 进入"团队管理"页面
2. 找到需要同步的团队
3. 点击"从 GitLab 同步"按钮
4. 在弹出的对话框中：
   - 选择来源类型（项目或组织）
   - 输入项目/组织的 ID 或路径（如 `mygroup/myproject`）
   - 选择合并策略
   - （可选）输入自定义 GitLab URL 和 Token
5. 点击"开始同步"
6. 等待同步完成，查看结果

### 环境配置

在 `.env` 文件中配置默认的 GitLab 连接信息：

```bash
# GitLab 配置
GITLAB_URL=https://gitlab.com
GITLAB_ACCESS_TOKEN=your_gitlab_token_here
```

**注意：** Token 需要有以下权限：
- 读取项目/组织成员列表
- 推荐使用 `read_api` 或 `api` scope

## 使用示例

### 示例 1：从项目同步（替换模式）

```bash
curl -X POST "http://localhost:5001/api/teams/1/sync-from-gitlab" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "project",
    "source_id": "mygroup/myproject",
    "merge_strategy": "replace"
  }'
```

### 示例 2：从组织同步（合并模式）

```bash
curl -X POST "http://localhost:5001/api/teams/1/sync-from-gitlab" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "group",
    "source_id": "mygroup",
    "merge_strategy": "merge"
  }'
```

### 示例 3：使用自定义 GitLab

```bash
curl -X POST "http://localhost:5001/api/teams/1/sync-from-gitlab" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "project",
    "source_id": "123",
    "merge_strategy": "replace",
    "gitlab_url": "https://gitlab.example.com",
    "gitlab_token": "custom_token_here"
  }'
```

## 错误处理

同步过程中可能遇到的错误及解决方法：

1. **"GitLab access token is required for API requests"**
   - 原因：未配置 GitLab Access Token
   - 解决：在环境变量 `GITLAB_ACCESS_TOKEN` 或请求中提供有效的 Token

2. **"无法从 GitLab 获取成员信息"**
   - 原因：Token 无权限或项目/组织 ID 错误
   - 解决：检查 Token 权限和 ID 是否正确

3. **"没有找到活跃的成员"**
   - 原因：项目/组织中没有活跃状态的成员
   - 解决：确认项目/组织中有成员且状态为 active

4. **"团队 ID {team_id} 不存在"**
   - 原因：指定的团队不存在
   - 解决：使用正确的团队 ID

## 注意事项

1. **替换模式慎用**：替换模式会清空当前所有成员，请谨慎操作
2. **Token 安全**：不要将 Token 硬编码在代码中，建议使用环境变量
3. **权限要求**：确保 Token 有足够的权限访问项目/组织成员列表
4. **成员上限**：为防止数据过载，单次最多同步 1000 个成员
5. **网络超时**：大型项目/组织同步可能需要一定时间，请耐心等待

## 技术细节

### 后端实现文件

- `biz/gitlab/gitlab_service.py` - GitLab API 客户端服务
- `biz/service/review_service.py` - 团队同步业务逻辑
- `api.py` - 同步 API 端点

### 前端实现文件

- `frontend/src/api/teams.ts` - 同步 API 客户端
- `frontend/src/views/admin/TeamsView.vue` - 团队管理界面

### 数据库表

使用现有的团队表：
- `teams` - 团队基本信息
- `team_members` - 团队成员关系（带外键约束）

## 未来改进

- [ ] 支持定时自动同步
- [ ] 记录详细的同步日志
- [ ] 支持按角色过滤成员
- [ ] 支持批量同步多个团队
- [ ] 提供同步历史查询接口
