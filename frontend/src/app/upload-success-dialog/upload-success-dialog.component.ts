import { Component, Inject } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogRef, MatDialogModule } from '@angular/material/dialog';
import { Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { CommonModule } from '@angular/common';

export interface UploadSuccessDialogData {
  fileName: string;
  taskId: string;
  count?: number;
}

@Component({
  selector: 'app-upload-success-dialog',
  standalone: true,
  imports: [CommonModule, MatDialogModule, MatButtonModule, MatIconModule],
  template: `
    <div class="dialog-container">
      <div class="dialog-header">
        <mat-icon class="success-icon">check_circle</mat-icon>
        <h2 mat-dialog-title>上传成功</h2>
      </div>
      <mat-dialog-content>
        <p>{{ data.count ? data.count + ' 个文件' : data.fileName }} 已成功上传至队列。</p>
      </mat-dialog-content>
      <mat-dialog-actions align="end">
        <button mat-stroked-button (click)="onViewQueue()">查看上传记录</button>
        <button mat-stroked-button (click)="onContinueUpload()">继续上传</button>
        <button mat-flat-button color="primary" (click)="onGoVerify()">前往鉴伪</button>
      </mat-dialog-actions>
    </div>
  `,
  styles: [`
    .dialog-container {
      padding: 8px;
      min-width: 320px;
    }
    .dialog-header {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 8px;
    }
    .success-icon {
      color: #4caf50;
      font-size: 28px;
      width: 28px;
      height: 28px;
    }
    h2 {
      margin: 0;
    }
    mat-dialog-actions {
      gap: 8px;
      padding-bottom: 8px;
    }
  `]
})
export class UploadSuccessDialogComponent {
  constructor(
    public dialogRef: MatDialogRef<UploadSuccessDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: UploadSuccessDialogData,
    private router: Router
  ) {}

  onViewQueue(): void {
    this.dialogRef.close('queue');
    this.router.navigate(['/queue']);
  }

  onContinueUpload(): void {
    this.dialogRef.close('continue');
  }

  onGoVerify(): void {
    this.dialogRef.close('verify');
    this.router.navigate(['/detection', this.data.taskId]);
  }
}
