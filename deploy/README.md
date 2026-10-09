# Docker 部署说明

完整的首次安装、数据库迁移、初始化、升级和故障处理命令参见项目根目录的 [`部署操作手册.md`](../部署操作手册.md)。

## 1. 准备配置

在项目根目录创建 `.env`：

```powershell
Copy-Item .env.docker.example .env
```

然后把 `HR_DATABASE_URL` 中的 `REPLACE_PASSWORD` 替换成 PostgreSQL 实际密码。

当前配置按以下数据库连接信息生成：

- PostgreSQL：`127.0.0.1:5432`
- PostgreSQL 用户：`langchain_user`
- PostgreSQL 数据库：`hr_ai_system`
- Redis：`127.0.0.1:6379`

容器访问宿主机服务时必须使用 `host.docker.internal`，不能在容器内使用 `127.0.0.1`。

## 2. 启动

在项目根目录执行：

```powershell
docker compose up -d --build
```

查看状态：

```powershell
docker compose ps
docker compose logs -f backend
```

访问地址：

- 应用入口：`http://127.0.0.1:8080`
- API 健康检查：`http://127.0.0.1:8080/api/health`

## 3. 停止

```powershell
docker compose down
```

该 Compose 文件使用宿主机已有 PostgreSQL 和 Redis，不会创建或删除数据库数据容器。
