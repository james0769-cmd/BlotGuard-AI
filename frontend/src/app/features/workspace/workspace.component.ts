import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpEventType } from '@angular/common/http';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSnackBarModule, MatSnackBar } from '@angular/material/snack-bar';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { UploadService } from '../../core/services/upload.service';
import { UploadSuccessDialogComponent } from '../../upload-success-dialog/upload-success-dialog.component';

export interface UploadRecord {
  taskId: string;
  fileName: string;
  fileSize: number;
  uploadTime: string;
}

const HISTORY_KEY = 'blotguard_upload_history';

function loadHistory(): UploadRecord[] {
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveHistory(records: UploadRecord[]): void {
  localStorage.setItem(HISTORY_KEY, JSON.stringify(records));
}

/**
 * WorkspaceComponent — 工作台
 *
 * 功能：拖拽/点击上传文件，实时进度条
 */
@Component({
  selector: 'app-workspace',
  standalone: true,
  imports: [
    CommonModule,
    MatButtonModule,
    MatIconModule,
    MatProgressBarModule,
    MatSnackBarModule,
    MatDialogModule,
  ],
  templateUrl: './workspace.component.html',
  styleUrl: './workspace.component.scss',
})
export class WorkspaceComponent {
  uploadProgress = signal(0);
  uploadStatus = signal<'idle' | 'uploading' | 'processing' | 'success' | 'error'>('idle');
  uploadPhaseText = signal('');
  isDragOver = signal(false);

  private readonly ALLOWED_EXTENSIONS = ['.pdf', '.docx', '.jpg', '.jpeg', '.png', '.tiff', '.tif'];
  readonly maxFileSizeMB = 30;
  private readonly MAX_FILE_SIZE = this.maxFileSizeMB * 1024 * 1024;

  constructor(
    private uploadService: UploadService,
    private snackBar: MatSnackBar,
    private dialog: MatDialog,
  ) {}

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
      input.value = '';
    }
  }

  private validateFile(file: File): boolean {
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

    if (file.size > this.MAX_FILE_SIZE) {
      this.snackBar.open(
        `文件过大（${this.formatFileSize(file.size)}），最大允许 ${this.maxFileSizeMB}MB`,
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
    this.uploadPhaseText.set('正在上传...');

    this.uploadService.uploadFile(file).subscribe({
      next: (event) => {
        if (event.type === HttpEventType.UploadProgress) {
          // 进度最多显示到 90%，100% 保留给服务器确认
          const raw = event.total
            ? Math.round((90 * event.loaded) / event.total)
            : this.uploadProgress();
          const capped = Math.min(raw, 90);
          this.uploadProgress.set(Math.max(this.uploadProgress(), capped));
        } else if (event.type === HttpEventType.Response && event.body) {
          this.handleUploadSuccess(file, event.body.task_id);
        }
      },
      error: (err) => {
        this.uploadStatus.set('error');
        this.uploadPhaseText.set('');
        const message = err?.error?.message || err?.message || '上传失败，请检查网络连接';
        this.snackBar.open(message, '关闭', { duration: 6000 });
      },
    });
  }

  private handleUploadSuccess(file: File, taskId: string): void {
    this.uploadProgress.set(100);
    this.uploadStatus.set('success');
    this.uploadPhaseText.set('');

    // 记录到上传历史
    const history = loadHistory();
    history.unshift({
      taskId,
      fileName: file.name,
      fileSize: file.size,
      uploadTime: new Date().toLocaleString('zh-CN'),
    });
    saveHistory(history);

    this.dialog.open(UploadSuccessDialogComponent, {
      data: { fileName: file.name, taskId },
      disableClose: true,
    });
  }

  formatFileSize(bytes: number): string {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  }
}
