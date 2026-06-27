# 部署边界

本目录用于后续保存正式部署资产，例如 NGINX、Docker Compose 和 Kubernetes 配置。

当前阶段只建立目录边界：

- 不新增 Compose 服务。
- 不引入 NGINX、MySQL 或 MongoDB。
- 不创建 Kubernetes 清单。
- 项目根目录现有的本地 Docker 文件保持原样，仍不纳入本轮正式工程结构。

待上传、任务管理、持久化和推理并发需求确定后，再按实际服务拓扑添加部署配置。
