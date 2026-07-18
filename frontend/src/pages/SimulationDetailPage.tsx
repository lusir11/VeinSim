/**
 * Simulation Detail page — live progress monitoring via WebSocket,
 * convergence chart, and 3D STL viewer for optimized geometry.
 */
import React, { useEffect, useState, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Typography, Card, Descriptions, Tag, Progress, Button,
  Row, Col, Steps, Alert, Space,
} from 'antd';
import {
  ArrowLeftOutlined, CheckCircleOutlined, LoadingOutlined,
  ClockCircleOutlined, DownloadOutlined,
} from '@ant-design/icons';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { simulationApi } from '../api/client';
import { useSimulationWs } from '../hooks/useSimulationWs';
import STLViewer from '../components/three/STLViewer';

const { Text } = Typography;

const statusSteps = ['queued', 'meshing', 'running', 'converged'];
const statusColors: Record<string, string> = {
  queued: 'default', meshing: 'blue', running: 'processing',
  converged: 'green', failed: 'red', cancelled: 'gray',
};

const SimulationDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [simulation, setSimulation] = useState<Record<string, unknown> | null>(null);
  const [stlUrl, setStlUrl] = useState<string | null>(null);
  const ws = useSimulationWs(id || null);

  // Load simulation data
  useEffect(() => {
    if (!id) return;
    simulationApi.get(id)
      .then((res) => setSimulation(res.data))
      .catch(() => {/* ignore */});
  }, [id]);

  // Poll for status updates (backup if WS fails)
  useEffect(() => {
    if (!id) return;
    const interval = setInterval(() => {
      simulationApi.get(id).then((res) => setSimulation(res.data)).catch(() => {});
    }, 15_000);
    return () => clearInterval(interval);
  }, [id]);

  // Use WS status if available, otherwise use polled status
  const currentStatus = ws.latestStatus !== 'idle' ? ws.latestStatus : (simulation?.status as string) || 'queued';
  const isRunning = currentStatus === 'running' || currentStatus === 'meshing';
  const currentStep = Math.max(0, statusSteps.indexOf(currentStatus));

  // Fetch STL URL when converged
  useEffect(() => {
    if (currentStatus === 'converged' && id && !stlUrl) {
      simulationApi.getStlUrl(id)
        .then((res) => setStlUrl(res.data.url))
        .catch(() => {/* no STL available */});
    }
  }, [currentStatus, id, stlUrl]);

  // Derive max_iterations from run_params for dynamic progress bar
  const maxIterations = useMemo(() => {
    const rp = simulation?.run_params as Record<string, unknown> | null;
    return (rp?.max_iterations as number) || 500;
  }, [simulation]);

  // Build convergence chart data from WS events + DB residual_history
  const wsResidualData = useMemo(() => {
    return ws.events
      .filter((e) => e.type === 'progress' && e.iteration != null && e.residual != null)
      .map((e) => ({ iteration: e.iteration as number, residual: e.residual as number }));
  }, [ws.events]);

  const dbResidualData = useMemo(() => {
    const history = simulation?.residual_history as number[] | null;
    if (!history || !Array.isArray(history) || history.length === 0) return [];
    return history.map((r, i) => ({ iteration: i, residual: r }));
  }, [simulation]);

  const chartData = dbResidualData.length > 0 ? dbResidualData : wsResidualData;

  return (
    <div>
      <Button type="text" icon={<ArrowLeftOutlined />} onClick={() => navigate('/simulations')} style={{ marginBottom: 16 }}>
        Back to Simulations
      </Button>

      <Row gutter={[24, 24]}>
        {/* Left: Status and Progress */}
        <Col xs={24} lg={14}>
          <Card title="Simulation Progress">
            <div style={{ marginBottom: 16, display: 'flex', alignItems: 'center', gap: 12 }}>
              <Tag color={statusColors[currentStatus] || 'default'} style={{ fontSize: 16, padding: '4px 16px' }}>
                {currentStatus.toUpperCase()}
              </Tag>
              {ws.connected && <Tag color="green">WebSocket Connected</Tag>}
              {!ws.connected && id && <Tag color="red">WebSocket Disconnected</Tag>}
            </div>

            {/* Step indicator */}
            <Steps
              current={currentStep}
              status={currentStatus === 'failed' ? 'error' : undefined}
              items={[
                { title: 'Queued', icon: <ClockCircleOutlined /> },
                { title: 'Meshing', icon: <LoadingOutlined /> },
                { title: 'Solving', icon: <LoadingOutlined /> },
                { title: 'Converged', icon: <CheckCircleOutlined /> },
              ]}
              style={{ marginBottom: 24 }}
            />

            {/* Iteration progress */}
            {isRunning && (
              <>
                <Progress
                  percent={Math.min(100, (ws.latestIteration / maxIterations) * 100)}
                  status="active"
                  format={() => `Iteration ${ws.latestIteration} / ${maxIterations}`}
                  style={{ marginBottom: 12 }}
                />
                {ws.latestResidual !== null && (
                  <Text type="secondary">
                    Residual: {ws.latestResidual.toExponential(3)}
                  </Text>
                )}
              </>
            )}

            {currentStatus === 'failed' && (
              <Alert type="error" message="Simulation Failed" description={
                ws.events.find((e) => e.type === 'status' && e.status === 'failed')?.message || 'Check solver logs for details'
              } style={{ marginTop: 12 }} />
            )}

            {currentStatus === 'converged' && ws.latestMetrics && (
              <Alert type="success" message="Optimization Converged!" description={
                <pre style={{ margin: 0, fontSize: 12 }}>
                  {JSON.stringify(ws.latestMetrics, null, 2)}
                </pre>
              } />
            )}
          </Card>

          {/* Convergence Chart */}
          {chartData.length > 0 && (
            <Card title="Convergence History" style={{ marginTop: 16 }}>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    dataKey="iteration"
                    label={{ value: 'Iteration', position: 'insideBottom', offset: -5 }}
                  />
                  <YAxis
                    scale="log"
                    domain={['auto', 'auto']}
                    label={{ value: 'Residual', angle: -90, position: 'insideLeft' }}
                    tickFormatter={(v: number) => v.toExponential(1)}
                  />
                  <Tooltip
                    formatter={(value: number) => [value.toExponential(4), 'Residual']}
                    labelFormatter={(label: number) => `Iteration ${label}`}
                  />
                  <Line
                    type="monotone"
                    dataKey="residual"
                    stroke="#1565c0"
                    dot={false}
                    strokeWidth={2}
                  />
                </LineChart>
              </ResponsiveContainer>
            </Card>
          )}
        </Col>

        {/* Right: Simulation parameters and results */}
        <Col xs={24} lg={10}>
          <Card title="Parameters" style={{ marginBottom: 16 }}>
            {simulation && (
              <Descriptions column={1} size="small">
                <Descriptions.Item label="ID">{(simulation.id as string)?.slice(0, 12)}...</Descriptions.Item>
                <Descriptions.Item label="Project">{(simulation.project_id as string)?.slice(0, 12)}...</Descriptions.Item>
                <Descriptions.Item label="Solver">{simulation.solver_type as string}</Descriptions.Item>
                <Descriptions.Item label="Mesh Cells">
                  {(simulation.mesh_cell_count as number)?.toLocaleString() || '—'}
                </Descriptions.Item>
                <Descriptions.Item label="Iterations">
                  {(simulation.iterations_completed as number) ?? '—'}
                </Descriptions.Item>
                <Descriptions.Item label="Final Residual">
                  {simulation.final_residual ? (simulation.final_residual as number).toExponential(3) : '—'}
                </Descriptions.Item>
                <Descriptions.Item label="Wall Time">
                  {simulation.wall_time_seconds ? `${((simulation.wall_time_seconds as number) / 60).toFixed(1)} min` : '—'}
                </Descriptions.Item>
              </Descriptions>
            )}
          </Card>

          <Card title="Performance Metrics">
            {ws.latestMetrics ? (
              <Descriptions column={1} size="small">
                {Object.entries(ws.latestMetrics).map(([key, value]) => (
                  <Descriptions.Item key={key} label={key.replace(/_/g, ' ')}>
                    {value != null ? (typeof value === 'number' ? value.toFixed(4) : String(value)) : '—'}
                  </Descriptions.Item>
                ))}
              </Descriptions>
            ) : simulation?.status === 'converged' ? (
              <Text type="secondary">Loading metrics...</Text>
            ) : (
              <Text type="secondary">No results available yet</Text>
            )}
          </Card>
        </Col>
      </Row>

      {/* Optimized Geometry 3D Viewer */}
      {currentStatus === 'converged' && stlUrl && (
        <Card
          title="Optimized Geometry"
          extra={
            <Space>
              <Button
                type="primary"
                icon={<DownloadOutlined />}
                href={stlUrl}
                target="_blank"
              >
                Download STL
              </Button>
            </Space>
          }
          style={{ marginTop: 16 }}
        >
          <STLViewer stlUrl={stlUrl} height={500} color="#1565c0" showGrid />
        </Card>
      )}
    </div>
  );
};

export default SimulationDetailPage;
