import { Component, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { FormsModule } from '@angular/forms';
import { MockDataService, SampleEntry } from '../../core/services/mock-data.service';

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
      </header>

      <div class="filter-bar">
        <mat-button-toggle-group [(ngModel)]="filterType" hideSingleSelectionIndicator>
          <mat-button-toggle value="all">全部 ({{ samples.length }})</mat-button-toggle>
          <mat-button-toggle value="original">真实 ({{ originalCount() }})</mat-button-toggle>
          <mat-button-toggle value="generated">AI生成 ({{ generatedCount() }})</mat-button-toggle>
        </mat-button-toggle-group>
      </div>

      <div class="gallery-grid">
        @for (sample of filteredSamples(); track sample.id) {
          <mat-card class="sample-card" (click)="openDetail(sample.id)">
            <img [src]="sample.assetPath" [alt]="sample.fileName" class="sample-thumb" loading="lazy" />
            <mat-card-content>
              <p class="file-name">{{ sample.fileName }}</p>
              <div class="card-meta">
                <mat-chip [style.backgroundColor]="getRiskColor(sample.probabilityGenerated)">
                  {{ (sample.probabilityGenerated * 100).toFixed(1) }}% 生成概率
                </mat-chip>
                <span class="generator-tag">{{ getGeneratorLabel(sample.generator) }}</span>
              </div>
              <div class="prediction-row">
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
    .filter-bar { margin-bottom: 24px; }
    .gallery-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 20px;
    }
    .sample-card {
      cursor: pointer;
      transition: transform 0.2s, box-shadow 0.2s;
    }
    .sample-card:hover {
      transform: translateY(-4px);
      box-shadow: 0 8px 24px rgba(0,0,0,0.12);
    }
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
  `],
})
export class GalleryComponent {
  samples: SampleEntry[];
  filterType = 'all';

  constructor(private mockData: MockDataService, private router: Router) {
    this.samples = this.mockData.getSampleEntries();
  }

  originalCount = computed(() => this.samples.filter(s => s.expectedClass === 'original').length);
  generatedCount = computed(() => this.samples.filter(s => s.expectedClass === 'generated').length);

  filteredSamples = computed(() => {
    if (this.filterType === 'all') return this.samples;
    return this.samples.filter(s => s.expectedClass === this.filterType);
  });

  getRiskColor(prob: number): string {
    if (prob >= 0.7) return '#ffcdd2';
    if (prob >= 0.4) return '#fff3e0';
    return '#e8f5e9';
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
