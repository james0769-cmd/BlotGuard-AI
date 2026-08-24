import { RiskLevel } from './services/task.service';

export type RiskFilter = 'all' | RiskLevel;

export const RISK_BOUNDARIES = {
  veryHigh: 0.6720226014610423,
  high: 0.47028575870349404,
  medium: 0.237057370700807,
  low: 0.11865540902281878,
} as const;

export function riskLevelForScore(score: number): RiskLevel {
  if (score < RISK_BOUNDARIES.low) return 'very_low';
  if (score < RISK_BOUNDARIES.medium) return 'low';
  if (score < RISK_BOUNDARIES.high) return 'medium';
  if (score < RISK_BOUNDARIES.veryHigh) return 'high';
  return 'very_high';
}

export function riskLabel(level: RiskLevel | null | undefined): string {
  switch (level) {
    case 'very_high': return '高置信生成';
    case 'high': return '高疑似生成';
    case 'medium': return '不确定';
    case 'low': return '高疑似真实';
    case 'very_low': return '高置信真实';
    default: return '待分析';
  }
}

export function riskBackground(level: RiskLevel | null | undefined): string {
  switch (level) {
    case 'very_high': return '#ffcdd2';
    case 'high': return '#fff3e0';
    case 'medium': return '#fff9c4';
    case 'low': return '#c8e6c9';
    case 'very_low': return '#e8f5e9';
    default: return '#f5f5f5';
  }
}

export function riskForeground(level: RiskLevel | null | undefined): string {
  switch (level) {
    case 'very_high': return '#d32f2f';
    case 'high': return '#f57c00';
    case 'medium': return '#f9a825';
    case 'low': return '#66bb6a';
    case 'very_low': return '#388e3c';
    default: return '#9e9e9e';
  }
}
