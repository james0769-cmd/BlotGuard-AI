import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { DetectionApiService } from './detection-api.service';

describe('DetectionApiService', () => {
  it('uploads an image to the real detector endpoint', () => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    const service = TestBed.inject(DetectionApiService);
    const http = TestBed.inject(HttpTestingController);
    const image = new File(['image'], 'sample.png', { type: 'image/png' });

    service.detect(image).subscribe();

    const request = http.expectOne('/api/v1/detect');
    expect(request.request.method).toBe('POST');
    expect(request.request.body.get('image')).toBe(image);
    request.flush({});
    http.verify();
  });
});
