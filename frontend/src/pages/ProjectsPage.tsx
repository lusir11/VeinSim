/**
 * Projects list page — CRUD for cold-plate design projects.
 */
import React, { useEffect, useState } from 'react';
import {
  Typography, Button, Table, Tag, Upload, Modal, Form,
  Input, Space, message, Popconfirm,
} from 'antd';
import {
  PlusOutlined, UploadOutlined, DeleteOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { projectApi } from '../api/client';

const { Title } = Typography;

interface Project {
  id: string;
  name: string;
  description: string | null;
  status: string;
  manufacturing_process: string | null;
  geometry_format: string | null;
  created_at: string;
  updated_at: string;
}

const statusColors: Record<string, string> = {
  draft: 'default',
  designing: 'blue',
  optimizing: 'orange',
  completed: 'green',
  archived: 'gray',
};

const ProjectsPage: React.FC = () => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm();

  const [page, setPage] = useState(1);
  const pageSize = 20;

  const fetchProjects = async (p = page) => {
    setLoading(true);
    try {
      const res = await projectApi.list((p - 1) * pageSize, pageSize);
      setProjects(res.data.items);
      setTotal(res.data.total);
    } catch {
      message.error('Failed to load projects');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchProjects(); }, [page]);

  const handleCreate = async (values: { name: string; description?: string }) => {
    try {
      await projectApi.create(values);
      message.success('Project created');
      setModalOpen(false);
      form.resetFields();
      fetchProjects();
    } catch {
      message.error('Failed to create project');
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await projectApi.delete(id);
      message.success('Project deleted');
      fetchProjects();
    } catch {
      message.error('Failed to delete project');
    }
  };

  const columns: ColumnsType<Project> = [
    { title: 'Name', dataIndex: 'name', key: 'name', width: 200 },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (s: string) => <Tag color={statusColors[s] || 'default'}>{s}</Tag>,
    },
    {
      title: 'Manufacturing',
      dataIndex: 'manufacturing_process',
      key: 'mfg',
      render: (v: string | null) => v ? <Tag>{v}</Tag> : '—',
    },
    {
      title: 'Geometry',
      dataIndex: 'geometry_format',
      key: 'geo',
      render: (v: string | null) => v ? <Tag color="blue">{v.toUpperCase()}</Tag> : '—',
    },
    {
      title: 'Updated',
      dataIndex: 'updated_at',
      key: 'updated',
      render: (v: string) => new Date(v).toLocaleDateString(),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Upload
            showUploadList={false}
            maxCount={1}
            accept=".stl,.step,.stp,.iges,.igs"
            customRequest={async ({ file }) => {
              try {
                await projectApi.uploadGeometry(record.id, file as File);
                message.success('Geometry uploaded');
                fetchProjects();
              } catch {
                message.error('Upload failed');
              }
            }}
          >
            <Button size="small" icon={<UploadOutlined />}>Upload</Button>
          </Upload>
          <Popconfirm title="Delete this project?" onConfirm={() => handleDelete(record.id)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={3} style={{ margin: 0 }}>Projects</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
          New Project
        </Button>
      </div>

      <Table
        dataSource={projects}
        columns={columns}
        rowKey="id"
        loading={loading}
        pagination={{
          current: page,
          total,
          pageSize,
          onChange: (p) => { setPage(p); fetchProjects(p); },
        }}
      />

      <Modal
        title="Create Project"
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={() => form.submit()}
      >
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Form.Item name="name" label="Project Name" rules={[{ required: true }]}>
            <Input placeholder="e.g. EV Battery Cold Plate v2" />
          </Form.Item>
          <Form.Item name="description" label="Description">
            <Input.TextArea rows={3} placeholder="Optional description..." />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ProjectsPage;
