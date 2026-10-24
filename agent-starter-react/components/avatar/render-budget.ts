import * as THREE from 'three';

export const MAX_TEXTURE_BYTES = 64 * 1024 * 1024;

/** Hysteresis avoids oscillating quality. Geometry and texture assets never change. */
export function createResolutionBudget() {
  let level = 0,
    slow = 0,
    fast = 0,
    cooldown = 3;
  const scales = [1, 0.85, 0.7, 0.55];
  return {
    get scale() {
      return scales[level];
    },
    observe(fps: number) {
      if (!Number.isFinite(fps) || fps < 0) return false;
      if (cooldown > 0) {
        cooldown--;
        return false;
      }
      slow = fps < 24 ? slow + 1 : 0;
      fast = fps >= 29 ? fast + 1 : 0;
      if (slow >= 3 && level < scales.length - 1) {
        level++;
        slow = fast = 0;
        cooldown = 5;
        return true;
      }
      if (fast >= 20 && level > 0) {
        level--;
        slow = fast = 0;
        cooldown = 10;
        return true;
      }
      return false;
    },
  };
}

/** Bound both dimensions, including high-DPI and unusually tall containers. */
export function renderSize(width: number, height: number, deviceRatio = 1) {
  const w = Math.max(2, width),
    h = Math.max(2, height);
  const scale = Math.min(Math.max(1, deviceRatio), 1.5, 1280 / w, 720 / h);
  return { width: Math.max(2, Math.floor(w * scale)), height: Math.max(2, Math.floor(h * scale)) };
}

/** Asset estimates only: excludes framebuffers, browser composition, drivers and other tabs. */
export function assetMemory(root: THREE.Object3D) {
  const textures = new Set<THREE.Texture>();
  const buffers = new Set<THREE.BufferAttribute | THREE.InterleavedBuffer>();
  root.traverse((node) => {
    if (!(node instanceof THREE.Mesh)) return;
    const geometry = node.geometry as THREE.BufferGeometry;
    const add = (attribute: THREE.BufferAttribute | THREE.InterleavedBufferAttribute) => {
      buffers.add(
        attribute instanceof THREE.InterleavedBufferAttribute ? attribute.data : attribute
      );
    };
    Object.values(geometry.attributes).forEach(add);
    if (geometry.index) add(geometry.index);
    Object.values(geometry.morphAttributes).forEach((attributes) => attributes?.forEach(add));
    for (const material of Array.isArray(node.material) ? node.material : [node.material])
      for (const value of Object.values(material))
        if (value instanceof THREE.Texture) textures.add(value);
  });
  let textureBytesEstimate = 0;
  textures.forEach((texture) => {
    if (texture instanceof THREE.CompressedTexture) {
      textureBytesEstimate += texture.mipmaps.reduce(
        (sum, level) => sum + level.data.byteLength,
        0
      );
    } else {
      const image = texture.image as { width?: number; height?: number } | undefined;
      const width = image?.width ?? 0,
        height = image?.height ?? 0;
      // glTF PNG/JPEG textures use RGBA8 after upload, regardless of download compression.
      textureBytesEstimate += Math.ceil(width * height * 4 * (texture.generateMipmaps ? 4 / 3 : 1));
    }
  });
  return {
    textureBytesEstimate,
    geometryDataBytes: [...buffers].reduce((sum, buffer) => sum + buffer.array.byteLength, 0),
  };
}
