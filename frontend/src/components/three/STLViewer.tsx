/**
 * STL mesh loader and viewer component using Three.js + @react-three/fiber.
 * Supports loading binary/ASCII STL from URL or File.
 */
import React, { Suspense, useEffect, useRef, useState } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Grid, Environment, Html, Center } from '@react-three/drei';
import * as THREE from 'three';
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader.js';

// ── STL Mesh component ───────────────────────────────────────────────────────

interface STLMeshProps {
  data: ArrayBuffer | null;
  color?: string;
  wireframe?: boolean;
  opacity?: number;
}

const STLMesh: React.FC<STLMeshProps> = ({ data, color = '#4fc3f7', wireframe = false, opacity = 1.0 }) => {
  const meshRef = useRef<THREE.Mesh>(null!);
  const [geometry, setGeometry] = useState<THREE.BufferGeometry | null>(null);

  useEffect(() => {
    if (!data) return;
    const loader = new STLLoader();
    const geo = loader.parse(data);
    geo.computeVertexNormals();
    geo.center();
    setGeometry(geo);
  }, [data]);

  if (!geometry) return null;

  return (
    <Center>
      <mesh ref={meshRef} geometry={geometry} castShadow receiveShadow>
        <meshStandardMaterial
          color={color}
          wireframe={wireframe}
          transparent={opacity < 1}
          opacity={opacity}
          metalness={0.2}
          roughness={0.6}
          side={THREE.DoubleSide}
        />
      </mesh>
    </Center>
  );
};

// ── Temperature field overlay (placeholder) ──────────────────────────────────

interface TemperatureOverlayProps {
  /** VTK data URL — not yet implemented */
  vtuUrl?: string | null;
}

const TemperatureOverlay: React.FC<TemperatureOverlayProps> = () => {
  // TODO: Implement VTK.js VTU loading and temperature colormap overlay
  // For now this is a placeholder for future VTK.js integration
  return null;
};

// ── Main STL Viewer ──────────────────────────────────────────────────────────

interface STLViewerProps {
  /** STL file as ArrayBuffer */
  stlData?: ArrayBuffer | null;
  /** URL to fetch STL from */
  stlUrl?: string | null;
  /** Show wireframe overlay */
  wireframe?: boolean;
  /** STL color */
  color?: string;
  height?: number | string;
  /** Show grid */
  showGrid?: boolean;
}

const STLViewer: React.FC<STLViewerProps> = ({
  stlData,
  stlUrl,
  wireframe = false,
  color = '#1565c0',
  height = 500,
  showGrid = true,
}) => {
  const [data, setData] = useState<ArrayBuffer | null>(stlData || null);
  const [loading, setLoading] = useState(false);

  // Fetch STL from URL
  useEffect(() => {
    if (stlData) {
      setData(stlData);
      return;
    }
    if (!stlUrl) return;
    setLoading(true);
    fetch(stlUrl)
      .then((r) => r.arrayBuffer())
      .then((buf) => { setData(buf); setLoading(false); })
      .catch(() => setLoading(false));
  }, [stlData, stlUrl]);

  return (
    <div style={{ width: '100%', height, border: '1px solid #e0e0e0', borderRadius: 8, overflow: 'hidden', position: 'relative' }}>
      {loading && (
        <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%,-50%)', zIndex: 10 }}>
          Loading STL...
        </div>
      )}
      <Canvas camera={{ position: [0.15, 0.1, 0.1], fov: 45 }} style={{ background: '#fafafa' }}>
        <Suspense fallback={<Html center><div>Loading 3D...</div></Html>}>
          <ambientLight intensity={0.4} />
          <directionalLight position={[5, 5, 5]} intensity={1} castShadow />
          <directionalLight position={[-3, -3, 2]} intensity={0.3} />

          {data && (
            <>
              <STLMesh data={data} color={color} wireframe={wireframe} />
              {wireframe && <STLMesh data={data} color="#ffffff" wireframe opacity={0.3} />}
            </>
          )}

          <TemperatureOverlay />

          {showGrid && (
            <Grid
              args={[0.5, 0.5]}
              cellSize={0.01}
              cellColor="#ccc"
              sectionSize={0.05}
              sectionColor="#999"
              fadeDistance={0.5}
              position={[0, -0.04, 0]}
            />
          )}

          <OrbitControls makeDefault enableDamping dampingFactor={0.1} minDistance={0.01} maxDistance={2} />
          <Environment preset="city" />
        </Suspense>
      </Canvas>
    </div>
  );
};

export default STLViewer;
