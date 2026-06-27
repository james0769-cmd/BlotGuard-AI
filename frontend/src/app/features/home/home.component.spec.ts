import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';

import { HealthApiService } from '../../core/services/health-api.service';
import { HomeComponent } from './home.component';

describe('HomeComponent', () => {
  it('shows that the backend is online after a successful health check', async () => {
    TestBed.configureTestingModule({
      imports: [HomeComponent],
      providers: [
        {
          provide: HealthApiService,
          useValue: {
            check: () => of({ status: 'ok', service: 'blotguard-api' }),
          },
        },
      ],
    });

    const fixture = TestBed.createComponent(HomeComponent);
    fixture.detectChanges();
    await fixture.whenStable();

    expect(fixture.nativeElement.textContent).toContain('后端服务在线');
  });
});
