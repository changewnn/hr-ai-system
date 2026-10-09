# Database migrations

完整操作顺序和 Docker 内执行方式参见项目根目录的 [`部署操作手册.md`](../../部署操作手册.md)。

```powershell
alembic upgrade head
alembic current
alembic downgrade -1
```

The migration URL is loaded from the application settings, so use the same `.env` configuration as the API.
