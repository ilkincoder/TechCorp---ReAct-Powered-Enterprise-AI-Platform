import { useState, useEffect } from 'react';
import type { DashboardStats } from '@/types/dashboard';
import { MOCK_DASHBOARD_DATA, transformApiResponse } from '@/data/dashboardData';

interface UseDashboardDataResult {
  data: DashboardStats | null;
  loading: boolean;
  error: string | null;
  usingMockData: boolean;
}

export function useDashboardData(): UseDashboardDataResult {
  const [data, setData] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [usingMockData, setUsingMockData] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function fetchData() {
      try {
        const res = await fetch('http://localhost:8000/dashboard/stats');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const apiData = await res.json();
        if (!cancelled) {
          setData(transformApiResponse(apiData));
          setUsingMockData(false);
          setError(null);
        }
      } catch {
        // Fallback to mock data silently
        if (!cancelled) {
          setData(MOCK_DASHBOARD_DATA);
          setUsingMockData(true);
          setError(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchData();
    return () => { cancelled = true; };
  }, []);

  return { data, loading, error, usingMockData };
}
