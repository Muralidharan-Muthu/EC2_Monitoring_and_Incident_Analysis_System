/**
 * Monitoring API client for remote EC2 operations.
 * All paths use /api/ prefix to match the FastAPI route registration.
 */

import { apiClient } from './api';

export interface SSHStatusData {
  connected: boolean;
  hostname: string | null;
  timestamp: string;
  status: 'CONNECTED' | 'DEGRADED' | 'UNAVAILABLE';
  latency_ms: number | null;
  error: string | null;
}

export interface MonitoringResponse<T> {
  success: boolean;
  data: T;
  incident_detected?: boolean;
  incident_id?: string | null;
  error: { code: string; message: string } | null;
}

export interface EC2Instance {
  instance_id: string;
  name: string;
  instance_type: string;
  public_dns: string;
  public_ip: string;
  state: string;
  region: string;
  launch_time: string | null;
}

export const monitoringApi = {
  getStatus: async (): Promise<MonitoringResponse<SSHStatusData>> => {
    const response = await apiClient.get<MonitoringResponse<SSHStatusData>>('/api/monitoring/status');
    return response.data;
  },

  getCurrent: async (): Promise<MonitoringResponse<any>> => {
    const response = await apiClient.get<MonitoringResponse<any>>('/api/monitoring/current');
    return response.data;
  },

  collectNow: async (): Promise<MonitoringResponse<any>> => {
    const response = await apiClient.post<MonitoringResponse<any>>('/api/monitoring/collect');
    return response.data;
  },

  resetDatabase: async (): Promise<{ success: boolean; message?: string; error?: any }> => {
    const response = await apiClient.post<{ success: boolean; message?: string; error?: any }>('/api/monitoring/reset-database');
    return response.data;
  },

  configureHost: async (payload: { host: string; username?: string; port?: number }): Promise<any> => {
    const response = await apiClient.post<any>('/api/monitoring/configure-host', payload);
    return response.data;
  },

  /** Fetch all running EC2 instances from AWS via boto3 — no manual copy-paste needed */
  discoverInstances: async (): Promise<{ success: boolean; instances: EC2Instance[]; count: number; region?: string; error?: any }> => {
    const response = await apiClient.get('/api/monitoring/discover-instances');
    return response.data;
  },

  /** One-click: auto-discover first running instance, SSH connect, and ingest metrics */
  autoConnect: async (): Promise<any> => {
    const response = await apiClient.post('/api/monitoring/auto-connect');
    return response.data;
  },
};

export default monitoringApi;
