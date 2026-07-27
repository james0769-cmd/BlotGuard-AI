# Nginx 本地联调交接

## 访问入口

- 前端和 API 统一入口：`http://localhost:8080`
- 前端请求使用相对路径：`/api/...`
- 本机 Python 后端：`5001`
- Docker 集成环境后端容器：`5000`

## 两种模式

`deploy/nginx.local-backend.conf` 用于 Nginx 在 Docker、后端在宿主机的模式：

```text
/api/ -> host.docker.internal:5001/api/
```

启动文件为 `deploy/compose.nginx-local.yaml`。默认前端静态目录是
`../frontend/dist/blotguard-web/browser`；如果前端项目不在同一仓库，可通过
`BLOTGUARD_FRONTEND_DIST` 指定绝对路径。

`deploy/nginx.compose.conf` 用于 MySQL、后端和 Nginx 全部在 Compose 中运行的模式：

```text
/api/ -> backend:5000/api/
```

## 验证命令

```bash
docker compose -f deploy/compose.nginx-local.yaml config
docker run --rm -v "$PWD/deploy/nginx.local-backend.conf:/etc/nginx/conf.d/default.conf:ro" nginx:1.27-alpine nginx -t
```

上传文件、任务结果、报告和模型权重仍由后端 API 管理，Nginx 不直接暴露这些目录。
