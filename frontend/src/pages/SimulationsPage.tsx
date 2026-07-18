/**
 * Simulations page — list, create, and monitor topology optimization runs.
 */
import React, { useEffect, useState } from 'react';
import {
  Typography, Button, Table, Tag, Modal, Form,
  InputNumber, Select, message, Descriptions,
} from 'antd';
import { PlayCircleOutlined, StopOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { simulationApi, projectApi } from '../api/client';

const { Title } = Typography;

interface Simulation {
  id: string;
  project_id: string;
  solver_type: string;
  status: string;
  mesh_cell_count: number | null;
  iterations_completed: number | null;
  final_residual: number | null;
  wall_time_seconds: number | null;
  created_at: string;
}

const statusColors: Record<string, string> = {
  queued: 'default',
  meshing: 'blue',
  running: 'processing',
  converged: 'green',
  failed: 'red',
  cancelled: 'gray',
};

const SimulationsPage: React.FC = () => {
  const [simulations, setSimulations] = useState<Simulation[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [projects, setProjects] = useState<{ id: string; name: string }[]>([]);
  const [form] = Form.useForm();

  const [page, setPage] = useState(1);
  const pageSize = 20;

  const fetchSimulations = async (p = page) => {
    setLoading(true);
    try {
      const res = await simulationApi.list(undefined, (p - 1) * pageSize, pageSize);
      setSimulations(res.data.items);
      setTotal(res.data.total);
    } catch {
      message.error('Failed to load simulations');
    } finally {
      setLoading(false);
    }
  };

  const fetchProjects = async () => {
    try {
      const res = await projectApi.list(0, 100);
      setProjects(res.data.items);
    } catch { /* ignore */ }
  };

  useEffect(() => {
    fetchSimulations();
    fetchProjects();
    // Poll every 10s for status updates
    const interval = setInterval(() => fetchSimulations(), 10_000);
    return () => clearInterval(interval);
  }, [page]);

  const handleCreate = async (values: {
    project_id: string;
    solver_type: string;
    inlet_velocity: number;
    max_iterations: number;
    convergence_tolerance: number;
  }) => {
    try {
      await simulationApi.create({
        project_id: values.project_id,
        solver_type: values.solver_type,
        run_params: {
          inlet_velocity: [values.inlet_velocity || 0.1, 0, 0],
          max_iterations: values.max_iterations || 500,
          convergence_tolerance: values.convergence_tolerance || 1e-5,
        },
      });
      message.success('Simulation launched');
      setModalOpen(false);
      form.resetFields();
      fetchSimulations();
    } catch {
      message.error('Failed to launch simulation');
    }
  };

  const handleCancel = async (id: string) => {
    try {
      await simulationApi.cancel(id);
      message.info('Simulation cancelled');
      fetchSimulations();
    } catch {
      message.error('Failed to cancel');
    }
  };

  const columns: ColumnsType<Simulation> = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 100,
      render: (v: string) => v.slice(0, 8) + '...',
    },
    {
      title: 'Solver',
      dataIndex: 'solver_type',
      key: 'solver',
      render: (v: string) => <Tag>{v}</Tag>,
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (s: string) => <Tag color={statusColors[s]}>{s}</Tag>,
    },
    {
      title: 'Mesh Cells',
      dataIndex: 'mesh_cell_count',
      key: 'mesh',
      render: (v: number | null) => v?.toLocaleString() || '—',
    },
    {
      title: 'Iterations',
      dataIndex: 'iterations_completed',
      key: 'iters',
      render: (v: number | null) => v ?? '—',
    },
    {
      title: 'Residual',
      dataIndex: 'final_residual',
      key: 'residual',
      render: (v: number | null) => v ? v.toExponential(2) : '—',
    },
    {
      title: 'Wall Time',
      dataIndex: 'wall_time_seconds',
      key: 'time',
      render: (v: number | null) => v ? `${(v / 60).toFixed(1)} min` : '—',
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) =>
        record.status === 'running' || record.status === 'queued' ? (
          <Button
            size="small"
            danger
            icon={<StopOutlined />}
            onClick={() => handleCancel(record.id)}
          >
            Cancel
          </Button>
        ) : null,
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={3} style={{ margin: 0 }}>Simulations</Title>
        <Button
          type="primary"
          icon={<PlayCircleOutlined />}
          onClick={() => { setModalOpen(true); fetchProjects(); }}
        >
          New Simulation
        </Button>
      </div>

      <Table
        dataSource={simulations}
        columns={columns}
        rowKey="id"
        loading={loading}
        pagination={{
          current: page,
          total,
          pageSize,
          onChange: (p) => { setPage(p); fetchSimulations(p); },
        }}
        expandable={{
          expandedRowRender: (record) => (
            <Descriptions size="small" column={3} bordered>
              <Descriptions.Item label="Full ID">{record.id}</Descriptions.Item>
              <Descriptions.Item label="Project">{record.project_id}</Descriptions.Item>
              <Descriptions.Item label="Created">{new Date(record.created_at).toLocaleString()}</Descriptions.Item>
            </Descriptions>
          ),
        }}
      />

      <Modal
        title="Launch Topology Optimization"
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={() => form.submit()}
        width={520}
      >
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Form.Item name="project_id" label="Project" rules={[{ required: true }]}>
            <Select placeholder="Select a project">
              {projects.map((p) => (
                <Select.Option key={p.id} value={p.id}>{p.name}</Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="solver_type" label="Solver" initialValue="adjointShapeOptimizationFoam">
            <Select>
              <Select.Option value="adjointShapeOptimizationFoam">Adjoint Shape Optimization</Select.Option>
              <Select.Option value="chtMultiRegionFoam">Conjugate Heat Transfer</Select.Option>
              <Select.Option value="buoyantSimpleFoam">Buoyant Simple</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="inlet_velocity" label="Inlet Velocity (m/s)" initialValue={0.1}>
            <InputNumber min={0.001} max={10} step={0.01} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="max_iterations" label="Max Iterations" initialValue={500}>
            <InputNumber min={10} max={10000} step={100} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="convergence_tolerance" label="Convergence Tolerance" initialValue={1e-5}>
            <InputNumber min={1e-8} max={1e-2} step={1e-6} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default SimulationsPage;
