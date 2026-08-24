import { Component, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { FormsModule } from '@angular/forms';
import { MockDataService, SampleEntry } from '../../core/services/mock-data.service';
import {
  RiskFilter,
  riskBackground,
  riskLabel,
  riskLevelForScore,
} from '../../core/risk-level';

@Component({
  selector: 'app-gallery',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatChipsModule,
    MatButtonModule,
    MatIconModule,
    MatButtonToggleModule,
    FormsModule,
  ],
  template: `
    <div class="gallery-page">
      <header class="gallery-header">
        <h1>样本图库</h1>
        <p class="subtitle">模型团队提供的 25 张 Western Blot 样本及检测结果</p>
        <p class="experimental-note">五级风险为实验性结果；真实标签与模型预测分别展示。</p>
      </header>

      <!-- 置信度分层过滤 -->
      <div class="filter-bar">
        <mat-button-toggle-group [ngModel]="filterType()" (ngModelChange)="filterType.set($event)"
                                 hideSingleSelectionIndicator>
          <mat-button-toggle value="all">全部 ({{ samples.length }})</mat-button-toggle>
          <mat-button-toggle value="very_high">
            高置信生成 ({{ veryHighCount() }})
          </mat-button-toggle>
          <mat-button-toggle value="high">
            高疑似生成 ({{ highCount() }})
          </mat-button-toggle>
          <mat-button-toggle value="medium">
            不确定 ({{ mediumCount() }})
          </mat-button-toggle>
          <mat-button-toggle value="low">
            高疑似真实 ({{ lowCount() }})
          </mat-button-toggle>
          <mat-button-toggle value="very_low">
            高置信真实 ({{ veryLowCount() }})
          </mat-button-toggle>
        </mat-button-toggle-group>
      </div>

      <div class="tier-legend">
        <span class="legend-item"><span class="dot high"></span>高置信生成 (&ge;67.2%)</span>
        <span class="legend-item"><span class="dot suspected"></span>高疑似生成 (47.0%~67.2%)</span>
        <span class="legend-item"><span class="dot uncertain"></span>不确定 (23.7%~47.0%)</span>
        <span class="legend-item"><span class="dot likely-real"></span>高疑似真实 (11.9%~23.7%)</span>
        <span class="legend-item"><span class="dot high-real"></span>高置信真实 (&lt;11.9%)</span>
      </div>

      <div class="gallery-grid">
        @for (sample of filteredSamples(); track sample.id) {
          <mat-card class="sample-card" (click)="openDetail(sample.id)">
            <div class="tier-badge" [class]="getTierClass(sample.scoreGenerated)">
              {{ getTierLabel(sample.scoreGenerated) }}
            </div>
            <img [src]="sample.assetPath" [alt]="sample.fileName" class="sample-thumb" loading="lazy" />
            <mat-card-content>
              <p class="file-name">{{ sample.fileName }}</p>
              <div class="card-meta">
                <mat-chip [style.backgroundColor]="getRiskColor(sample.scoreGenerated)">
                  {{ (sample.scoreGenerated * 100).toFixed(1) }}% 生成风险分数
                </mat-chip>
                <span class="generator-tag">{{ getGeneratorLabel(sample.generator) }}</span>
              </div>
              <div class="prediction-row">
                <span class="ground-truth-tag" [class.generated]="sample.expectedClass === 'generated'">
                  真实: {{ sample.expectedClass === 'generated' ? 'AI生成' : '真实原图' }}
                </span>
                <mat-icon [style.color]="sample.prediction === 'generated' ? '#f44336' : '#4caf50'">
                  {{ sample.prediction === 'generated' ? 'warning' : 'check_circle' }}
                </mat-icon>
                <span>预测: {{ sample.prediction === 'generated' ? 'AI生成' : '真实原图' }}</span>
              </div>
            </mat-card-content>
          </mat-card>
        }
      </div>
    </div>
  `,
  styles: [`
    .gallery-page { padding: 24px; max-width: 1400px; margin: 0 auto; }
    .gallery-header { margin-bottom: 24px; }
    .gallery-header h1 { margin: 0 0 8px; font-size: 28px; }
    .subtitle { color: var(--mat-sys-on-surface-variant); margin: 0; }
    .experimental-note { margin: 8px 0 0; color: #92400e; font-size: 13px; }
    .filter-bar { margin-bottom: 16px; }
    .tier-legend {
      display: flex;
      gap: 16px;
      margin-bottom: 20px;
      flex-wrap: wrap;
      font-size: 12px;
      color: var(--mat-sys-on-surface-variant);
    }
    .legend-item { display: flex; align-items: center; gap: 4px; }
    .dot {
      width: 10px; height: 10px; border-radius: 50%;
    }
    .dot.high { background: #d32f2f; }
    .dot.suspected { background: #f57c00; }
    .dot.uncertain { background: #fbc02d; }
    .dot.likely-real { background: #66bb6a; }
    .dot.high-real { background: #388e3c; }
    .gallery-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 20px;
    }
    .sample-card {
      cursor: pointer;
      transition: transform 0.2s, box-shadow 0.2s;
      position: relative;
    }
    .sample-card:hover {
      transform: translateY(-4px);
      box-shadow: 0 8px 24px rgba(0,0,0,0.12);
    }
    .tier-badge {
      position: absolute;
      top: 8px;
      right: 8px;
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 500;
      color: #fff;
      z-index: 2;
    }
    .tier-badge.tier-high { background: #d32f2f; }
    .tier-badge.tier-suspected { background: #f57c00; }
    .tier-badge.tier-uncertain { background: #f9a825; color: #333; }
    .tier-badge.tier-likely-real { background: #66bb6a; }
    .tier-badge.tier-high-real { background: #388e3c; }
    .sample-thumb {
      width: 100%;
      height: 180px;
      object-fit: cover;
      border-radius: 12px 12px 0 0;
    }
    .file-name {
      font-size: 12px;
      color: var(--mat-sys-on-surface-variant);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      margin: 8px 0 4px;
    }
    .card-meta {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
      margin-bottom: 8px;
    }
    .generator-tag {
      font-size: 11px;
      padding: 2px 8px;
      border-radius: 10px;
      background: var(--mat-sys-surface-variant);
      color: var(--mat-sys-on-surface-variant);
    }
    .prediction-row {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 13px;
    }
    .prediction-row mat-icon { font-size: 18px; width: 18px; height: 18px; }
    .ground-truth-tag {
      font-size: 11px;
      padding: 1px 6px;
      border-radius: 4px;
      font-weight: 500;
    }
    .ground-truth-tag:not(.generated) { background: #c8e6c9; color: #2e7d32; }
    .ground-truth-tag.generated { background: #ffcdd2; color: #c62828; }
  `],
})
export class GalleryComponent {
  samples: SampleEntry[];
  filterType = signal<RiskFilter>('all');

