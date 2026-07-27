import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

/**
 * ReportService — 处理报告生成和下载
 * 后端返回 PDF 文件流，前端触发浏览器下载
 */
@Injectable({ providedIn: 'root' })
export class ReportService {
  constructor(private http: HttpClient) {}

  /**
   * 下载指定任务的 PDF 报告
   * @param taskId 任务 ID
   */
  downloadReport(taskId: string): Observable<Blob> {
    return this.http.get(`/api/tasks/${taskId}/report`, {
      responseType: 'blob',
    });
  }

  /**
   * 工具方法：把 Blob 数据触发浏览器下载
   */
  triggerDownload(blob: Blob, filename: string): void {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    window.URL.revokeObjectURL(url); // 释放内存
  }
}
