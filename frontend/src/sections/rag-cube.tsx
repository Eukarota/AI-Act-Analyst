"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, Line } from "@react-three/drei";
import * as THREE from "three";
import { Maximize2, Minimize2 } from "lucide-react";

import { useTranslation } from "@/lib/language";
import type { Citation, RetrievedPassage } from "@/lib/types";

interface Point {
  id: number;
  key: string;
  label: string;
  kind: "article" | "annex" | "recital" | "other";
  scope: string | null;
  x: number;
  y: number;
  z: number;
}

interface Projection {
  corpus_version: string;
  point_count: number;
  points: Point[];
}

interface Props {
  retrievedPassages: RetrievedPassage[];
  corpusVersion: string;
}

function citationKey(c: Citation): string {
  return [
    c.celex_id ?? "",
    c.article ?? "",
    c.paragraph ?? "",
    c.annex_ref ?? "",
    c.recital_ref ?? "",
  ].join("|");
}

const COLOR_BY_KIND: Record<Point["kind"], string> = {
  article: "#4b5563",
  annex: "#374151",
  recital: "#52525b",
  other: "#3f3f46",
};

// Dots: pale cyan with a cyan emissive glow.
const DOT_HIGHLIGHT_COLOR = "#a5f3fc";
const DOT_HIGHLIGHT_EMISSIVE = "#06b6d4";

// Lines: kept on a different hue (violet) so the path the agent took through
// the embedding space is visually distinct from the points it landed on.
const LINE_COLOR = "#1e8c00"; // red-500

function CubeFrame() {
  return (
    <lineSegments>
      <edgesGeometry args={[new THREE.BoxGeometry(2, 2, 2)]} />
      <lineBasicMaterial color="#828282" />
    </lineSegments>
  );
}

function Cloud({
  points,
  retrievedKeys,
  onHover,
}: {
  points: Point[];
  retrievedKeys: Set<string>;
  onHover: (point: Point | null) => void;
}) {
  const meshRef = useRef<THREE.InstancedMesh | null>(null);
  const dummy = useMemo(() => new THREE.Object3D(), []);
  const color = useMemo(() => new THREE.Color(), []);

  useEffect(() => {
    const mesh = meshRef.current;
    if (!mesh) return;
    for (let i = 0; i < points.length; i++) {
      const p = points[i];
      const highlighted = retrievedKeys.has(p.key);
      dummy.position.set(p.x, p.y, p.z);
      const scale = highlighted ? 0.024 : 0.008;
      dummy.scale.set(scale, scale, scale);
      dummy.updateMatrix();
      mesh.setMatrixAt(i, dummy.matrix);
      color.set(highlighted ? DOT_HIGHLIGHT_COLOR : COLOR_BY_KIND[p.kind]);
      mesh.setColorAt(i, color);
    }
    mesh.instanceMatrix.needsUpdate = true;
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
  }, [points, retrievedKeys, dummy, color]);

  return (
    <instancedMesh
      ref={meshRef}
      args={[undefined, undefined, points.length]}
      onPointerMove={(e) => {
        if (e.instanceId == null) return;
        const p = points[e.instanceId];
        if (p && retrievedKeys.has(p.key)) onHover(p);
        else onHover(null);
      }}
      onPointerOut={() => onHover(null)}
    >
      <sphereGeometry args={[1, 8, 8]} />
      <meshStandardMaterial
        vertexColors
        emissive={DOT_HIGHLIGHT_EMISSIVE}
        emissiveIntensity={0.4}
        metalness={0.1}
        roughness={0.85}
      />
    </instancedMesh>
  );
}

function RetrievedLines({
  points,
  retrievedKeys,
}: {
  points: Point[];
  retrievedKeys: Set<string>;
}) {
  const targets = useMemo(
    () => points.filter((p) => retrievedKeys.has(p.key)),
    [points, retrievedKeys],
  );
  return (
    <>
      {targets.map((p) => (
        <Line
          key={p.key}
          points={[
            [0, 0, 0],
            [p.x, p.y, p.z],
          ]}
          color={LINE_COLOR}
          opacity={0.95}
          transparent
          lineWidth={2.5}
        />
      ))}
    </>
  );
}

function Spinner() {
  const ref = useRef<THREE.Group | null>(null);
  useFrame((_, delta) => {
    if (ref.current) ref.current.rotation.y += delta * 0.08;
  });
  // The cube + cloud sit inside this slowly rotating group so users get
  // free motion to see the highlighted points without having to drag.
  return <group ref={ref} />;
}

