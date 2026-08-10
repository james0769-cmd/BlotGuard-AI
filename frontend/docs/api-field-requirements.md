# 前端 API 字段需求文档

> 交付日期：2026-07-12 (M0)
> 负责人：前端开发
> 对接方：赵艺泽（后端）、李子牧（模型）
> 版本：v0.1

---

## 一、接口总览

| # | 接口 | 方法 | 用途 | 对接人 |
|---|------|------|------|--------|
| 1 | `/api/auth/login` | POST | 用户登录（本阶段 Mock） | 赵艺泽 |
| 2 | `/api/tasks/upload` | POST | 上传图片文件 | 赵艺泽 |
| 3 | `/api/tasks/:task_id` | GET | 轮询任务状态 | 赵艺泽 |
| 4 | `/api/tasks/:task_id/result` | GET | 获取检测结果详情 | 赵艺泽 + 李子牧 |
| 5 | `/api/tasks/:task_id/report` | GET | 下载 PDF 报告 | 赵艺泽 |

---

## 二、各接口详细字段

### 2.1 登录接口（本阶段仅占位）

**POST** `/api/auth/login`

请求体：
```json
{
  "username": "string",
  "password": "string"
}
```

响应体：
```json
{
  "access_token": "string (JWT)",
  "user": {
    "id": "number",
    "username": "string",
    "role": "string"
  }
}
```

> 说明：本阶段前端已做 Mock 登录，后端可暂不实现。后续对接时只需返回上述格式即可。

---

### 2.2 文件上传接口

**POST** `/api/tasks/upload`（`multipart/form-data`）

