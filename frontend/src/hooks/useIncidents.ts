/**
 * Custom hooks for fetching incident data.
 */

import { useState, useEffect, useCallback } from 'react';
import { incidentsApi, type IncidentFilters } from '../services/incidentsApi';
import type { Incident, IncidentListResponse } from '../types/incident';

const POLL_INTERVAL = Number(import.meta.env.VITE_POLL_INTERVAL_MS) || 10000;

export function useIncidents(filters: IncidentFilters = {}) {
  const [data, setData] = useState<IncidentListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const filtersKey = JSON.stringify(filters);

  const fetch = useCallback(async () => {
    try {
      const result = await incidentsApi.list(filters);
      setData(result);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load incidents');
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtersKey]);

  useEffect(() => {
    fetch();
    const interval = setInterval(fetch, POLL_INTERVAL);
    return () => clearInterval(interval);
  }, [fetch]);

  return { data, loading, error, refresh: fetch };
}

export function useIncidentDetail(incidentId: string | null) {
  const [incident, setIncident] = useState<Incident | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);

  const fetch = useCallback(async () => {
    if (!incidentId) return;
    setLoading(true);
    try {
      const data = await incidentsApi.getById(incidentId);
      setIncident(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load incident');
    } finally {
      setLoading(false);
    }
  }, [incidentId]);

  useEffect(() => {
    fetch();
  }, [fetch]);

  const triggerAnalysis = async () => {
    if (!incidentId) return;
    setAnalyzing(true);
    try {
      const updated = await incidentsApi.analyze(incidentId);
      setIncident(updated);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed');
    } finally {
      setAnalyzing(false);
    }
  };

  return { incident, loading, error, analyzing, refresh: fetch, triggerAnalysis };
}
