/**
 * App layout with sidebar navigation + top bar.
 */
import React from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, Button, Typography, Space } from 'antd';
import {
  HomeOutlined,
  ProjectOutlined,
  ThunderboltOutlined,
  LogoutOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { useAuthStore } from '../../stores/authStore';

const { Header, Sider, Content } = Layout;
const { Text } = Typography;

const menuItems = [
  { key: '/', icon: <HomeOutlined />, label: 'Dashboard' },
  { key: '/projects', icon: <ProjectOutlined />, label: 'Projects' },
  { key: '/simulations', icon: <ThunderboltOutlined />, label: 'Simulations' },
];

const AppLayout: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuthStore();

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider theme="dark" width={220} breakpoint="lg" collapsedWidth={60}>
        <div
          style={{
            padding: '16px',
            textAlign: 'center',
            borderBottom: '1px solid rgba(255,255,255,0.1)',
          }}
        >
          <Typography.Title level={4} style={{ color: '#fff', margin: 0 }}>
            ToffeeX
          </Typography.Title>
          <Text style={{ color: 'rgba(255,255,255,0.5)', fontSize: 11 }}>
            Generative Thermal Design
          </Text>
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          style={{ marginTop: 8 }}
        />
      </Sider>

      <Layout>
        <Header
          style={{
            background: '#fff',
            padding: '0 24px',
            display: 'flex',
            justifyContent: 'flex-end',
            alignItems: 'center',
            borderBottom: '1px solid #f0f0f0',
          }}
        >
          <Space>
            <UserOutlined />
            <Text>{user?.username || 'Guest'}</Text>
            <Button type="text" icon={<LogoutOutlined />} onClick={logout} />
          </Space>
        </Header>

        <Content style={{ margin: 24, padding: 24, background: '#fff', borderRadius: 8 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
};

export default AppLayout;
