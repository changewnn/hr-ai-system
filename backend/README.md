# HR AI System Backend

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
