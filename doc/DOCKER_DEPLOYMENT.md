# Docker 镜像构建与发布指南

本文档说明如何构建和发布不同版本的 AI Code Review Docker 镜像。

## 📋 目录

- [镜像标签规则](#镜像标签规则)
- [发布流程](#发布流程)
- [使用方法](#使用方法)
- [故障排除](#故障排除)

## 🏷️ 镜像标签规则

### 自动生成的标签

GitHub Actions 会根据不同的触发条件自动生成相应的镜像标签：

| 触发条件 | 生成的标签 | 示例 | 用途 |
|---------|-----------|------|------|
| 推送到 main 分支 | `latest`, `main`, `main-<sha>` | `latest`, `main`, `main-a4ba36c` | 开发版本 |
| 创建版本标签 | `<version>`, `<major>.<minor>`, `<major>` | `1.0.0`, `1.0`, `1` | 正式版本 |
| 推送到其他分支 | `<branch>`, `<branch>-<sha>` | `develop`, `develop-abc123` | 功能分支 |

### 标签配置详解

在 `.github/workflows/build_images.yml` 中的配置：

```yaml
tags: |
  type=semver,pattern={{version}}                    # v1.0.0 → 1.0.0
  type=semver,pattern={{major}}.{{minor}}           # v1.0.0 → 1.0
  type=semver,pattern={{major}}                     # v1.0.0 → 1
  type=raw,value=latest,enable={{is_default_branch}} # main分支 → latest
  type=ref,event=branch                             # 分支名 → 分支名
  type=sha,prefix={{branch}}-,enable={{is_default_branch}} # main分支 → main-<sha>
```

## 🚀 发布流程

### 1. 开发版本发布（推送到 main 分支）

```bash
# 提交代码到 main 分支
git add .
git commit -m "feat: 添加新功能"
git push origin main
```

**生成的镜像：**
- `ghcr.io/qwisedev/ai-code-review:latest`
- `ghcr.io/qwisedev/ai-code-review:main`
- `ghcr.io/qwisedev/ai-code-review:main-<commit-sha>`

### 2. 正式版本发布（创建版本标签）

```bash
# 创建版本标签
git tag v1.0.0
git push origin v1.0.0

# 或者创建带注释的标签
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0
```

**生成的镜像：**
- `ghcr.io/qwisedev/ai-code-review:1.0.0`
- `ghcr.io/qwisedev/ai-code-review:1.0`
- `ghcr.io/qwisedev/ai-code-review:1`

### 3. 预发布版本（Beta/RC 版本）

```bash
# 创建预发布标签
git tag v1.1.0-beta.1
git push origin v1.1.0-beta.1

# 或者 RC 版本
git tag v1.1.0-rc.1
git push origin v1.1.0-rc.1
```

**生成的镜像：**
- `ghcr.io/qwisedev/ai-code-review:1.1.0-beta.1`
- `ghcr.io/qwisedev/ai-code-review:1.1.0-rc.1`

### 4. 功能分支测试

```bash
# 推送到功能分支
git checkout -b feature/new-llm-provider
git push origin feature/new-llm-provider
```

**生成的镜像：**
- `ghcr.io/qwisedev/ai-code-review:feature-new-llm-provider`
- `ghcr.io/qwisedev/ai-code-review:feature-new-llm-provider-<sha>`

## 📦 使用方法

### 使用 docker-compose（推荐）

项目提供了两种 docker-compose 配置：

#### 1. 使用预构建镜像（推荐，快速启动）

```bash
# 使用预构建的最新镜像
docker-compose up -d

# 使用特定版本的镜像
# 编辑 docker-compose.yml 中的 image 标签
# image: ghcr.io/qwisedev/ai-code-review:1.0.0
docker-compose up -d
```

#### 2. 本地构建镜像（开发用）

```bash
# 使用本地构建
docker-compose --profile build up -d app-build
```

### docker-compose.yml 配置说明

```yaml
version: '3.8'

services:
  # 使用预构建镜像（默认服务）
  app:
    image: ghcr.io/qwisedev/ai-code-review:latest  # 可改为具体版本
    ports:
      - "5001:5001"
    volumes:
      - ./data:/app/data
      - ./log:/app/log
    env_file:
      - ./conf/.env
    restart: unless-stopped

  # 本地构建版本（需要 --profile build 启用）
  app-build:
    build:
      context: .
      dockerfile: Dockerfile
      target: app
    ports:
      - "5001:5001"
    volumes:
      - ./data:/app/data
      - ./log:/app/log
    env_file:
      - ./conf/.env
    restart: unless-stopped
    profiles:
      - build
```

**重要说明：**
- 默认的 `app` 服务直接拉取预构建镜像，启动速度快
- `app-build` 服务用于本地构建，需要使用 `--profile build` 参数启用
- 不要同时配置 `build` 和 `image`，这会导致优先执行本地构建

### 直接运行 Docker 容器

```bash
# 运行最新版本
docker run -d \
  --name ai-code-review \
  -p 5001:5001 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/log:/app/log \
  --env-file ./conf/.env \
  ghcr.io/qwisedev/ai-code-review:latest

# 运行特定版本
docker run -d \
  --name ai-code-review \
  -p 5001:5001 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/log:/app/log \
  --env-file ./conf/.env \
  ghcr.io/qwisedev/ai-code-review:1.0.0
```

## 🔍 查看可用版本

### 方法 1：GitHub Packages 页面
访问：https://github.com/QWiseDev/ai-code-review/pkgs/container/ai-code-review

### 方法 2：GitHub Actions 页面
访问：https://github.com/QWiseDev/ai-code-review/actions

查看构建日志中的 "Extract metadata" 步骤，可以看到生成的所有标签。

### 方法 3：使用 Docker 命令

```bash
# 拉取并查看镜像信息
docker pull ghcr.io/qwisedev/ai-code-review:latest
docker images ghcr.io/qwisedev/ai-code-review
```

## 🛠️ 故障排除

### 构建失败常见问题

#### 1. ARM64 架构构建失败
**问题：** `Cannot find module @rollup/rollup-linux-arm64-musl`

**解决方案：** 已在 Dockerfile 中修复，使用 `node:18-slim` 替代 `node:18-alpine`

#### 2. 权限问题
**问题：** `denied: permission_denied`

**解决方案：** 确保 GitHub Token 有 `packages:write` 权限

#### 3. 多架构构建超时
**问题：** 构建时间过长或超时

**解决方案：** 
- 检查网络连接
- 考虑减少构建的架构数量
- 优化 Dockerfile 减少构建层数

### 版本管理最佳实践

1. **语义化版本控制**
   - 主版本号：不兼容的 API 修改
   - 次版本号：向下兼容的功能性新增
   - 修订号：向下兼容的问题修正

2. **标签命名规范**
   ```bash
   # 正式版本
   v1.0.0, v1.1.0, v2.0.0
   
   # 预发布版本
   v1.1.0-alpha.1, v1.1.0-beta.1, v1.1.0-rc.1
   
   # 开发版本
   直接推送到 main 分支
   ```

3. **生产环境建议**
   - 使用具体的版本号，避免使用 `latest`
   - 在测试环境验证后再部署到生产环境
   - 保留多个版本以便快速回滚

## 📝 更新日志

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| 1.0.0 | 2024-XX-XX | 初始版本发布 |

---

**注意：** 本文档会随着项目发展持续更新，请定期查看最新版本。