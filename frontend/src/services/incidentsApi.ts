/**
 * Incidents API service functions.
 */

import { apiClient } from './api';
import type { Incident, IncidentListResponse } from '../types/incident';
import type { AnomalyListResponse } from '../types/anomaly';

export interface IncidentFilters {
  status?: string;
  severity?: string;
  hostname?: string;
  page?: number;
  page_size?: number;
}

export const incidentsApi = {
  list: async (filters: IncidentFilters = {}): Promise<IncidentListResponse> => {
    const response = await apiClient.get<IncidentListResponse>('/api/incidents', {
      params: filters,
    });
    return response.data;
  },

  getById: async (incidentId: string): Promise<Incident> => {
    const response = await apiClient.get<Incident>(`/api/incidents/${incidentId}`);
    return response.data;
  },

  analyze: async (incidentId: string): Promise<Incident> => {
    const response = await apiClient.post<Incident>(`/api/incidents/${incidentId}/analyze`);
    return response.data;
  },

  simulateAssessment: async (hostname?: string): Promise<Incident> => {
    const params: Record<string, string> = {};
    if (hostname) params.hostname = hostname;
    const response = await apiClient.post<Incident>(
      '/api/incidents/simulate-assessment-scenario',
      null,
      { params }
    );
    return response.data;
  },

  updateStatus: async (incidentId: string, status: string): Promise<Incident> => {
    const response = await apiClient.patch<Incident>(`/api/incidents/${incidentId}`, {
      status,
    });
    return response.data;
  },

  remediate: async (
    incidentId: string,
    command: string
  ): Promise<{
    success: boolean;
    incident_id: string;
    command: string;
    stdout: string;
    stderr: string;
    exit_code: number;
    duration_ms: number;
    error?: string | null;
    message: string;
  }> => {
    const response = await apiClient.post(`/api/incidents/${incidentId}/remediate`, { command });
    return response.data;
  },
};

export const anomaliesApi = {
  list: async (minutes: number = 60, severity?: string): Promise<AnomalyListResponse> => {
    const params: Record<string, unknown> = { minutes };
    if (severity) params.severity = severity;
    const response = await apiClient.get<AnomalyListResponse>('/api/anomalies', { params });
    return response.data;
  },
};
