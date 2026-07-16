import { Component, Output, EventEmitter, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatSliderModule } from '@angular/material/slider';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { FormsModule } from '@angular/forms';

/**
 * ForensicToolbarComponent — 法医工具箱
 *
 * 提供实时调节图像的：
 * - 亮度 (Brightness)
 * - 对比度 (Contrast)
 * - 掩码透明度 (Mask Opacity)
 */
@Component({
  selector: 'app-forensic-toolbar',
  standalone: true,
  imports: [CommonModule, MatSliderModule, MatIconModule, MatButtonModule, FormsModule],
  template: `
    <div class="toolbar-container">
      <h4 class="toolbar-title">
        <mat-icon>tune</mat-icon>
        法医工具箱
      </h4>

      <!-- 亮度 -->
      <div class="slider-group">
        <label>
          <mat-icon>brightness_6</mat-icon>
          亮度
          <span class="value">{{ brightness() }}%</span>
        </label>
        <mat-slider min="0" max="200" step="1" [discrete]="true">
          <input matSliderThumb [ngModel]="brightness()" (ngModelChange)="onBrightnessChange($event)" />
        </mat-slider>
      </div>

      <!-- 对比度 -->
      <div class="slider-group">
        <label>
          <mat-icon>contrast</mat-icon>
          对比度
          <span class="value">{{ contrast() }}%</span>
        </label>
        <mat-slider min="0" max="200" step="1" [discrete]="true">
          <input matSliderThumb [ngModel]="contrast()" (ngModelChange)="onContrastChange($event)" />
        </mat-slider>
      </div>

      <!-- 掩码透明度 -->
      <div class="slider-group">
        <label>
          <mat-icon>layers</mat-icon>
          掩码透明度
          <span class="value">{{ maskOpacityPercent() }}%</span>
        </label>
        <mat-slider min="0" max="100" step="1" [discrete]="true">
          <input matSliderThumb [ngModel]="maskOpacityPercent()" (ngModelChange)="onMaskOpacityChange($event)" />
        </mat-slider>
      </div>

      <!-- 重置按钮 -->
      <button mat-stroked-button class="reset-btn" (click)="resetAll()">
        <mat-icon>restart_alt</mat-icon>
        重置
      </button>
    </div>
  `,
  styles: [`
    .toolbar-container {
      padding: 16px;
      background: #fafafa;
      border-radius: 8px;
      border: 1px solid #e0e0e0;
    }

    .toolbar-title {
      display: flex;
      align-items: center;
      gap: 8px;
      margin: 0 0 16px;
      font-size: 0.95rem;
      color: #333;
    }

    .slider-group {
      margin-bottom: 16px;

      label {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 0.82rem;
        color: #555;
        margin-bottom: 4px;

        .value {
          margin-left: auto;
          font-weight: 500;
          color: #1976d2;
        }

        mat-icon {
          font-size: 18px;
          width: 18px;
          height: 18px;
        }
      }

      mat-slider {
        width: 100%;
      }
    }

    .reset-btn {
      width: 100%;
      margin-top: 8px;
    }
  `],
})
export class ForensicToolbarComponent {
  @Output() brightnessChange = new EventEmitter<number>();
  @Output() contrastChange = new EventEmitter<number>();
  @Output() maskOpacityChange = new EventEmitter<number>();

  brightness = signal(100);
  contrast = signal(100);
  maskOpacityPercent = signal(60); // 0~100 对应实际的 0~1

  onBrightnessChange(value: number): void {
    this.brightness.set(value);
    this.brightnessChange.emit(value);
  }

  onContrastChange(value: number): void {
    this.contrast.set(value);
    this.contrastChange.emit(value);
  }

  onMaskOpacityChange(value: number): void {
    this.maskOpacityPercent.set(value);
    this.maskOpacityChange.emit(value / 100);
  }

  resetAll(): void {
    this.onBrightnessChange(100);
    this.onContrastChange(100);
    this.onMaskOpacityChange(60);
  }
}
