# 部署边界

本目录用于后续保存正式部署资产，例如 NGINX、生产 Dockerfile 和 Kubernetes 配置。

当前仓库已经提供用于 Mac/Windows 团队联调的 CPU 开发环境：

- 根目录 `Dockerfile`：Flask 后端开发镜像，包含 CPU PyTorch 和测试依赖。
- 根目录 `compose.dev.yaml`：启动后端与 Angular 开发服务器。
- 根目录 `.dockerignore`：排除权重、数据、输出和历史训练工作区。

启动前先按 `models/README.md` 放置并校验权重，然后运行：

```bash
docker compose -f compose.dev.yaml up --build
```

当前仍不包含正式生产部署：

- 不引入 NGINX、MySQL 或 MongoDB。
- 不创建 Kubernetes 清单。

待上传、任务管理、持久化和推理并发需求确定后，再按实际服务拓扑添加部署配置。
