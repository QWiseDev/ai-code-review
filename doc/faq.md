## 常见问题

### Docker 容器部署时，更新 .env 文件后不生效

**可能原因**

Docker 的文件映射机制是将宿主机的文件复制到容器内，因此宿主机文件的更新不会自动同步到容器内。

**解决方案**

- 删除现有容器：

```
docker rm -f <container_name>
```

重新创建并启动容器：

```
docker-compose up -d
```

或参考说明文档启动容器。

### GitLab 配置 Webhooks 时提示 "Invalid url given"

**可能原因**

GitLab 默认禁止 Webhooks 访问本地网络地址。

**解决方案**

- 进入 GitLab 管理区域：Admin Area → Settings → Network。
- 在 Outbound requests 部分，勾选 Allow requests to the local network from webhooks and integrations。
- 保存。

### 如何让不同项目的消息发送到不同的群？

**推荐方式（前端配置）**

1. 登录管理后台 → 系统设置 → 项目 Webhook 配置。
2. 点击“添加项目配置”，填写项目名称（或 URL Slug）以及钉钉、企业微信、飞书、自定义 Webhook 地址。
3. 根据需要开启/关闭对应渠道的开关并保存。

> 提示：项目名称匹配优先，其次是 URL Slug。若某项目未配置或渠道关闭，将自动回退到默认配置。

**兼容方式（环境变量）**

仍兼容旧版按环境变量区分项目的方案。以 DingTalk 为例：

```
DINGTALK_ENABLED=1
# 项目 A 的群机器人的 Webhook 地址
DINGTALK_WEBHOOK_URL_PROJECT_A=https://oapi.dingtalk.com/robot/send?access_token={access_token_of_project_a}
# 项目 B 的群机器人的 Webhook 地址
DINGTALK_WEBHOOK_URL_PROJECT_B=https://oapi.dingtalk.com/robot/send?access_token={access_token_of_project_b}
# 默认 Webhook，用于未定义专属配置的项目或日报推送
DINGTALK_WEBHOOK_URL=https://oapi.dingtalk.com/robot/send?access_token={access_token}
```

飞书和企业微信的配置方式类似。

### 如何让不同的Gitlab服务器的消息发送到不同的群？

**推荐方式（前端配置）**

在系统设置 → 项目 Webhook 配置中，新增一条配置并填写 `URL 标识`（例如 `example_gitlab_com`），即可按服务器维度匹配。

**兼容方式（环境变量）**

依旧支持环境变量方式。以 DingTalk 为例：

```
DINGTALK_ENABLED=1
# GitLab 服务器 A(http://192.168.30.164) 的群机器人 Webhook 地址
DINGTALK_WEBHOOK_192_168_30_164=https://oapi.dingtalk.com/robot/send?access_token={access_token_of_gitlab_server_a}
# GitLab 服务器 B(http://example.gitlab.com) 的群机器人 Webhook 地址
DINGTALK_WEBHOOK_example_gitlab_com=https://oapi.dingtalk.com/robot/send?access_token={access_token_of_gitlab_server_b}
```

飞书和企业微信的配置方式类似。

**优先级：** 优先根据仓库名称匹配webhook地址，其次根据Gitlab服务器地址匹配webhook地址，如果都没有匹配到，则最后使用默认服务器地址

### 如何以项目维度查看审查记录与 Webhook？

1. 登录管理后台 → 左侧菜单选择“项目管理”。
2. 在左侧项目列表中选择目标项目，可查看该项目的合并请求/代码推送审查记录、最近审查时间等信息。
3. 在详情区点击“配置/编辑 Webhook”可直接维护该项目的钉钉、企业微信、飞书及自定义 Webhook 设置。
4. 支持通过搜索框按项目名称或 URL 标识过滤项目；若需批量维护配置仍可前往“系统设置 → 项目 Webhook 配置”页。

### docker 容器部署时，连接Ollama失败

**可能原因**

配置127.0.0.1:11434连接Ollama。由于docker容器的网络模式为bridge，容器内的127.0.0.1并不是宿主机的127.0.0.1，所以连接失败。

**解决方案**

在.env文件中修改OLLAMA_API_BASE_URL为宿主机的IP地址或外网IP地址。同时要配置Ollama服务绑定到宿主机的IP地址（或0.0.0.0）。

```
OLLAMA_API_BASE_URL=http://127.0.0.1:11434  # 错误
OLLAMA_API_BASE_URL=http://{宿主机/外网IP地址}:11434  # 正确
```

### 如何使用Redis Queue队列？

**操作步骤**

1.开发调试模式下，启动容器：

```
docker compose -f docker-compose.rq.yml up -d
```

2.生产模式下，启动容器：

```
docker compose -f docker-compose.prod.yml up -d
```

**特别说明：**

在 .env 文件中配置 WORKER_QUEUE，其值为 GitLab 域名，并将域名中的点（.）替换为下划线（_）。如果域名为 gitlab.test.cn，则配置为：

```
WORKER_QUEUE=gitlab_test_cn
```

### 如何配置企业微信和飞书消息推送？

**1.配置企业微信推送**

- 在企业微信群中添加一个自定义机器人，获取 Webhook URL。

- 更新 .env 中的配置：
  ```
  #企业微信配置
  WECOM_ENABLED=1  #0不发送企业微信消息，1发送企业微信消息
  WECOM_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx  #替换为你的Webhook URL
  ```

**2.配置飞书推送**

- 在飞书群中添加一个自定义机器人，获取 Webhook URL。
- 更新 .env 中的配置：
  ```
  #飞书配置
  FEISHU_ENABLED=1
  FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxx #替换为你的Webhook URL
  ```

### 是否支持对 GitHub 代码库的 Review？

是的，支持。 需完成以下配置：

**1.配置Github Webhook**

- 进入你的 GitHub 仓库 → Settings → Webhooks → Add webhook。
    - Payload URL: http://your-server-ip:5001/review/webhook（替换为你的服务器地址）
    - Content type选择application/json
    - 在 Which events would you like to trigger this webhook? 中选择 Just the push event（或按需勾选其他事件）
    - 点击 Add webhook 完成配置。

**2.生成 GitHub Personal Access Token**

- 进入 GitHub 个人设置 → Developer settings → Personal access tokens → Generate new token。
- 选择 Fine-grained tokens 或 tokens (classic) 都可以
- 点击 Create new token
- Repository access根据需要选择
- Permissions需要选择Commit statuses、Contents、Discussions、Issues、Metadata和Pull requests
- 点击 Generate token 完成配置。

**3.配置.env文件**

- 在.env文件中，配置GITHUB_ACCESS_TOKEN：
  ```
  GITHUB_ACCESS_TOKEN=your-access-token  #替换为你的Access Token
  ```