export function RagCube({ retrievedPassages, corpusVersion }: Props) {
  const { t } = useTranslation();
  const [projection, setProjection] = useState<Projection | null>(null);
  const [hovered, setHovered] = useState<Point | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [fullscreen, setFullscreen] = useState(false);

  useEffect(() => {
    if (!fullscreen) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") setFullscreen(false);
    };
    window.addEventListener("keydown", handler);
    // Lock body scroll while the overlay is up.
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", handler);
      document.body.style.overflow = prev;
    };
  }, [fullscreen]);

  useEffect(() => {
    let cancelled = false;
    fetch("/chunks_pca3.json")
      .then((r) => {
        if (!r.ok) throw new Error(`status ${r.status}`);
        return r.json();
      })
      .then((data: Projection) => {
        if (!cancelled) setProjection(data);
      })
      .catch((e) => {
        if (!cancelled) setError(String(e));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const retrievedKeys = useMemo(
    () => new Set(retrievedPassages.map((p) => citationKey(p.citation))),
    [retrievedPassages],
  );

  const versionMatch = projection
    ? projection.corpus_version === corpusVersion
    : true;

  const matchedCount = useMemo(() => {
    if (!projection) return 0;
    const pointKeys = new Set(projection.points.map((p) => p.key));
    let n = 0;
    for (const k of retrievedKeys) if (pointKeys.has(k)) n++;
    return n;
  }, [projection, retrievedKeys]);

  const containerClasses = fullscreen
    ? "fixed inset-0 z-50 bg-background/95 backdrop-blur-2xl overflow-hidden"
    : "relative rounded-2xl bg-card/60 ring-1 ring-inset ring-white/[0.06] backdrop-blur-xl overflow-hidden";

  const canvasShellClasses = fullscreen
    ? "relative w-full h-[calc(100vh-3.5rem)]"
    : "relative h-64 w-full";

  return (
    <div className={containerClasses}>
      <div className="flex items-start justify-between px-4 pt-3 pb-2 gap-3">
        <div className="min-w-0">
          <p className="text-[12px] font-medium text-foreground">
            {t("report.rag_cube.heading")}
          </p>
          <p className="text-[10px] text-foreground-dim">
            {projection
              ? t("report.rag_cube.subhead_ready")
                  .replace("{matched}", String(matchedCount))
                  .replace("{total}", String(projection.point_count))
              : t("report.rag_cube.subhead_loading")}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-foreground-dim font-mono truncate max-w-[200px]">
            {hovered ? hovered.label : ""}
          </span>
          <button
            type="button"
            onClick={() => setFullscreen((v) => !v)}
            aria-label={
              fullscreen
                ? t("report.rag_cube.exit_fullscreen")
                : t("report.rag_cube.fullscreen")
            }
            title={
              fullscreen
                ? t("report.rag_cube.exit_fullscreen")
                : t("report.rag_cube.fullscreen")
            }
            className="rounded-md p-1 text-foreground-dim hover:text-foreground hover:bg-white/[0.06] transition-colors"
          >
            {fullscreen ? (
              <Minimize2 className="h-3.5 w-3.5" />
            ) : (
              <Maximize2 className="h-3.5 w-3.5" />
            )}
          </button>
        </div>
      </div>

      <div className={canvasShellClasses}>
        {error && (
          <p className="absolute inset-0 flex items-center justify-center text-[11px] text-foreground-dim">
            {t("report.rag_cube.error")}
          </p>
        )}
        {!error && !versionMatch && (
          <p className="absolute inset-x-0 top-2 z-10 mx-auto w-fit rounded-full bg-amber-500/10 text-amber-300 ring-1 ring-amber-500/30 px-2 py-0.5 text-[10px]">
            {t("report.rag_cube.version_mismatch")}
          </p>
        )}
        <Canvas
          camera={{ position: [2.4, 1.6, 2.4], fov: 45 }}
          gl={{ alpha: true, antialias: true }}
          style={{ background: "transparent" }}
        >
          <ambientLight intensity={0.7} />
          <pointLight position={[3, 3, 3]} intensity={0.4} />
          <Spinner />
          <CubeFrame />
          {projection && (
            <>
              <Cloud
                points={projection.points}
                retrievedKeys={retrievedKeys}
                onHover={setHovered}
              />
              <RetrievedLines
                points={projection.points}
                retrievedKeys={retrievedKeys}
              />
            </>
          )}
          <OrbitControls
            enablePan={false}
            enableZoom={fullscreen}
            autoRotate
            autoRotateSpeed={0.6}
          />
        </Canvas>
      </div>
    </div>
  );
}
