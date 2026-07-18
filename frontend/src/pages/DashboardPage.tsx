/**
 * Dashboard page — overview of projects and recent simulations.
 */
import React from 'react';
import { Row, Col, Card, Statistic, Typography } from 'antd';
import {
  ProjectOutlined,
  ThunderboltOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import ModelViewer from '../components/three/ModelViewer';

const { Title, Paragraph } = Typography;

const DashboardPage: React.FC = () => {
  return (
    <div>
      <Title level={3}>Dashboard</Title>
      <Paragraph type="secondary">
        Cloud-native generative design platform for thermal-fluid components.
        Physics-driven topology optimization for cold plates, heat exchangers, and manifolds.
      </Paragraph>

      {/* Statistics */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic title="Projects" value={0} prefix={<ProjectOutlined />} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic title="Simulations" value={0} prefix={<ThunderboltOutlined />} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic title="Converged" value={0} prefix={<CheckCircleOutlined />} valueStyle={{ color: '#3f8600' }} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic title="Running" value={0} prefix={<ClockCircleOutlined />} valueStyle={{ color: '#cf1322' }} />
          </Card>
        </Col>
      </Row>

      {/* 3D Viewer Demo */}
      <Card title="3D Cold-Plate Viewer (Demo)" style={{ marginBottom: 24 }}>
        <Paragraph type="secondary">
          Interactive 3D preview of the cold-plate design domain. In production, this displays
          the imported geometry and optimization results with temperature/velocity field overlays.
        </Paragraph>
        <ModelViewer showDemo height={400} />
      </Card>

      {/* Quick Start */}
      <Card title="Quick Start Guide">
        <ol>
          <li>Create a new <strong>Project</strong> and upload your cold-plate geometry (STL/STEP)</li>
          <li>Define <strong>heat sources</strong>, <strong>boundary conditions</strong>, and <strong>manufacturing constraints</strong></li>
          <li>Launch a <strong>Simulation</strong> — the topology optimizer will automatically generate flow channels</li>
          <li>Review <strong>results</strong>: temperature field, pressure drop, optimized geometry</li>
          <li>Export the optimized design for <strong>3D printing</strong> or <strong>CNC machining</strong></li>
        </ol>
      </Card>
    </div>
  );
};

export default DashboardPage;
