import { Component, signal } from '@angular/core';
import { Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { HttpEventType } from '@angular/common/http';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatTableModule } from '@angular/material/table';
import { MatChipsModule } from '@angular/material/chips';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatSnackBarModule, MatSnackBar } from '@angular/material/snack-bar';
import { UploadService } from '../../core/services/upload.service';
import { MockDataService, UploadedFile } from '../../core/services/mock-data.service';

/**
 * WorkspaceComponent — 工作台
 *
 * 功能：
 * 1. 拖拽/点击上传文件
 * 2. 实时进度条
 * 3. 已上传文件列表（从 Mock 获取）
 * 4. 点击文件 → 跳转到鉴伪详情页
 */
@Component({
  selector: 'app-workspace',
  standalone: true,
  imports: [
    CommonModule,
    MatButtonModule,
    MatIconModule,
    MatProgressBarModule,
    MatTableModule,
    MatChipsModule,
    MatTooltipModule,
    MatSnackBarModule,
  ],
  templateUrl: './workspace.component.html',
  styleUrl: './workspace.component.scss',
})
export class WorkspaceComponent {
  uploadProgress = signal(0);
  uploadStatus = signal<'idle' | 'uploading' | 'success' | 'error'>('idle');
  isDragOver = signal(false);
  uploadedFiles = signal<UploadedFile[]>([]);

  displayedColumns = ['fileName', 'fileSize', 'status', 'uploadTime', 'actions'];

  // 允许的文件格式
  private readonly ALLOWED_EXTENSIONS = ['.pdf', '.docx', '.doc', '.jpg', '.jpeg', '.png', '.tiff', '.tif'];
  // 最大文件大小：50MB
  private readonly MAX_FILE_SIZE = 50 * 1024 * 1024;

  constructor(
    private uploadService: UploadService,
    private mockDataService: MockDataService,
    private router: Router,
    private snackBar: MatSnackBar,
  ) {
    // 加载模拟的已上传文件列表
    this.uploadedFiles.set(this.mockDataService.getUploadedFiles());
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver.set(false);

    const files = event.dataTransfer?.files;
    if (files && files.length > 0) {
      const file = files[0];
      if (this.validateFile(file)) {
        this.startUpload(file);
      }
    }
  }

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver.set(true);
  }

  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    this.isDragOver.set(false);
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      const file = input.files[0];
      if (this.validateFile(file)) {
        this.startUpload(file);
      }
      input.value = ''; // 清空以允许重复选择同一文件
    }
  }

  /** 查看检测详情 */
  viewDetail(file: UploadedFile): void {
    this.router.navigate(['/detection', file.id]);
  }

  /** 文件校验：格式 + 大小 */
  private validateFile(file: File): boolean {
    // 校验文件格式
    const fileName = file.name.toLowerCase();
    const hasValidExt = this.ALLOWED_EXTENSIONS.some(ext => fileName.endsWith(ext));
    if (!hasValidExt) {
      this.snackBar.open(
        `不支持的文件格式，请上传：${this.ALLOWED_EXTENSIONS.join('、')}`,
        '关闭',
        { duration: 4000 }
      );
      return false;
    }

    // 校验文件大小
    if (file.size > this.MAX_FILE_SIZE) {
      this.snackBar.open(
        `文件过大（${this.formatFileSize(file.size)}），最大允许 50MB`,
        '关闭',
        { duration: 4000 }
      );
      return false;
    }

    return true;
  }

  private startUpload(file: File): void {
    this.uploadProgress.set(0);
    this.uploadStatus.set('uploading');

    this.uploadService.uploadFile(file).subscribe({
      next: (event) => {
        if (event.type === HttpEventType.UploadProgress) {
          const percent = event.total
            ? Math.round((100 * event.loaded) / event.total)
            : 0;
          this.uploadProgress.set(percent);
        } else if (event.type === HttpEventType.Response) {
          this.handleUploadSuccess(file);
        }
      },
      error: () => {
        // 后端未启动时，模拟上传过程（演示用）
        this.simulateUploadProgress(file);
      },
    });
  }

  /** 模拟上传进度动画（后端未启动时） */
  private simulateUploadProgress(file: File): void {
    let progress = 0;
    const interval = setInterval(() => {
      progress += Math.random() * 15 + 5;
      if (progress >= 100) {
        progress = 100;
        clearInterval(interval);
        this.uploadProgress.set(100);
        this.handleUploadSuccess(file);
      } else {
        this.uploadProgress.set(Math.round(progress));
      }
    }, 200);
  }

  /** 上传完成后的处理：更新列表 + 延迟跳转到详情页 */
  private handleUploadSuccess(file: File): void {
    this.uploadStatus.set('success');
    this.uploadProgress.set(100);
    this.mockDataService.addUploadedFile(file.name, file.size);
    this.uploadedFiles.set(this.mockDataService.getUploadedFiles());

    // 1.5 秒后自动跳转到检测详情页
    setTimeout(() => {
      const latestFile = this.uploadedFiles()[0];
      if (latestFile) {
        this.router.navigate(['/detection', latestFile.id]);
      }
    }, 1500);
  }

  formatFileSize(bytes: number): string {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  }

  getStatusColor(status: string): string {
    switch (status) {
      case 'completed': return '#4caf50';
      case 'processing': return '#ff9800';
      case 'pending': return '#9e9e9e';
      default: return '#9e9e9e';
    }
  }

  getStatusLabel(status: string): string {
    switch (status) {
      case 'completed': return '已完成';
      case 'processing': return '分析中';
      case 'pending': return '待处理';
      default: return '未知';
    }
  }
}