请求体：
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file` | File | ✅ | 上传的图片文件 |

前端校验（上传前）：
- 格式白名单：`.jpg`, `.jpeg`, `.png`, `.tiff`, `.tif`
- 大小限制：≤ 20MB

响应体：
```json
{
  "task_id": "string",
  "file_name": "string",
  "file_size": "number (bytes)",
  "status": "pending",
  "created_at": "string (ISO 8601)"
}
```

> ⚠️ 需要赵艺泽确认：上传接口是否支持 `reportProgress`（即分块上传或返回进度），还是前端自己模拟进度条？

---

### 2.3 任务状态轮询接口

**GET** `/api/tasks/:task_id`

响应体：
```json
{
  "task_id": "string",
  "file_name": "string",
  "status": "pending | processing | completed | failed",
  "progress": "number (0~100, 可选)",
  "created_at": "string (ISO 8601)",
  "completed_at": "string (ISO 8601, 可选)",
  "error_message": "string (仅 status=failed 时)"
}
```

前端轮询策略：
- 间隔：3 秒
- 终止条件：`status === 'completed'` 或 `status === 'failed'`
- 超时：5 分钟无响应提示用户

> ⚠️ 需要赵艺泽确认：
> 1. 是否支持 WebSocket / SSE 推送？还是纯轮询？
> 2. `progress` 字段是否能提供？（前端用于展示分析进度）

---

### 2.4 检测结果详情接口（核心）

**GET** `/api/tasks/:task_id/result`

响应体：
```json
{
  "task_id": "string",
  "file_name": "string",
  "status": "completed",

  // --- 图片资源 ---
  "original_image_url": "string (可访问的图片 URL)",
  "mask_image_url": "string (SAM/LoRA 掩码叠加图 URL)",

  // --- 综合评分 ---
  "score_generated": "number (0~1，唯一规范风险分数字段)",
  "overall_score": "number (0~1，兼容字段，等同于 score_generated)",
  "risk_level": "very_low | low | medium | high | very_high（唯一规范风险等级字段）",
  "overall_risk": "兼容字段，等同于 risk_level",
  "risk_level_is_experimental": true,
  "risk_level_semantics": "experimental_class_balanced_calibrated_risk",
  "risk_level_version": "experimental-platt-balanced-v1",

  // --- 可疑区域列表 ---
  "suspect_regions": [
    {
      "id": "number",
      "label": "string (区域描述，如'条带复制区域')",
      "confidence": "number (0~1)",
      "bbox": {
        "x": "number (0~1, 相对原图左上角水平比例)",
        "y": "number (0~1, 相对原图左上角垂直比例)",
        "width": "number (0~1, 区域宽度比例)",
        "height": "number (0~1, 区域高度比例)"
      },
      "description": "string (一句话说明检测发现)"
    }
  ],

  // --- 模型概率分布 ---
  "model_probabilities": [
    {
      "model": "string (模型名称，如 'CycleGAN')",
      "probability": "number (0~1)"
    }
  ],

  // --- 元信息 ---
  "model_version": "string (如 'v1.2.0')",
  "processing_time": "number (秒)",
  "conclusion": "string (文字结论，使用中性表述)",

  "created_at": "string (ISO 8601)",
  "completed_at": "string (ISO 8601)"
}
```

> ⚠️ 需要李子牧确认的模型输出字段：
> 1. `overall_score` — 综合分数的计算方式？是各模型概率加权还是独立分数？
> 2. `suspect_regions` — SAM 模型能输出几个区域？坐标是归一化的吗？
> 3. `model_probabilities` — 最终输出几种模型的概率？名称是否固定为 CycleGAN / DDPM / Pix2Pix / StyleGAN2-ADA？
> 4. `mask_image_url` — 掩码图是 PNG 带透明度的吗？分辨率和原图一致吗？
> 5. `conclusion` — 文字结论由模型生成还是后端根据分数模板化生成？

> ⚠️ 需要赵艺泽确认：
> 1. `original_image_url` / `mask_image_url` — 图片存储位置？直接返回 base64 还是可访问的 URL？
> 2. 图片是否需要鉴权 token 才能访问？

---

### 2.5 PDF 报告下载接口

**GET** `/api/tasks/:task_id/report`

响应：
- Content-Type: `application/pdf`
- Content-Disposition: `attachment; filename="detection_report_{task_id}.pdf"`
- Body: PDF 二进制流

前端处理：
```typescript
// 前端通过 Blob 下载
this.http.get(url, { responseType: 'blob' }).subscribe(blob => {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `检测报告_${taskId}.pdf`;
  a.click();
});
```

> ⚠️ 需要赵艺泽确认：
> 1. 报告由后端生成还是前端生成？（建议后端生成，前端只负责下载）
> 2. 生成报告是否需要额外时间？是否需要先调用生成接口再轮询？

---

## 三、公共约定

### 3.1 请求头
```
Authorization: Bearer <access_token>
Content-Type: application/json（除上传接口外）
```

### 3.2 错误响应格式
```json
{
  "error": "string (错误码)",
  "message": "string (人类可读的错误描述)"
}
```

### 3.3 HTTP 状态码约定
| 状态码 | 含义 |
|--------|------|
| 200 | 成功 |
| 201 | 创建成功（上传） |
| 400 | 请求参数错误 |
| 401 | 未认证 / Token 过期 |
| 404 | 任务不存在 |
| 413 | 文件过大 |
| 500 | 服务器内部错误 |

### 3.4 风险标签文字规范（M2.5 统一）

所有面向用户的风险判定文字必须使用中性表述：
- ✅ 「疑似 AI 生成」「存在伪造风险」「建议进一步核实」
- ❌ 「确认伪造」「一定是假的」「绝对是 AI 生成」

---

## 四、前端 Mock 数据映射

在后端接口就绪前，前端使用 `MockDataService` 模拟全部接口响应。后端对接时只需：
1. 将 `MockDataService` 的调用替换为 `HttpClient` 请求
2. 字段名映射：后端返回 `snake_case` → 前端使用 `camelCase`（在拦截器或 service 层转换）

| 后端字段 (snake_case) | 前端字段 (camelCase) |
|---|---|
| `task_id` | `taskId` |
| `file_name` | `fileName` |
| `file_size` | `fileSize` |
| `original_image_url` | `originalImageUrl` |
| `mask_image_url` | `maskImageUrl` |
| `score_generated` | `scoreGenerated` |
| `risk_level` | `riskLevel` |
| `risk_level_is_experimental` | `riskLevelIsExperimental` |
| `suspect_regions` | `suspectRegions` |
| `model_probabilities` | `modelProbabilities` |
| `model_version` | `modelVersion` |
| `processing_time` | `processingTime` |
| `created_at` | `createdAt` |
| `completed_at` | `completedAt` |
| `error_message` | `errorMessage` |

---

## 五、待确认问题汇总

| # | 问题 | 对接人 | 截止时间 |
|---|------|--------|----------|
| 1 | 上传接口是否支持分块/进度回报？ | 赵艺泽 | 7.14 |
| 2 | 任务状态用轮询还是 WebSocket？ | 赵艺泽 | 7.14 |
| 3 | 图片 URL 是否需要鉴权？ | 赵艺泽 | 7.19 |
| 4 | 模型输出几种概率？名称固定吗？ | 李子牧 | 7.15 |
| 5 | 掩码图格式（PNG透明度？分辨率？）| 李子牧 | 7.15 |
| 6 | overall_score 计算方式？ | 李子牧 | 7.15 |
| 7 | 文字结论模板化还是模型生成？ | 李子牧 | 7.15 |
| 8 | PDF 报告由后端生成？需要额外等待？ | 赵艺泽 | 7.26 |
| 9 | Nginx 代理路径 + Docker 端口？ | 杨泽群 | 7.26 |
