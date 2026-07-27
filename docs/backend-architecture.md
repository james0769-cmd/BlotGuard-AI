# 后端架构

## 责任边界

后端负责把上传文件转换为可追踪的分析任务，协调文件解析、模型推理、持久化、
报告生成和结果交付。模型适配层不读取 Flask 请求，也不访问数据库。

```text
Angular
  -> Flask /api/v1
     -> AnalysisService
        -> ExtractionService
        -> InferenceProvider
        -> AnalysisRepository
        -> ReportService
        -> LocalStorage
```

## 主流程

1. API 校验 multipart 请求并立即保存上传流。
2. 生成 UUID `task_id` 和源文件 SHA-256。
3. 根据类型提取并规范化为 RGB PNG。
4. 为每张图片创建独立 item 和 artifact。
5. 延迟加载检测模型并逐图推理。
6. 保存风险分数、阈值、模型版本和权重哈希。
7. 生成 PDF 报告。
8. 通过 opaque artifact ID 提供图片和报告。

任务状态：

```text
queued -> extracting -> inferencing -> reporting -> succeeded
                                               `-> failed
```

## 存储

MySQL/SQLite 只保存结构化元数据。二进制文件保存在：

```text
var/tasks/<task_id>/
  input/
  images/
  masks/
  reports/
```

数据库路径均为相对于 storage root 的路径，公共响应从不返回它们。

## 扩展顺序

1. 用黄金样本冻结模型契约。
2. 与 Angular 联调单图和任务查询。
3. 验证 PDF/DOCX 的真实论文样本。
4. 添加用户、权限和数据保留策略。
5. 将进程内线程执行器替换为 Redis/Celery worker。
6. 使用 MinIO/S3 替代本地文件系统。
7. 测量后再决定 ONNX、Kubernetes 和横向扩容。
