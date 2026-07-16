import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { SuspectRegion } from '../../../core/services/mock-data.service';

/**
 * SuspectListComponent — 可疑区域列表侧边栏
 *
 * 展示所有 AI 检测到的可疑区域，每项包含：
 * - 区域名称
 * - 置信度百分比（带颜色编码）
 * - 简短描述
 * 点击某项时可高亮对应画布区域
 */
@Component({
  selector: 'app-suspect-list',
  standalone: true,
  imports: [CommonModule, MatListModule, MatIconModule, MatChipsModule],
  template: `
    <div class="suspect-container">
      <h4 class="section-title">
        <mat-icon>warning_amber</mat-icon>
        可疑区域 ({{ regions.length }})
      </h4>

      <div class="region-list">
        @for (region of regions; track region.id) {
          <div class="region-card"
               [class.active]="selectedId === region.id"
               (click)="onSelect(region)">
            <div class="region-header">
              <span class="region-label">{{ region.label }}</span>
              <span class="confidence-badge" [style.backgroundColor]="getConfidenceColor(region.confidence)">
                {{ (region.confidence * 100).toFixed(0) }}%
              </span>
            </div>
            <p class="region-desc">{{ region.description }}</p>
            <div class="confidence-bar">
              <div class="confidence-fill"
                   [style.width.%]="region.confidence * 100"
                   [style.backgroundColor]="getConfidenceColor(region.confidence)">
              </div>
            </div>
          </div>
        }
      </div>

      @if (regions.length === 0) {
        <div class="empty-state">
          <mat-icon>check_circle</mat-icon>
          <p>未检测到可疑区域</p>
        </div>
      }
    </div>
  `,
  styles: [`
    .suspect-container {
      padding: 16px;
    }

    .section-title {
      display: flex;
      align-items: center;
      gap: 8px;
      margin: 0 0 12px;
      font-size: 0.95rem;
      color: #333;

      mat-icon { color: #ff9800; }
    }

    .region-list {
      display: flex;
      flex-direction: column;
      gap: 10px;
    }

    .region-card {
      padding: 12px;
      border: 1px solid #e0e0e0;
      border-radius: 8px;
      cursor: pointer;
      transition: all 0.2s;

      &:hover {
        border-color: #1976d2;
        background: #f5f9ff;
      }

      &.active {
        border-color: #1976d2;
        background: #e3f2fd;
        box-shadow: 0 0 0 2px rgba(25, 118, 210, 0.2);
      }
    }

    .region-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 6px;
    }

    .region-label {
      font-weight: 500;
      font-size: 0.88rem;
      color: #333;
    }

    .confidence-badge {
      color: #fff;
      padding: 2px 8px;
      border-radius: 12px;
      font-size: 0.75rem;
      font-weight: 600;
    }

    .region-desc {
      font-size: 0.78rem;
      color: #666;
      margin: 0 0 8px;
      line-height: 1.4;
    }

    .confidence-bar {
      height: 4px;
      background: #e0e0e0;
      border-radius: 2px;
      overflow: hidden;
    }

    .confidence-fill {
      height: 100%;
      border-radius: 2px;
      transition: width 0.3s ease;
    }

    .empty-state {
      text-align: center;
      padding: 32px 16px;
      color: #4caf50;

      mat-icon {
        font-size: 48px;
        width: 48px;
        height: 48px;
      }

      p {
        margin-top: 8px;
        color: #666;
      }
    }
  `],
})
export class SuspectListComponent {
  @Input() regions: SuspectRegion[] = [];
  @Input() selectedId: number | null = null;
  @Output() regionSelected = new EventEmitter<SuspectRegion>();

  onSelect(region: SuspectRegion): void {
    this.regionSelected.emit(region);
  }

  /** 根据置信度返回颜色：红/橙/黄 */
  getConfidenceColor(confidence: number): string {
    if (confidence >= 0.8) return '#f44336'; // 高风险 - 红
    if (confidence >= 0.6) return '#ff9800'; // 中风险 - 橙
    return '#ffc107'; // 低风险 - 黄
  }
}
