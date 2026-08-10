# API 契约

规范接口使用 `/api/v1`，JSON 字段使用 `snake_case`，时间使用 UTC ISO 8601。
为配合前端 2026-07-12 的 v0.1 对接草案，后端同时提供 `/api/tasks`
兼容接口；兼容接口不改变规范接口，只做路径、字段和状态映射。

## 创建分析

```text
POST /api/v1/analyses
Content-Type: multipart/form-data
file=<binary>
localize=false
```

返回 `202` 和完整任务资源。默认异步执行，前端轮询任务地址。支持
JPG、JPEG、JFIF、PNG、TIFF、PDF、DOCX。

## 查询和删除

```text
GET    /api/v1/analyses/{task_id}
GET    /api/v1/analyses/{task_id}/report
DELETE /api/v1/analyses/{task_id}
```

只有终态任务可以删除。

## Artifact

```text
GET /api/v1/artifacts/{artifact_id}
GET /api/v1/artifacts/{artifact_id}?download=true
```

## 健康检查

```text
GET /api/v1/health/live
GET /api/v1/health/ready
```

`live` 只表示进程存活。`ready` 同时检查数据库、模型文件和模型运行依赖。

## 错误

```json
{
  "error": {
    "code": "UNSUPPORTED_FILE_TYPE",
    "message": "File type '.doc' is not supported",
    "details": {},
    "request_id": "uuid"
  }
}
```

主要状态码：`400` 请求错误，`404` 不存在，`409` 状态冲突，`413` 文件过大，
`415` 类型错误，`422` 文件可读但无法分析，`503` 服务未就绪。

## 前端 v0.1 兼容接口

这些接口用于匹配前端页面草案和 API 字段需求：

```text
POST /api/auth/login
POST /api/tasks/upload
GET  /api/tasks/{task_id}
GET  /api/tasks/{task_id}/result
GET  /api/tasks/{task_id}/report
```

兼容状态映射：

| 规范状态 | 前端状态 | progress |
| --- | --- | --- |
| `queued` | `pending` | 0 |
| `extracting` | `processing` | 25 |
| `inferencing` | `processing` | 65 |
| `reporting` | `processing` | 90 |
| `succeeded` | `completed` | 100 |
| `failed` | `failed` | 100 |
| `cancelled` | `failed` | 100 |

兼容接口的错误格式为前端草案中的扁平格式：

```json
{
  "error": "UNSUPPORTED_FILE_TYPE",
  "message": "File type '.doc' is not supported",
  "details": {},
  "request_id": "uuid"
}
```

当前不返回伪造定位区域和多生成器概率分布，因此：

- 当前模型不提供定位时，`mask_available` 为 `false`、`mask_image_url` 为
  `null`，并返回 `localization_message`。不得使用原图或空地址冒充 mask。
- `score_generated` 是唯一规范风险分数字段，`overall_score` 仅为兼容别名。
- `risk_level` 是唯一规范五级风险字段，枚举为 `very_low`、`low`、`medium`、
  `high`、`very_high`；`overall_risk` 仅为兼容别名。
- 五级风险当前作为实验性功能启用，响应同时返回
  `risk_level_is_experimental=true`、`risk_level_semantics` 和
  `risk_level_version`。当前模型对 DDPM/Pix2Pix 的区分能力仍待改进，结果只用于
  辅助人工复核。
- `suspect_regions` 为空数组。
- `model_probabilities` 为空数组。

报告由后端生成，任务成功后可直接下载；不需要额外生成接口。
