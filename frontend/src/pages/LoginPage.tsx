/**
 * Login / Register page.
 */
import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Form, Input, Button, Tabs, Typography, Alert, Space } from 'antd';
import { UserOutlined, LockOutlined, MailOutlined } from '@ant-design/icons';
import { useAuthStore } from '../stores/authStore';

const { Title, Text } = Typography;

const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const { login, register, isLoading, error } = useAuthStore();
  const [loginForm] = Form.useForm();
  const [registerForm] = Form.useForm();

  const handleLogin = async (values: { email: string; password: string }) => {
    await login(values.email, values.password);
    if (!error) navigate('/');
  };

  const handleRegister = async (values: {
    email: string;
    username: string;
    password: string;
  }) => {
    await register(values.email, values.username, values.password);
    if (!error) navigate('/');
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #1a237e 0%, #0d47a1 50%, #01579b 100%)',
      }}
    >
      <Card style={{ width: 420, borderRadius: 12, boxShadow: '0 8px 32px rgba(0,0,0,0.2)' }}>
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <div style={{ textAlign: 'center' }}>
            <Title level={2} style={{ margin: 0 }}>
              ToffeeX
            </Title>
            <Text type="secondary">Generative Thermal Design Platform</Text>
          </div>

          {error && <Alert message={error} type="error" showIcon closable />}

          <Tabs
            centered
            items={[
              {
                key: 'login',
                label: 'Login',
                children: (
                  <Form form={loginForm} onFinish={handleLogin} layout="vertical">
                    <Form.Item name="email" rules={[{ required: true, type: 'email' }]}>
                      <Input prefix={<MailOutlined />} placeholder="Email" size="large" />
                    </Form.Item>
                    <Form.Item name="password" rules={[{ required: true }]}>
                      <Input.Password prefix={<LockOutlined />} placeholder="Password" size="large" />
                    </Form.Item>
                    <Button type="primary" htmlType="submit" block size="large" loading={isLoading}>
                      Sign In
                    </Button>
                  </Form>
                ),
              },
              {
                key: 'register',
                label: 'Register',
                children: (
                  <Form form={registerForm} onFinish={handleRegister} layout="vertical">
                    <Form.Item name="email" rules={[{ required: true, type: 'email' }]}>
                      <Input prefix={<MailOutlined />} placeholder="Email" size="large" />
                    </Form.Item>
                    <Form.Item name="username" rules={[{ required: true }]}>
                      <Input prefix={<UserOutlined />} placeholder="Username" size="large" />
                    </Form.Item>
                    <Form.Item name="password" rules={[{ required: true, min: 6 }]}>
                      <Input.Password prefix={<LockOutlined />} placeholder="Password" size="large" />
                    </Form.Item>
                    <Button type="primary" htmlType="submit" block size="large" loading={isLoading}>
                      Create Account
                    </Button>
                  </Form>
                ),
              },
            ]}
          />
        </Space>
      </Card>
    </div>
  );
};

export default LoginPage;
