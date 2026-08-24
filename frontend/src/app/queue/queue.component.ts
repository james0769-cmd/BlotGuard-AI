import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { Router } from '@angular/router';
import { forkJoin } from 'rxjs';
import { TaskService } from '../core/services/task.service';

interface UploadRecord {
  taskId: string;
  fileName: string;
  fileSize: number;
  uploadTime: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  errorMessage: string | null;
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
                [disabled]="deleting() || deletableItems().length === 0">
          <mat-icon>delete_sweep</mat-icon>
          删除全部已完成记录
        </button>
      </div>

      @if (loading()) {
        <div class="queue-empty">
          <mat-icon class="loading-icon">sync</mat-icon>
          <p>正在读取服务器上传记录...</p>
        </div>
      } @else if (items().length === 0) {
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

          <ng-container matColumnDef="status">
            <th mat-header-cell *matHeaderCellDef>状态</th>
            <td mat-cell *matCellDef="let item">
              <mat-chip [class]="'status-' + item.status">{{ statusLabel(item.status) }}</mat-chip>
            </td>
          </ng-container>

          <ng-container matColumnDef="actions">
            <th mat-header-cell *matHeaderCellDef></th>
            <td mat-cell *matCellDef="let item">
              <button mat-icon-button (click)="viewDetail(item.taskId)"
                      matTooltip="查看分析结果">
                <mat-icon>visibility</mat-icon>
              </button>
              <button mat-icon-button color="warn" (click)="removeItem(item.taskId)"
                      [disabled]="deletingId() === item.taskId || !isTerminal(item.status)"
                      [matTooltip]="isTerminal(item.status) ? '永久删除任务、图片和报告' : '分析完成后才能删除'">
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
    .loading-icon { animation: spin 1s linear infinite; }
    @keyframes spin { to { transform: rotate(360deg); } }
    .status-completed { background: #dcfce7; color: #166534; }
    .status-failed { background: #fee2e2; color: #991b1b; }
    .status-processing, .status-pending { background: #fef3c7; color: #92400e; }
  `]
})
export class QueueComponent implements OnInit {
  columns = ['fileName', 'size', 'uploadTime', 'status', 'actions'];
  items = signal<UploadRecord[]>([]);
  loading = signal(true);
  deleting = signal(false);
  deletingId = signal<string | null>(null);

  constructor(
    private router: Router,
    private snackBar: MatSnackBar,
    private taskService: TaskService,
  ) {}

  ngOnInit(): void {
    this.loadHistory();
  }

  viewDetail(taskId: string): void {
    this.router.navigate(['/detection', taskId]);
  }

  removeItem(taskId: string): void {
    const item = this.items().find(record => record.taskId === taskId);
    if (!item || !this.isTerminal(item.status)) return;
    if (!window.confirm(`确定永久删除“${item.fileName}”吗？相关图片和报告也会删除。`)) return;

    this.deletingId.set(taskId);
    this.taskService.deleteTask(taskId).subscribe({
      next: () => {
        this.removeFromViews([taskId]);
        this.deletingId.set(null);
        this.snackBar.open('任务、图片和报告已删除', '关闭', { duration: 2500 });
      },
      error: err => {
        this.deletingId.set(null);
        this.snackBar.open(err?.error?.message || '删除失败，请稍后重试', '关闭', { duration: 5000 });
      },
    });
  }

  clearAll(): void {
    const targets = this.deletableItems();
    if (!targets.length) return;
    if (!window.confirm(`确定永久删除 ${targets.length} 条已完成记录吗？相关图片和报告也会删除。`)) return;

    this.deleting.set(true);
    forkJoin(targets.map(item => this.taskService.deleteTask(item.taskId))).subscribe({
      next: () => {
        this.removeFromViews(targets.map(item => item.taskId));
        this.deleting.set(false);
        this.snackBar.open(`已删除 ${targets.length} 条记录`, '关闭', { duration: 2500 });
      },
      error: err => {
        this.deleting.set(false);
        this.loadHistory();
        this.snackBar.open(err?.error?.message || '部分记录删除失败，列表已刷新', '关闭', { duration: 5000 });
      },
    });
  }

  formatSize(bytes: number): string {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  }

  private loadHistory(): void {
    this.loading.set(true);
    this.taskService.listTasks().subscribe({
      next: tasks => {
        this.items.set(tasks.map(task => ({
          taskId: task.task_id,
          fileName: task.file_name,
          fileSize: task.file_size || 0,
          uploadTime: new Date(task.created_at).toLocaleString('zh-CN'),
          status: task.status,
          errorMessage: task.error_message,
        })));
        this.loading.set(false);
      },
      error: err => {
        this.items.set([]);
        this.loading.set(false);
        this.snackBar.open(err?.error?.message || '上传记录读取失败', '关闭', { duration: 5000 });
      },
    });
  }

  deletableItems(): UploadRecord[] {
    return this.items().filter(item => this.isTerminal(item.status));
  }

  isTerminal(status: UploadRecord['status']): boolean {
    return status === 'completed' || status === 'failed';
  }

  statusLabel(status: UploadRecord['status']): string {
    return ({
      pending: '等待中',
      processing: '分析中',
      completed: '已完成',
      failed: '失败',
    })[status];
  }

  private removeFromViews(taskIds: string[]): void {
    const deleted = new Set(taskIds);
    this.items.update(items => items.filter(item => !deleted.has(item.taskId)));
    try {
      const raw = localStorage.getItem(HISTORY_KEY);
      const localItems = raw ? JSON.parse(raw) : [];
      localStorage.setItem(
        HISTORY_KEY,
        JSON.stringify(localItems.filter((item: UploadRecord) => !deleted.has(item.taskId))),
      );
    } catch { /* server remains the source of truth */ }
  }
}
