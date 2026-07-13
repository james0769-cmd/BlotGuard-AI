import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

export interface DetectionResponse {
  task: 'detect';
  image: string;
  device: string;
  logit: number;
  probability_generated: number;
  prediction: 'original' | 'generated';
  threshold: number;
  model_version: string;
  weight_sha256: string;
  mask_image_url: null;
  suspect_regions: unknown[];
}

@Injectable({ providedIn: 'root' })
export class DetectionApiService {
  private readonly http = inject(HttpClient);

  detect(image: File): Observable<DetectionResponse> {
    const form = new FormData();
    form.append('image', image);
    return this.http.post<DetectionResponse>('/api/v1/detect', form);
  }
}
