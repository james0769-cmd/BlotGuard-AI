# BlotGuard-AI 仓库适配状态

更新时间：2026-07-27

## 已完成的本地适配

- 后端保留规范接口 `/api/v1/...`，并提供前端当前使用的 `/api/...` 兼容入口。
- `/api/tasks/upload`、任务轮询、结果查询、PDF 下载和 mock 登录均已实现。
- 结果接口同时提供规范字段 `file_name`、`overall_risk`，以及当前前端 service 使用的 `filename`、`risk_level` 别名。
- Nginx Docker 集成配置放在 `deploy/nginx.compose.conf`。
- Nginx 本机后端 5001 联调配置放在 `deploy/nginx.local-backend.conf` 和
  `deploy/compose.nginx-local.yaml`。
- 前端构建目录已确认：`frontend/dist/blotguard-web/browser`。
- 已创建独立真实模型环境 `blotguard-real`，并准备本地三份模型权重。

## 验证记录

```text
后端 pytest：13 passed
前端 Angular build：通过
前端构建产物：frontend/dist/blotguard-web/browser/index.html
真实模型：GitHub 25 张黄金样本逐条一致，25/25
真实后端链路：上传 201、结果 200、PDF 报告 200
```

## 提交上游仓库前必须做的事

1. 在最新 `main` 上创建 `feat/backend-analysis-api` 分支。
2. 只提交后端 API、服务、持久化、报告、测试、部署配置和文档；不要提交
   `*.pth`、数据集、`var/` 运行文件、构建产物、密钥和个人配置。
3. 运行 `pytest backend/tests` 和真实 detector smoke；当前两项均已完成。
4. 邀请前端负责人评审 API 字段兼容改动，邀请模型负责人评审推理结果字段。
5. PR 通过至少一次有效代码评审后再合并，不直接推送 `main`。

## 当前还需要确认

- GitHub 账号是否已登录，并确认由谁创建 PR。
- 是否把前端字段别名保留到 v0.1 结束，还是由前端统一改为 `file_name`、
  `overall_risk` 后删除别名。
