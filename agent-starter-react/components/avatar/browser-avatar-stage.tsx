'use client';

import { type RefObject, useEffect, useRef } from 'react';
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { AVATAR_MAX_BYTES, AVATAR_MAX_TRIANGLES, type BrowserAvatar } from '@/lib/browser-avatar';
import { cn } from '@/lib/shadcn/utils';
import { applyElianMaterials } from './elian-materials';
import { applyLiraMaterials } from './lira-materials';
import { createMateoRig } from './mateo-rig';
import { applyNexoMaterials } from './nexo-materials';
import { MAX_TEXTURE_BYTES, assetMemory, renderSize } from './render-budget';
import { type MouthPose, REST_MOUTH } from './speech-motion';

export interface AvatarSample {
  character: BrowserAvatar['character'];
  timestamp: string;
  fps: number;
  renderSubmissionMs: number;
  drawCalls: number;
  triangles: number;
  geometries: number;
  textures: number;
  pageJsHeapBytes: number | null;
  mouthAnimationAvailable: boolean;
  modelBytes: number;
  loadMs: number;
  fetchMs: number;
  parseMs: number;
  firstFrameMs: number;
  width: number;
  height: number;
  animationClips: number;
  textureBytesEstimate: number;
  geometryDataBytes: number;
  lipShapesAvailable: boolean;
  mouthOpen: number;
  mouthRound: number;
  mouthWide: number;
}

function disposeModel(root: THREE.Object3D) {
  const geometries = new Set<THREE.BufferGeometry>();
  const materials = new Set<THREE.Material>();
  const textures = new Set<THREE.Texture>();
  const skeletons = new Set<THREE.Skeleton>();
  root.traverse((node) => {
    if (!(node instanceof THREE.Mesh)) return;
    geometries.add(node.geometry);
    for (const material of Array.isArray(node.material) ? node.material : [node.material]) {
      materials.add(material);
      for (const value of Object.values(material))
        if (value instanceof THREE.Texture) textures.add(value);
    }
    if (node instanceof THREE.SkinnedMesh) skeletons.add(node.skeleton);
  });
  geometries.forEach((g) => g.dispose());
  materials.forEach((m) => m.dispose());
  textures.forEach((t) => {
    t.dispose();
    if (typeof ImageBitmap !== 'undefined' && t.source.data instanceof ImageBitmap)
      t.source.data.close();
  });
  skeletons.forEach((s) => s.dispose());
}

