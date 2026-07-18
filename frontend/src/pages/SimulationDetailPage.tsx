/**
 * Simulation Detail page — live progress monitoring via WebSocket.
 */
import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Typography, Card, Descriptions, Tag, Progress, Button,
  Row, Col, Steps, Alert,
} from 'antd';
import {
  ArrowLeftOutlined, CheckCircleOutlined, LoadingOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import { simulationApi } from '../api/client';
import { useSimulationWs } from '../hooks/useSimulationWs';

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
                  percent={Math.min(100, (ws.latestIteration / 500) * 100)}
                  status="active"
                  format={() => `Iteration ${ws.latestIteration}`}
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
            ) : (
              <Text type="secondary">No results available yet</Text>
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default SimulationDetailPage;
