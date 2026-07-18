/**
 * React hook for WebSocket connection to simulation progress.
 */
import { useEffect, useRef, useState, useCallback } from 'react';

const WS_BASE = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000/api/v1/ws';

export interface ProgressEvent {
  type: 'status' | 'progress' | 'result' | 'error' | 'pong';
  simulation_id?: string;
  status?: string;
  iteration?: number;
  residual?: number;
  metrics?: Record<string, number | null>;
  message?: string;
  timestamp?: number;
  [key: string]: unknown;
}

export function useSimulationWs(simulationId: string | null) {
  const [events, setEvents] = useState<ProgressEvent[]>([]);
  const [latestStatus, setLatestStatus] = useState<string>('idle');
  const [latestIteration, setLatestIteration] = useState<number>(0);
  const [latestResidual, setLatestResidual] = useState<number | null>(null);
  const [latestMetrics, setLatestMetrics] = useState<Record<string, number | null> | null>(null);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const pingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const reset = useCallback(() => {
    setEvents([]);
    setLatestStatus('idle');
    setLatestIteration(0);
    setLatestResidual(null);
    setLatestMetrics(null);
  }, []);

  useEffect(() => {
    if (!simulationId) return;
    reset();

    const url = `${WS_BASE}/simulations/${simulationId}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      // Heartbeat every 30s
      pingRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) ws.send('ping');
      }, 30_000);
    };

    ws.onmessage = (event) => {
      try {
        const data: ProgressEvent = JSON.parse(event.data);
        setEvents((prev) => [...prev, data]);

        switch (data.type) {
          case 'status':
            if (data.status) setLatestStatus(data.status);
            break;
          case 'progress':
            if (data.iteration != null) setLatestIteration(data.iteration);
            if (data.residual != null) setLatestResidual(data.residual);
            break;
          case 'result':
            if (data.metrics) setLatestMetrics(data.metrics);
            break;
        }
      } catch {
        // ignore parse errors
      }
    };

    ws.onclose = () => {
      setConnected(false);
      if (pingRef.current) clearInterval(pingRef.current);
    };

    ws.onerror = () => {
      setConnected(false);
    };

    return () => {
      ws.close();
      if (pingRef.current) clearInterval(pingRef.current);
    };
  }, [simulationId, reset]);

  return {
    events,
    latestStatus,
    latestIteration,
    latestResidual,
    latestMetrics,
    connected,
  };
}
