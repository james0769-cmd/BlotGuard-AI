import { Injectable } from '@angular/core';
import { HttpClient, HttpEvent, HttpRequest } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface UploadResponse {
  task_id: string;
  filename: string;
  status: string;
}

/**
 * UploadService — 处理文件上传到后端
 * 使用 HttpRequest + reportProgress 获取实时上传进度
 */
@Injectable({ providedIn: 'root' })
export class UploadService {
  constructor(private http: HttpClient) {}

  /**
   * 上传单个文件
   * @param file 要上传的文件对象
   * @returns Observable 流，会发出 UploadProgress 和 Response 事件
   */
  uploadFile(file: File): Observable<HttpEvent<UploadResponse>> {
    const formData = new FormData();
    formData.append('file', file, file.name);

    const req = new HttpRequest('POST', '/api/tasks/upload', formData, {
      reportProgress: true, // 开启进度报告
    });

    return this.http.request<UploadResponse>(req);
  }

  /**
   * 批量上传多个文件
   */
  uploadFiles(files: File[]): Observable<HttpEvent<UploadResponse>>[] {
    return files.map((file) => this.uploadFile(file));
  }
}
