import {
  Component,
  input,
  signal,
  computed,
  ElementRef,
  ViewChild,
  AfterViewInit,
  OnDestroy,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';

/**
 * CanvasViewerComponent — 双图对比画布
 *
 * 核心功能：
 * 1. 左侧原图 + 右侧掩码叠加图
 * 2. 鼠标滚轮缩放（两图联动）
 * 3. 拖拽平移（两图联动）
 * 4. 支持亮度/对比度调节（通过 CSS filter）
 */
@Component({
  selector: 'app-canvas-viewer',
  standalone: true,
  imports: [CommonModule, MatButtonModule, MatIconModule, MatTooltipModule],
  template: `
    <div class="viewer-container">
      <!-- 控制栏 -->
      <div class="viewer-controls">
        <button mat-icon-button matTooltip="放大" (click)="zoomIn()">
          <mat-icon>zoom_in</mat-icon>
        </button>
        <button mat-icon-button matTooltip="缩小" (click)="zoomOut()">
          <mat-icon>zoom_out</mat-icon>
        </button>
        <button mat-icon-button matTooltip="重置视图" (click)="resetView()">
          <mat-icon>fit_screen</mat-icon>
        </button>
        <span class="zoom-label">{{ zoomPercent() }}%</span>
      </div>

      <!-- 双图画布区域 -->
      <div class="canvas-area" #canvasArea [class.single-panel]="!hasMask()"
           (wheel)="onWheel($event)"
           (mousedown)="onMouseDown($event)"
           (mousemove)="onMouseMove($event)"
           (mouseup)="onMouseUp()"
           (mouseleave)="onMouseUp()">

        <!-- 左侧：原图 -->
        <div class="image-panel">
          <div class="panel-label">{{ hasMask() ? '原始图像' : '整图检测输入' }}</div>
          <div class="image-wrapper" [style.transform]="transformStyle()">
            <img [src]="originalImageUrl()"
                 [style.filter]="filterStyle()"
                 alt="原始图像"
                 draggable="false" />
          </div>
        </div>

        @if (hasMask()) {
          <!-- 分隔线 -->
          <div class="divider"></div>

          <!-- 右侧：掩码叠加图 -->
          <div class="image-panel">
            <div class="panel-label">区域定位结果</div>
            <div class="image-wrapper" [style.transform]="transformStyle()">
              <img [src]="originalImageUrl()"
                   [style.filter]="filterStyle()"
                   alt="原始图像底层"
                   draggable="false" />
              <img [src]="maskImageUrl()"
                   class="mask-overlay"
                   [style.opacity]="maskOpacity()"
                   alt="SAM/LoRA 掩码"
                   draggable="false" />
            </div>
          </div>
        }
      </div>
    </div>
  `,
  styles: [`
    .viewer-container {
      display: flex;
      flex-direction: column;
      height: 100%;
      background: #1a1a2e;
      border-radius: 8px;
      overflow: hidden;
    }

    .viewer-controls {
      display: flex;
      align-items: center;
      gap: 4px;
      padding: 8px 12px;
      background: #16213e;
      border-bottom: 1px solid #0f3460;

      button { color: #a0c4ff; }
      .zoom-label {
        margin-left: 8px;
        color: #a0c4ff;
        font-size: 0.8rem;
        min-width: 40px;
      }
    }

    .canvas-area {
      flex: 1;
      display: flex;
      overflow: hidden;
      cursor: grab;
      user-select: none;

      &:active { cursor: grabbing; }
    }
    .canvas-area.single-panel .image-panel { flex: 1 1 100%; }

    .image-panel {
      flex: 1;
      position: relative;
      display: flex;
      align-items: center;
      justify-content: center;
      overflow: hidden;

      .panel-label {
        position: absolute;
        top: 8px;
        left: 12px;
        background: rgba(0, 0, 0, 0.6);
        color: #fff;
        padding: 4px 10px;
        border-radius: 4px;
        font-size: 0.75rem;
        z-index: 10;
      }
    }

    .image-wrapper {
      position: relative;
      transform-origin: center center;
      transition: none;

      img {
        max-width: 100%;
        max-height: 100%;
        display: block;
      }
    }

    .mask-overlay {
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      mix-blend-mode: multiply;
      pointer-events: none;
    }

    .divider {
      width: 2px;
      background: #0f3460;
    }
  `],
})
export class CanvasViewerComponent implements AfterViewInit, OnDestroy {
  /** 原图 URL */
  originalImageUrl = input('');
  /** 掩码图 URL */
  maskImageUrl = input('');
  /** 是否有掩码 */
  hasMask = input(true);
  /** 亮度 0~200 */
  brightness = input(100);
  /** 对比度 0~200 */
  contrast = input(100);

  @ViewChild('canvasArea') canvasAreaRef!: ElementRef<HTMLElement>;

  // 缩放与平移状态
  private _scale = signal(1);
  private _translateX = signal(0);
  private _translateY = signal(0);
  private _maskOpacity = signal(0.6);

  // 拖拽状态
  private isPanning = false;
  private startX = 0;
  private startY = 0;
  private startTranslateX = 0;
  private startTranslateY = 0;

  /** 缩放百分比显示 */
  zoomPercent = computed(() => Math.round(this._scale() * 100));

  /** CSS transform 字符串 — 两张图共享同一个变换 */
  transformStyle = computed(
    () => `translate(${this._translateX()}px, ${this._translateY()}px) scale(${this._scale()})`
  );

  /** CSS filter 字符串 — 亮度/对比度调节 */
  filterStyle = computed(
    () => `brightness(${this.brightness()}%) contrast(${this.contrast()}%)`
  );

  /** 掩码透明度 */
  maskOpacity = this._maskOpacity.asReadonly();

  ngAfterViewInit(): void {
    // 阻止画布区域的默认滚动行为
    this.canvasAreaRef?.nativeElement.addEventListener('wheel', (e) => e.preventDefault(), { passive: false });
  }

  ngOnDestroy(): void {
    // cleanup handled by Angular
  }

  /** 滚轮缩放 */
  onWheel(event: WheelEvent): void {
    event.preventDefault();
    // 触控板会连续发送大量小 delta；按实际 delta 做平滑指数缩放，
    // 并限制单次变化，避免双指缩放瞬间跳到极值。
    const delta = Math.max(-40, Math.min(40, event.deltaY));
    const factor = Math.exp(-delta * 0.0025);
    const newScale = Math.max(0.25, Math.min(4, this._scale() * factor));
    this._scale.set(newScale);
  }

  /** 拖拽开始 */
  onMouseDown(event: MouseEvent): void {
    this.isPanning = true;
    this.startX = event.clientX;
    this.startY = event.clientY;
    this.startTranslateX = this._translateX();
    this.startTranslateY = this._translateY();
  }

  /** 拖拽移动 */
  onMouseMove(event: MouseEvent): void {
    if (!this.isPanning) return;
    const dx = event.clientX - this.startX;
    const dy = event.clientY - this.startY;
    this._translateX.set(this.startTranslateX + dx);
    this._translateY.set(this.startTranslateY + dy);
  }

  /** 拖拽结束 */
  onMouseUp(): void {
    this.isPanning = false;
  }

  /** 放大按钮 */
  zoomIn(): void {
    this._scale.update((s) => Math.min(4, s * 1.15));
  }

  /** 缩小按钮 */
  zoomOut(): void {
    this._scale.update((s) => Math.max(0.25, s / 1.15));
  }

  /** 重置视图 */
  resetView(): void {
    this._scale.set(1);
    this._translateX.set(0);
    this._translateY.set(0);
  }

  /** 外部调节掩码透明度 */
  setMaskOpacity(value: number): void {
    this._maskOpacity.set(value);
  }
}
