# 部署边界

本目录用于后续保存正式部署资产，例如 NGINX、生产 Dockerfile 和 Kubernetes 配置。

当前仓库已经提供用于本地联调的开发环境：

- 根目录 `Dockerfile`：Flask 后端开发镜像，默认使用开发 mock 推理。
- 根目录 `compose.dev.yaml`：启动 MySQL、Flask 后端和 NGINX，并提供已构建的 Angular 静态页面。
- `deploy/compose.nginx-local.yaml`：只启动 NGINX，适合后端在宿主机 5001 端口运行时联调。

启动前安装并构建前端：

```bash
cd frontend
npm ci
npm run build
cd ..
docker compose -f compose.dev.yaml up --build
```

完整开发环境入口为 `http://localhost:8080`。当前仍不包含正式生产部署：

- 不创建 Kubernetes 清单。
- Compose 默认使用 mock 推理；真实模型建议按根目录 README 的 Conda/本机方式启动。

待上传、任务管理、持久化和推理并发需求确定后，再按实际服务拓扑添加部署配置。
