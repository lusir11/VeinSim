/**
 * Three.js 3D viewer for geometry and simulation results.
 * Uses @react-three/fiber and @react-three/drei.
 */
import React, { Suspense, useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Grid, Environment, Html } from '@react-three/drei';
import * as THREE from 'three';

// ── Rotating placeholder geometry ────────────────────────────────────────────

const RotatingBox: React.FC<{ position?: [number, number, number] }> = ({
  position = [0, 0, 0],
}) => {
  const meshRef = useRef<THREE.Mesh>(null!);

  useFrame((_, delta) => {
    meshRef.current.rotation.y += delta * 0.3;
  });

  return (
    <mesh ref={meshRef} position={position}>
      <boxGeometry args={[0.1, 0.05, 0.005]} />
      <meshStandardMaterial color="#4fc3f7" metalness={0.3} roughness={0.4} />
    </mesh>
  );
};

// ── Cold-plate wireframe placeholder ─────────────────────────────────────────

const ColdPlateWireframe: React.FC = () => {
  return (
    <group>
      {/* Main plate body */}
      <mesh position={[0, 0, 0]}>
        <boxGeometry args={[0.1, 0.05, 0.005]} />
        <meshStandardMaterial
          color="#1565c0"
          wireframe
          transparent
          opacity={0.6}
        />
      </mesh>
      {/* Inlet marker */}
      <mesh position={[-0.055, 0, 0]}>
        <cylinderGeometry args={[0.003, 0.003, 0.05, 8]} />
        <meshStandardMaterial color="#4caf50" />
      </mesh>
      {/* Outlet marker */}
      <mesh position={[0.055, 0, 0]}>
        <cylinderGeometry args={[0.003, 0.003, 0.05, 8]} />
        <meshStandardMaterial color="#f44336" />
      </mesh>
    </group>
  );
};

// ── Main Viewer Component ────────────────────────────────────────────────────

interface ModelViewerProps {
  /** Optional STL/OBJ mesh data (base64 or URL) — not yet implemented */
  meshData?: string | null;
  /** Show placeholder demo geometry */
  showDemo?: boolean;
  height?: number | string;
}

const ModelViewer: React.FC<ModelViewerProps> = ({
  meshData,
  showDemo = true,
  height = 500,
}) => {
  return (
    <div style={{ width: '100%', height, border: '1px solid #e0e0e0', borderRadius: 8, overflow: 'hidden' }}>
      <Canvas
        camera={{ position: [0.15, 0.1, 0.1], fov: 45 }}
        style={{ background: '#fafafa' }}
      >
        <Suspense fallback={
          <Html center>
            <div>Loading 3D scene...</div>
          </Html>
        }>
          {/* Lighting */}
          <ambientLight intensity={0.4} />
          <directionalLight position={[5, 5, 5]} intensity={1} />
          <directionalLight position={[-3, -3, 2]} intensity={0.3} />

          {/* Scene content */}
          {showDemo && !meshData && (
            <>
              <ColdPlateWireframe />
              <RotatingBox position={[0, 0, 0.01]} />
            </>
          )}

          {/* Ground grid */}
          <Grid
            args={[0.5, 0.5]}
            cellSize={0.01}
            cellColor="#ccc"
            sectionSize={0.05}
            sectionColor="#999"
            fadeDistance={0.5}
            position={[0, -0.03, 0]}
          />

          {/* Camera controls */}
          <OrbitControls
            makeDefault
            enableDamping
            dampingFactor={0.1}
            minDistance={0.02}
            maxDistance={1}
          />

          {/* Environment map for reflections */}
          <Environment preset="city" />
        </Suspense>
      </Canvas>
    </div>
  );
};

export default ModelViewer;
