import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { HealthApiService } from './health-api.service';

describe('HealthApiService', () => {
  it('requests the backend health endpoint', () => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    const service = TestBed.inject(HealthApiService);
    const http = TestBed.inject(HttpTestingController);

    service.check().subscribe((response) => {
      expect(response).toEqual({ status: 'ok', service: 'blotguard-api' });
    });

    http.expectOne('/api/v1/health').flush({
      status: 'ok',
      service: 'blotguard-api',
    });
    http.verify();
  });
});
