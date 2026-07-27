import {
  Component,
  Input,
  OnChanges,
  SimpleChanges,
  ElementRef,
  ViewChild,
  AfterViewInit,
  OnDestroy,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import * as echarts from 'echarts';
import { ModelProbability } from '../../../core/services/mock-data.service';

/**
 * ProbabilityChartComponent — AI 概率图表
 *
 * 用 ECharts 渲染 4 类生成模型（CycleGAN, DDPM, Pix2Pix, StyleGAN2-ADA）
 * 的伪造概率分布，支持柱状图和雷达图两种模式
 */
@Component({
  selector: 'app-probability-chart',
  standalone: true,
  imports: [CommonModule, MatIconModule],
  template: `
    <div class="chart-container">
      <h4 class="section-title">
        <mat-icon>analytics</mat-icon>
        AI 模型概率分析
      </h4>
      <div class="chart-wrapper" #chartContainer></div>
    </div>
  `,
  styles: [`
    .chart-container {
      padding: 16px;
      background: #fafafa;
      border-radius: 8px;
      border: 1px solid #e0e0e0;
    }

    .section-title {
      display: flex;
      align-items: center;
      gap: 8px;
      margin: 0 0 12px;
      font-size: 0.95rem;
      color: #333;

      mat-icon { color: #1976d2; }
    }

    .chart-wrapper {
      width: 100%;
      height: 250px;
    }
  `],
})
export class ProbabilityChartComponent implements AfterViewInit, OnChanges, OnDestroy {
  @Input() probabilities: ModelProbability[] = [];
  @ViewChild('chartContainer') chartContainerRef!: ElementRef<HTMLElement>;

  private chart: echarts.ECharts | null = null;
  private resizeObserver: ResizeObserver | null = null;

  ngAfterViewInit(): void {
    this.initChart();
    this.updateChart();

    // 监听容器尺寸变化，自动 resize
    this.resizeObserver = new ResizeObserver(() => {
      this.chart?.resize();
    });
    this.resizeObserver.observe(this.chartContainerRef.nativeElement);
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['probabilities'] && this.chart) {
      this.updateChart();
    }
  }

  ngOnDestroy(): void {
    this.resizeObserver?.disconnect();
    this.chart?.dispose();
  }

  private initChart(): void {
    this.chart = echarts.init(this.chartContainerRef.nativeElement);
  }

  private updateChart(): void {
    if (!this.chart || !this.probabilities.length) return;

    const models = this.probabilities.map((p) => p.model);
    const values = this.probabilities.map((p) => +(p.probability * 100).toFixed(1));

    // 找出最高概率的模型，用不同颜色高亮
    const maxIdx = values.indexOf(Math.max(...values));
    const colors = values.map((_, i) => (i === maxIdx ? '#f44336' : '#1976d2'));

    const option: echarts.EChartsOption = {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter: (params: any) => {
          const p = params[0];
          return `${p.name}<br/>概率: <strong>${p.value}%</strong>`;
        },
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '8%',
        top: '8%',
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: models,
        axisLabel: {
          fontSize: 11,
          interval: 0,
          rotate: 0,
        },
      },
      yAxis: {
        type: 'value',
        max: 100,
        axisLabel: {
          formatter: '{value}%',
          fontSize: 11,
        },
      },
      series: [
        {
          type: 'bar',
          data: values.map((v, i) => ({
            value: v,
            itemStyle: { color: colors[i] },
          })),
          barWidth: '40%',
          label: {
            show: true,
            position: 'top',
            formatter: '{c}%',
            fontSize: 12,
            fontWeight: 'bold',
          },
        },
      ],
    };

    this.chart.setOption(option);
  }
}
