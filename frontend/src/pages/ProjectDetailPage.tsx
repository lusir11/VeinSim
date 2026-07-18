/**
 * Project Detail page — constraint editing, heat source setup, simulation launch.
 */
import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Typography, Card, Form, Input, InputNumber, Select, Button,
  Row, Col, Space, Tag, Upload, message, Descriptions,
  Slider,
} from 'antd';
import {
  SaveOutlined, PlayCircleOutlined, UploadOutlined, ArrowLeftOutlined,
  PlusOutlined, DeleteOutlined,
} from '@ant-design/icons';
import { projectApi, simulationApi } from '../api/client';
import ModelViewer from '../components/three/ModelViewer';

const { Text } = Typography;

interface HeatSource {
  x: number;
  y: number;
  z: number;
  power_watts: number;
}

interface ProjectData {
  id: string;
  name: string;
  description: string | null;
  status: string;
  geometry_file_key: string | null;
  geometry_format: string | null;
  manufacturing_process: string | null;
  constraints: Record<string, unknown> | null;
  created_at: string;
}

const ProjectDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [project, setProject] = useState<ProjectData | null>(null);
  const [form] = Form.useForm();
  const [heatSources, setHeatSources] = useState<HeatSource[]>([]);
  const [launching, setLaunching] = useState(false);

  // Load project
  useEffect(() => {
    if (!id) return;
    projectApi.get(id)
      .then((res) => {
        const p = res.data;
        setProject(p);
        form.setFieldsValue({
          name: p.name,
          description: p.description,
          manufacturing_process: p.manufacturing_process,
          max_temperature_k: (p.constraints as Record<string, unknown>)?.max_temperature_k as number,
          max_pressure_drop_pa: (p.constraints as Record<string, unknown>)?.max_pressure_drop_pa as number,
          inlet_velocity_m_s: (p.constraints as Record<string, unknown>)?.inlet_velocity_m_s as number,
          fluid_type: ((p.constraints as Record<string, unknown>)?.fluid_type as string) || 'water',
          min_feature_size_mm: (p.constraints as Record<string, unknown>)?.min_feature_size_mm as number,
          overhang_angle_deg: (p.constraints as Record<string, unknown>)?.overhang_angle_deg as number,
        });
        const hs = ((p.constraints as Record<string, unknown>)?.heat_sources as HeatSource[]) || [];
        setHeatSources(hs);
      })
      .catch(() => message.error('Failed to load project'));
  }, [id]);

  const handleSave = async () => {
    if (!id) return;
    const values = form.getFieldsValue();
    const constraints: Record<string, unknown> = {
      max_temperature_k: values.max_temperature_k,
      max_pressure_drop_pa: values.max_pressure_drop_pa,
      inlet_velocity_m_s: values.inlet_velocity_m_s,
      fluid_type: values.fluid_type,
      min_feature_size_mm: values.min_feature_size_mm,
      overhang_angle_deg: values.overhang_angle_deg,
      heat_sources: heatSources,
    };
    try {
      await projectApi.update(id, {
        name: values.name,
        description: values.description,
        manufacturing_process: values.manufacturing_process,
        constraints,
      });
      message.success('Project saved');
    } catch {
      message.error('Save failed');
    }
  };

  const handleLaunchSimulation = async () => {
    if (!id) return;
    setLaunching(true);
    try {
      await simulationApi.create({
        project_id: id,
        solver_type: 'adjointShapeOptimizationFoam',
        run_params: {
          inlet_velocity: [form.getFieldValue('inlet_velocity_m_s') || 0.1, 0, 0],
          max_iterations: 500,
          convergence_tolerance: 1e-5,
        },
      });
      message.success('Simulation launched!');
      navigate('/simulations');
    } catch {
      message.error('Launch failed');
    } finally {
      setLaunching(false);
    }
  };

  const addHeatSource = () => {
    setHeatSources([...heatSources, { x: 0, y: 0, z: 0, power_watts: 10 }]);
  };

  const updateHeatSource = (idx: number, field: keyof HeatSource, value: number) => {
    const updated = [...heatSources];
    updated[idx] = { ...updated[idx], [field]: value };
    setHeatSources(updated);
  };

  const removeHeatSource = (idx: number) => {
    setHeatSources(heatSources.filter((_, i) => i !== idx));
  };

  if (!project) return <div style={{ padding: 24 }}>Loading...</div>;

  return (
    <div>
      <Button type="text" icon={<ArrowLeftOutlined />} onClick={() => navigate('/projects')} style={{ marginBottom: 16 }}>
        Back to Projects
      </Button>

      <Row gutter={[24, 24]}>
        {/* Left column: 3D viewer + info */}
        <Col xs={24} lg={12}>
          <Card title="3D Preview" style={{ marginBottom: 16 }}>
            <ModelViewer showDemo height={350} />
            <Descriptions size="small" column={2} style={{ marginTop: 12 }}>
              <Descriptions.Item label="Status">
                <Tag color={project.status === 'completed' ? 'green' : 'blue'}>{project.status}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Geometry">
                {project.geometry_format
                  ? <Tag color="blue">{project.geometry_format.toUpperCase()}</Tag>
                  : <Text type="secondary">No geometry uploaded</Text>}
              </Descriptions.Item>
            </Descriptions>
            {project.geometry_file_key && (
              <Upload
                showUploadList={false}
                maxCount={1}
                accept=".stl,.step,.stp"
                customRequest={async ({ file }) => {
                  try {
                    await projectApi.uploadGeometry(project.id, file as File);
                    message.success('Geometry updated');
                  } catch { message.error('Upload failed'); }
                }}
              >
                <Button icon={<UploadOutlined />} style={{ marginTop: 8 }}>Replace Geometry</Button>
              </Upload>
            )}
          </Card>

          {/* Heat Sources */}
          <Card title="Heat Sources" extra={<Button size="small" icon={<PlusOutlined />} onClick={addHeatSource}>Add</Button>}>
            {heatSources.length === 0 ? (
              <Text type="secondary">No heat sources defined. Click Add to place one.</Text>
            ) : (
              heatSources.map((hs, idx) => (
                <Card key={idx} size="small" style={{ marginBottom: 8 }} extra={
                  <Button size="small" danger icon={<DeleteOutlined />} onClick={() => removeHeatSource(idx)} />
                }>
                  <Row gutter={8}>
                    <Col span={6}><Text type="secondary">X (m)</Text><InputNumber size="small" value={hs.x} onChange={(v) => updateHeatSource(idx, 'x', v || 0)} step={0.001} style={{ width: '100%' }} /></Col>
                    <Col span={6}><Text type="secondary">Y (m)</Text><InputNumber size="small" value={hs.y} onChange={(v) => updateHeatSource(idx, 'y', v || 0)} step={0.001} style={{ width: '100%' }} /></Col>
                    <Col span={6}><Text type="secondary">Z (m)</Text><InputNumber size="small" value={hs.z} onChange={(v) => updateHeatSource(idx, 'z', v || 0)} step={0.001} style={{ width: '100%' }} /></Col>
                    <Col span={6}><Text type="secondary">Power (W)</Text><InputNumber size="small" value={hs.power_watts} onChange={(v) => updateHeatSource(idx, 'power_watts', v || 0)} step={1} style={{ width: '100%' }} /></Col>
                  </Row>
                </Card>
              ))
            )}
          </Card>
        </Col>

        {/* Right column: Configuration */}
        <Col xs={24} lg={12}>
          <Form form={form} layout="vertical">
            <Card title="Project Settings" style={{ marginBottom: 16 }}>
              <Form.Item name="name" label="Name" rules={[{ required: true }]}>
                <Input />
              </Form.Item>
              <Form.Item name="description" label="Description">
                <Input.TextArea rows={2} />
              </Form.Item>
              <Form.Item name="manufacturing_process" label="Manufacturing Process">
                <Select placeholder="Select process">
                  <Select.Option value="stamping">Stamping (2.5D)</Select.Option>
                  <Select.Option value="cnc">CNC Machining</Select.Option>
                  <Select.Option value="chemical_etching">Chemical Etching</Select.Option>
                  <Select.Option value="3d_print">3D Printing (Additive)</Select.Option>
                </Select>
              </Form.Item>
            </Card>

            <Card title="Thermal Constraints" style={{ marginBottom: 16 }}>
              <Form.Item name="fluid_type" label="Coolant Fluid" initialValue="water">
                <Select>
                  <Select.Option value="water">Water</Select.Option>
                  <Select.Option value="ethylene_glycol">Ethylene Glycol 50%</Select.Option>
                  <Select.Option value="engine_oil">Engine Oil</Select.Option>
                  <Select.Option value="air">Air</Select.Option>
                </Select>
              </Form.Item>
              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item name="max_temperature_k" label="Max Temp (K)">
                    <InputNumber min={250} max={500} step={1} style={{ width: '100%' }} placeholder="353" />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item name="max_pressure_drop_pa" label="Max Pressure Drop (Pa)">
                    <InputNumber min={0} max={100000} step={100} style={{ width: '100%' }} placeholder="5000" />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item name="inlet_velocity_m_s" label="Inlet Velocity (m/s)">
                    <InputNumber min={0.001} max={10} step={0.01} style={{ width: '100%' }} placeholder="0.1" />
                  </Form.Item>
                </Col>
              </Row>
            </Card>

            <Card title="Manufacturing Constraints" style={{ marginBottom: 16 }}>
              <Form.Item name="min_feature_size_mm" label="Min Feature Size (mm)">
                <InputNumber min={0.01} max={50} step={0.1} style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item name="overhang_angle_deg" label="Max Overhang Angle (deg) — for 3D Print">
                <Slider min={0} max={90} marks={{ 0: '0°', 45: '45°', 90: '90°' }} />
              </Form.Item>
            </Card>

            <Space>
              <Button type="primary" icon={<SaveOutlined />} onClick={handleSave}>Save</Button>
              <Button type="primary" danger icon={<PlayCircleOutlined />} loading={launching} onClick={handleLaunchSimulation}>
                Launch Optimization
              </Button>
            </Space>
          </Form>
        </Col>
      </Row>
    </div>
  );
};

export default ProjectDetailPage;
