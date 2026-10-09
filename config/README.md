# 环境配置约定

## 配置层级

配置按以下顺序加载，后加载值覆盖先加载值：

1. 项目根目录 `.env`
2. 项目根目录 `.env.<APP_ENV>`
3. `backend/.env`
4. `backend/.env.<APP_ENV>`
5. `.env.local`
6. 进程环境变量

生产环境建议只通过部署平台的环境变量或密钥管理服务注入敏感配置，不提交生产 `.env` 文件。

## 环境边界

| 环境 | `APP_ENV` | 用途 |
|---|---|---|
| development | `development` | 本地开发，允许调试和 Swagger |
| test | `test` | 自动化测试，使用独立数据库/Redis 配置 |
| production | `production` | 线上运行，禁止调试和默认密钥 |

生产启动时会校验：`HR_SECRET_KEY` 至少 32 个字符且不能使用默认值，`HR_DEBUG=false`。

## 敏感配置

- 不提交 `.env`、`.env.local`、生产密钥、数据库密码、Redis 密码。
- 只提交 `.env.example` 和环境模板文件。
- 前端 `VITE_*` 变量会进入浏览器构建产物，禁止放入数据库密码、JWT 密钥等服务端秘密。
