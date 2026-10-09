# HR AI System Frontend

M1-02 的 Vue 3 + Vite + Element Plus 前端工程骨架，包含 Pinia 状态管理、Vue Router、Axios API 客户端、统一管理端布局和工作台占位页面。

## 启动

```powershell
conda activate hr-ai-system
cd frontend
npm install
npm run dev
```

默认地址：`http://127.0.0.1:5173`

## 配置

复制 `.env.example` 为 `.env`。开发环境默认将 `/api` 代理到 `http://127.0.0.1:8000`，与 M1-01 的 FastAPI 服务对接。

## 当前页面

- `/dashboard`：管理端工作台，含统计卡片、考勤概览、待处理事项和动态列表。
- `/employees`、`/attendance`、`/leaves`、`/payroll`、`/messages`：后续模块的路由占位页面。