export default function BrowserAvatarStage({
  asset,
  compact = false,
  speech,
  onReady,
  onFailure,
  onSample,
}: {
  asset: BrowserAvatar;
  compact?: boolean;
  speech?: RefObject<() => MouthPose>;
  onReady: () => void;
  onFailure: () => void;
  onSample?: (sample: AvatarSample) => void;
}) {
  const host = useRef<HTMLDivElement>(null);
  const callbacks = useRef({ onReady, onFailure, onSample, speech });
  callbacks.current = { onReady, onFailure, onSample, speech };
  useEffect(() => {
    const element = host.current;
    if (!element) return;
    let cancelled = false,
      frame = 0;
    let renderer: THREE.WebGLRenderer | undefined;
    let model: THREE.Group | undefined;
    let mixer: THREE.AnimationMixer | undefined;
    let resize: ResizeObserver | undefined;
    let startFrames = () => {};
    const controller = new AbortController();
    const contextLost = (event: Event) => {
      event.preventDefault();
      cancelAnimationFrame(frame);
      if (!cancelled) callbacks.current.onFailure();
    };
    const visibility = () => {
      cancelAnimationFrame(frame);
      if (!document.hidden && !cancelled) startFrames();
    };
    const initialize = async () => {
      const started = performance.now();
      if (asset.bytes > AVATAR_MAX_BYTES) throw new Error('Model exceeds web budget');
      const response = await fetch(asset.modelUrl, {
        signal: AbortSignal.any([controller.signal, AbortSignal.timeout(60_000)]),
      });
      if (!response.ok) throw new Error('Model unavailable');
      const bytes = await response.arrayBuffer();
      if (cancelled) return;
      if (bytes.byteLength !== asset.bytes) throw new Error('Unexpected model size');
      const fetched = performance.now();
      const gltf = await new GLTFLoader().parseAsync(bytes, '');
      const parsed = performance.now();
      if (cancelled) {
        disposeModel(gltf.scene);
        return;
      }
      model = gltf.scene;
      if (asset.character === 'LIRA') applyLiraMaterials(model);
      if (asset.character === 'NEXO') applyNexoMaterials(model);
      if (asset.character === 'ELIAN') applyElianMaterials(model);
      let triangles = 0;
      const mouths: { mesh: THREE.Mesh; index: number }[] = [];
      model.traverse((node) => {
        if (!(node instanceof THREE.Mesh)) return;
        triangles += (node.geometry.index?.count ?? node.geometry.attributes.position.count) / 3;
        node.castShadow = false;
        node.receiveShadow = false;
        const index = asset.mouthMorph ? node.morphTargetDictionary?.[asset.mouthMorph] : undefined;
        if (index !== undefined && node.morphTargetInfluences) mouths.push({ mesh: node, index });
      });
      if (triangles > AVATAR_MAX_TRIANGLES) throw new Error('Geometry exceeds web budget');
      const memory = assetMemory(model);
      if (memory.textureBytesEstimate > MAX_TEXTURE_BYTES)
        throw new Error('Textures exceed web budget');
      renderer = new THREE.WebGLRenderer({
        alpha: true,
        antialias: true,
        powerPreference: 'low-power',
      });
      renderer.setPixelRatio(1);
      renderer.outputColorSpace = THREE.SRGBColorSpace;
      renderer.toneMapping = THREE.ACESFilmicToneMapping;
      renderer.toneMappingExposure = 1;
      renderer.domElement.setAttribute('aria-label', `${asset.character}, avatar 3D`);
      renderer.domElement.style.cssText = 'width:100%;height:100%;display:block';
      renderer.domElement.addEventListener('webglcontextlost', contextLost);
      element.appendChild(renderer.domElement);
      const scene = new THREE.Scene();
      const pivot = new THREE.Group();
      pivot.add(model);
      pivot.rotation.y = asset.frontYaw;
      scene.add(pivot);
      mixer = new THREE.AnimationMixer(model);
      for (const clip of gltf.animations) mixer.clipAction(clip).play();
      mixer.update(0);
      const bounds = new THREE.Box3().setFromObject(pivot);
      const size = bounds.getSize(new THREE.Vector3());
      if (!Number.isFinite(size.y) || size.y <= 0) throw new Error('Invalid bounds');
      pivot.scale.setScalar(1.75 / size.y);
      const normalized = new THREE.Box3().setFromObject(pivot);
      const center = normalized.getCenter(new THREE.Vector3());
      pivot.position.set(-center.x, -normalized.min.y, -center.z);
      const rig = asset.rigProfile ? createMateoRig(model) : undefined;
      const camera = new THREE.PerspectiveCamera(32, 16 / 9, 0.01, 20);
      camera.position.set(
        0,
        asset.character === 'LIRA' ? 1.4 : asset.character === 'ELIAN' ? 1.48 : 1.43,
        asset.character === 'ELIAN' ? 1.06 : 1.3
      );
      camera.lookAt(
        0,
        asset.character === 'LIRA' ? 1.39 : asset.character === 'ELIAN' ? 1.47 : 1.42,
        0
      );
      scene.add(new THREE.HemisphereLight(0xd7eaff, 0x4b4053, 2.5));
      const key = new THREE.DirectionalLight(0xfff2e7, asset.character === 'NEXO' ? 2.2 : 3);
      key.position.set(-1, 3, 4);
      scene.add(key);
      const fill = new THREE.DirectionalLight(0xe8f2ff, 1.5);
      fill.position.set(2, 1, 4);
      scene.add(fill);
      const rim = new THREE.DirectionalLight(
        asset.character === 'LIRA' ? 0xc77dff : asset.character === 'ELIAN' ? 0x00c2b2 : 0x55ddff,
        1.4
      );
      rim.position.set(2, 2, -2);
      scene.add(rim);
      resize = new ResizeObserver(() => {
        if (!renderer) return;
        const { width, height } = renderSize(
          element.clientWidth,
          element.clientHeight,
          window.devicePixelRatio
        );
        renderer.setSize(width, height, false);
        camera.aspect = width / height;
        camera.updateProjectionMatrix();
      });
      resize.observe(element);
      const loadMs = performance.now() - started;
      let lastRender = 0,
        previous = performance.now(),
        reportStart = previous,
        renders = 0,
        renderMs = 0;
      let animatedSeconds = 1;
      let ready = false;
      let firstFrameMs = 0;
      const renderFrame = (now: number) => {
        if (cancelled || document.hidden || !renderer) return;
        frame = requestAnimationFrame(renderFrame);
        if (now - lastRender < 1000 / 30) return;
        lastRender = now - ((now - lastRender) % (1000 / 30));
        const dt = Math.min(0.1, (now - previous) / 1000);
        previous = now;
        mixer?.update(dt);
        animatedSeconds += dt;
        const mouth = callbacks.current.speech?.current() ?? REST_MOUTH;
        mouths.forEach(({ mesh, index }) => {
          mesh.morphTargetInfluences![index] = mouth.open;
        });
        rig?.update(mouth, animatedSeconds);
        const submitted = performance.now();
        try {
          renderer.render(scene, camera);
        } catch {
          cancelAnimationFrame(frame);
          callbacks.current.onFailure();
          return;
        }
        renderMs += performance.now() - submitted;
        renders++;
        if (!ready) {
          ready = true;
          // Includes first-draw shader work; this is submission, not GPU completion.
          firstFrameMs = performance.now() - started;
          callbacks.current.onReady();
        }
        if (now - reportStart >= 1000) {
          const heap = (performance as Performance & { memory?: { usedJSHeapSize: number } })
            .memory;
          const sample: AvatarSample = {
            character: asset.character,
            timestamp: new Date().toISOString(),
            fps: (renders * 1000) / (now - reportStart),
            renderSubmissionMs: renderMs / renders,
            drawCalls: renderer.info.render.calls,
            triangles: renderer.info.render.triangles,
            geometries: renderer.info.memory.geometries,
            textures: renderer.info.memory.textures,
            pageJsHeapBytes: heap?.usedJSHeapSize ?? null,
            mouthAnimationAvailable: mouths.length > 0 || !!rig?.mouthAvailable,
            modelBytes: asset.bytes,
            loadMs,
            fetchMs: fetched - started,
            parseMs: parsed - fetched,
            firstFrameMs,
            width: renderer.domElement.width,
            height: renderer.domElement.height,
            animationClips: gltf.animations.length,
            ...memory,
            lipShapesAvailable: rig?.lipShapesAvailable ?? false,
            mouthOpen: mouth.open,
            mouthRound: mouth.round,
            mouthWide: mouth.wide,
          };
          callbacks.current.onSample?.(sample);
          // Same non-sensitive measurements in preview and conversation, without an extra service.
          window.dispatchEvent(new CustomEvent('viva:avatar-sample', { detail: sample }));
          reportStart = now;
          renders = 0;
          renderMs = 0;
        }
      };
      startFrames = () => {
        previous = reportStart = performance.now();
        renders = 0;
        renderMs = 0;
        lastRender = 0;
        frame = requestAnimationFrame(renderFrame);
      };
      document.addEventListener('visibilitychange', visibility);
      if (!document.hidden) startFrames();
    };
    void initialize().catch(() => {
      if (!cancelled) callbacks.current.onFailure();
    });
    return () => {
      cancelled = true;
      controller.abort();
      cancelAnimationFrame(frame);
      document.removeEventListener('visibilitychange', visibility);
      resize?.disconnect();
      mixer?.stopAllAction();
      if (model) mixer?.uncacheRoot(model);
      if (model) disposeModel(model);
      if (renderer) {
        renderer.domElement.removeEventListener('webglcontextlost', contextLost);
        renderer.dispose();
        renderer.forceContextLoss();
        renderer.domElement.remove();
      }
    };
  }, [asset]);
  return (
    <div
      ref={host}
      style={{
        backgroundImage: asset.backgroundColor ? undefined : `url(${asset.backgroundUrl})`,
        backgroundColor: asset.backgroundColor,
      }}
      className={cn(
        'overflow-hidden rounded-xl bg-slate-950 bg-cover bg-center',
        compact ? 'h-[120px] w-[213px]' : 'aspect-video w-[min(100vw-2rem,60rem)]'
      )}
    />
  );
}
