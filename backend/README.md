# HR AI System Backend

完整部署、数据库迁移和初始化操作参见项目根目录的 [`部署操作手册.md`](../部署操作手册.md)。

M1-01 的 FastAPI 后端工程骨架。当前只提供应用入口、分层配置和健康检查，业务模块将在后续阶段按任务清单逐步加入。

## Conda 环境

项目使用名为 `hr-ai-system` 的 Conda 环境：

```powershell
conda activate hr-ai-system
```

## 安装依赖

在项目根目录执行：

```powershell
python -m pip install -e ".\\backend[test]"
```

## 配置

复制 `backend/.env.example` 为项目根目录的 `.env`，再按环境覆盖配置：

```powershell
Copy-Item backend/.env.example .env
```

配置加载顺序为：`.env` → `.env.<APP_ENV>` → `.env.local` → 进程环境变量。后加载的值覆盖前面的值，进程环境变量优先级最高。

## 启动

```powershell
python -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

启动后访问：

- 健康检查：`http://127.0.0.1:8000/api/health`
- OpenAPI：`http://127.0.0.1:8000/docs`

## 测试

```powershell
pytest backend/tests
```

## 数据库迁移

```powershell
alembic -c backend/alembic.ini upgrade head
```

首次迁移会创建核心业务表和 Agent/消息/审计/RAG 支撑表。执行迁移前请确认 `.env` 中的 `HR_DATABASE_URL` 可连接 PostgreSQL。

初始化默认管理员：

```powershell
python backend/scripts/init_admin.py --username admin --password "ChangeMe123"
```

初始化字典和默认考勤规则：

```powershell
python backend/scripts/seed.py
```

## 代码质量检查

```powershell
python -m pip install -e ".\\backend[test,dev]"
ruff check backend/app backend/tests
ruff format --check backend/app backend/tests
mypy backend/app
```

首次启用提交前检查：

```powershell
pre-commit install
pre-commit run --all-files
```

前端检查：

```powershell
cd frontend
npm install
npm run format:check
npm run lint
npm run typecheck
npm run build
```
