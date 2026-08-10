import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { Router } from '@angular/router';

interface UploadRecord {
  taskId: string;
  fileName: string;
  fileSize: number;
  uploadTime: string;
}

const HISTORY_KEY = 'blotguard_upload_history';

@Component({
  selector: 'app-queue',
  standalone: true,
  imports: [
    CommonModule,
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatChipsModule,
    MatTooltipModule,
    MatSnackBarModule,
  ],
  template: `
    <div class="queue-page">
      <div class="queue-header">
        <h1>
          <mat-icon>history</mat-icon>
          上传记录
        </h1>
        <span class="spacer"></span>
        <button mat-stroked-button color="warn" (click)="clearAll()"
                [disabled]="items().length === 0">
          清空全部
        </button>
      </div>

      @if (items().length === 0) {
        <div class="queue-empty">
          <mat-icon>inbox</mat-icon>
          <p>暂无上传记录</p>
          <p class="empty-hint">在工作台上传文件后，记录将在此显示</p>
        </div>
      } @else {
        <table mat-table [dataSource]="items()" class="queue-table">
          <ng-container matColumnDef="fileName">
            <th mat-header-cell *matHeaderCellDef>文件名</th>
            <td mat-cell *matCellDef="let item">
              <span class="file-name-link" (click)="viewDetail(item.taskId)">
                {{ item.fileName }}
              </span>
            </td>
          </ng-container>

          <ng-container matColumnDef="size">
            <th mat-header-cell *matHeaderCellDef>大小</th>
            <td mat-cell *matCellDef="let item">{{ formatSize(item.fileSize) }}</td>
          </ng-container>

          <ng-container matColumnDef="uploadTime">
            <th mat-header-cell *matHeaderCellDef>上传时间</th>
            <td mat-cell *matCellDef="let item">{{ item.uploadTime }}</td>
          </ng-container>

          <ng-container matColumnDef="actions">
            <th mat-header-cell *matHeaderCellDef></th>
            <td mat-cell *matCellDef="let item">
              <button mat-icon-button (click)="viewDetail(item.taskId)"
                      matTooltip="查看分析结果">
                <mat-icon>visibility</mat-icon>
              </button>
              <button mat-icon-button color="warn" (click)="removeItem(item.taskId)"
                      matTooltip="移除记录">
                <mat-icon>delete_outline</mat-icon>
              </button>
            </td>
          </ng-container>

          <tr mat-header-row *matHeaderRowDef="columns"></tr>
          <tr mat-row *matRowDef="let row; columns: columns;"></tr>
        </table>
      }
    </div>
  `,
  styles: [`
    .queue-page {
      padding: 24px;
      max-width: 1000px;
      margin: 0 auto;
    }
    .queue-header {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 24px;
    }
    .queue-header h1 {
      margin: 0;
      font-size: 22px;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .spacer { flex: 1; }
    .queue-table { width: 100%; }
    .queue-empty {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 12px;
      padding: 64px 0;
      color: #999;
    }
    .queue-empty mat-icon { font-size: 48px; width: 48px; height: 48px; }
    .empty-hint { font-size: 13px; color: #bbb; }
    .file-name-link {
      color: #1976d2;
      cursor: pointer;
      font-weight: 500;
    }
    .file-name-link:hover {
      text-decoration: underline;
    }
  `]
})
export class QueueComponent implements OnInit {
  columns = ['fileName', 'size', 'uploadTime', 'actions'];
  items = signal<UploadRecord[]>([]);

  constructor(
    private router: Router,
    private snackBar: MatSnackBar,
  ) {}

  ngOnInit(): void {
    this.loadHistory();
  }

  viewDetail(taskId: string): void {
    this.router.navigate(['/detection', taskId]);
  }

  removeItem(taskId: string): void {
    const updated = this.items().filter(r => r.taskId !== taskId);
    this.items.set(updated);
    localStorage.setItem(HISTORY_KEY, JSON.stringify(updated));
    this.snackBar.open('已移除记录', '关闭', { duration: 2000 });
  }

  clearAll(): void {
    this.items.set([]);
    localStorage.removeItem(HISTORY_KEY);
    this.snackBar.open('已清空全部上传记录', '关闭', { duration: 2000 });
  }

  formatSize(bytes: number): string {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  }

  private loadHistory(): void {
    try {
      const raw = localStorage.getItem(HISTORY_KEY);
      if (raw) {
        this.items.set(JSON.parse(raw));
      }
    } catch {
      this.items.set([]);
    }
  }
}
