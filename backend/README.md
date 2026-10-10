# HR AI System Backend

完整部署、数据库迁移和初始化操作参见项目根目录的 [`部署操作手册.md`](../部署操作手册.md)。

登录接口：`POST /api/auth/login`

认证接口：`POST /api/auth/refresh`、`POST /api/auth/logout`、`GET /api/auth/me`、`POST /api/auth/change-password`。

组织接口：`/api/departments`、`/api/positions`、`/api/employees`，其中员工导出接口为 `GET /api/employees/export`，CSV 兼容导出为 `GET /api/employees/export-csv`。

薪酬接口：`GET/PUT /api/salary/config`、`POST /api/salary/calculate`、`POST /api/salary/publish`、`GET /api/salary/records`、`GET /api/salary/mine`、`POST /api/salary/adjustments`。

政策知识库接口：`/api/admin/knowledge`。仅 ADMIN 可以上传、查看、重试、发布和归档政策版本。文档上传后由后台任务解析、切分并调用千问向量模型写入 PostgreSQL + pgvector；支持带文本层的 PDF、DOCX、MD、TXT，暂不支持扫描 PDF OCR。

知识库需要配置 `HR_EMBEDDING_BASE_URL`、`HR_EMBEDDING_API_KEY`、`HR_EMBEDDING_MODEL`。当前迁移固定向量维度为 1024，因此 `HR_EMBEDDING_DIMENSION` 必须为 1024。

执行 M10 知识库迁移前，请确认目标数据库已经启用 pgvector。若当前数据库用户没有创建扩展权限，请由数据库管理员连接到目标数据库 `hr-ai-system` 执行：

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

然后在项目根目录执行：

```powershell
docker compose exec backend alembic -c alembic.ini upgrade head
```

受保护业务路由应使用 `CurrentActiveUser`；首次登录需要改密、账号停用或员工已离职时会被拒绝。角色依赖可使用 `AdminUser`、`ManagerOrAdminUser`，员工/部门数据范围使用 `ensure_employee_scope` 和 `ensure_employee_department_scope`。

请求示例：

```json
{"identifier":"admin","password":"your-password"}
```

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