  constructor(private mockData: MockDataService, private router: Router) {
    this.samples = this.mockData.getSampleEntries();
  }

  /** 5级风险计数 */
  veryHighCount = computed(() => this.samples.filter(s => riskLevelForScore(s.scoreGenerated) === 'very_high').length);
  highCount = computed(() => this.samples.filter(s => riskLevelForScore(s.scoreGenerated) === 'high').length);
  mediumCount = computed(() => this.samples.filter(s => riskLevelForScore(s.scoreGenerated) === 'medium').length);
  lowCount = computed(() => this.samples.filter(s => riskLevelForScore(s.scoreGenerated) === 'low').length);
  veryLowCount = computed(() => this.samples.filter(s => riskLevelForScore(s.scoreGenerated) === 'very_low').length);

  filteredSamples = computed(() => {
    const filter = this.filterType();
    return filter === 'all'
      ? this.samples
      : this.samples.filter(s => riskLevelForScore(s.scoreGenerated) === filter);
  });

  getTierClass(prob: number): string {
    switch (riskLevelForScore(prob)) {
      case 'very_high': return 'tier-high';
      case 'high': return 'tier-suspected';
      case 'medium': return 'tier-uncertain';
      case 'low': return 'tier-likely-real';
      case 'very_low': return 'tier-high-real';
    }
  }

  getTierLabel(prob: number): string {
    return riskLabel(riskLevelForScore(prob));
  }

  getRiskColor(prob: number): string {
    return riskBackground(riskLevelForScore(prob));
  }

  getGeneratorLabel(gen: string): string {
    const labels: Record<string, string> = {
      real: '真实',
      stylegan2ada: 'StyleGAN2-ADA',
      cyclegan: 'CycleGAN',
      pix2pix: 'Pix2Pix',
      ddpm: 'DDPM',
    };
    return labels[gen] || gen;
  }

  openDetail(id: string): void {
    this.router.navigate(['/detection', id]);
  }
}
