/**
 * Metrics API service functions.
 */

import { apiClient } from './api';
import type {
  Metric,
  TimeSeriesResponse,
  DashboardSummary,
  SystemStatus,
} from '../types/metric';

export const metricsApi = {
  getLatest: async (hostname?: string): Promise<Metric | null> => {
    const params = hostname ? { hostname } : {};
    const response = await apiClient.get<Metric | null>('/api/metrics/latest', { params });
    return response.data;
  },

  getHistory: async (minutes: number = 60, hostname?: string): Promise<TimeSeriesResponse> => {
    const params: Record<string, unknown> = { minutes };
    if (hostname) params.hostname = hostname;
    const response = await apiClient.get<TimeSeriesResponse>('/api/metrics/history', { params });
    return response.data;
  },

  getDashboardSummary: async (): Promise<DashboardSummary> => {
    const response = await apiClient.get<DashboardSummary>('/api/dashboard/summary');
    return response.data;
  },

  getDashboardTimeseries: async (minutes: number = 60, hostname?: string): Promise<TimeSeriesResponse> => {
    const params: Record<string, unknown> = { minutes };
    if (hostname) params.hostname = hostname;
    const response = await apiClient.get<TimeSeriesResponse>('/api/dashboard/timeseries', { params });
    return response.data;
  },

  getSystemStatus: async (): Promise<SystemStatus> => {
    const response = await apiClient.get<SystemStatus>('/api/system/status');
    return response.data;
  },
};
