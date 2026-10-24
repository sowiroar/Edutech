import { readFile, stat } from 'node:fs/promises';
import path from 'node:path';
import {
  AVATAR_MAX_BYTES,
  AVATAR_SOURCE_SCENES,
  type BrowserAvatar,
  WEB_CHARACTERS,
} from './browser-avatar';

// Only locally installed, content-addressed models can be served. No external asset URLs.
export async function browserAvatar({
  preview = false,
  character = 'NEXO',
}: {
  preview?: boolean;
  character?: BrowserAvatar['character'];
} = {}): Promise<BrowserAvatar | null> {
  try {
    if (!WEB_CHARACTERS.includes(character)) return null;
    const slug = character.toLowerCase();
    const directory = path.join(process.cwd(), 'public', 'avatars', slug);
    let candidate: string | null = null;
    if (preview) {
      candidate = await readFile(path.join(directory, 'manifest.preview.json'), 'utf8').catch(
        (error: NodeJS.ErrnoException) => {
          if (error.code === 'ENOENT') return null;
          throw error;
        }
      );
    }
    const manifest = JSON.parse(
      candidate ?? (await readFile(path.join(directory, 'manifest.json'), 'utf8'))
    );
    if (manifest.character && manifest.character !== character) return null;
    const sourceScene = AVATAR_SOURCE_SCENES[character];
    if (sourceScene && (manifest.character !== character || manifest.source_scene !== sourceScene))
      return null;
    if (manifest.web_profile !== 2 || manifest.export_profile !== 3) return null;
    // A candidate may be inspected locally without advertising it for a live call.
    if (
      !preview &&
      (manifest.visual_review !== 'passed' ||
        manifest.motion_review !== 'passed' ||
        manifest.mouth_mapping !== 'amplitude-verified' ||
        !(manifest.animations > 0))
    )
      return null;
    if (!/^[a-f0-9]{64}$/.test(manifest.sha256)) return null;
    const filename = `${slug}-${manifest.sha256}.glb`;
    const model = await stat(path.join(directory, filename));
    if (
      !model.isFile() ||
      model.size < 20 ||
      model.size !== manifest.bytes ||
      model.size > AVATAR_MAX_BYTES
    )
      return null;
    if (!Number.isFinite(manifest.frontYaw)) return null;
    const background = candidate === null ? 'uam-background.jpg' : 'uam-background.preview.jpg';
    await stat(path.join(directory, background));
    return {
      engine: 'webgl',
      ...(candidate !== null ? { reviewPending: true } : {}),
      character,
      modelUrl: `/avatars/${slug}/${filename}`,
      backgroundUrl: `/avatars/${slug}/${background}`,
      ...(typeof manifest.background_color === 'string' &&
      /^#[a-fA-F0-9]{6}$/.test(manifest.background_color)
        ? { backgroundColor: manifest.background_color }
        : {}),
      bytes: model.size,
      sha256: manifest.sha256,
      frontYaw: manifest.frontYaw,
      ...(typeof manifest.mouthMorph === 'string' ? { mouthMorph: manifest.mouthMorph } : {}),
      ...(['metahuman-mateo-web-v1', 'metahuman-web-v1'].includes(manifest.rigProfile)
        ? { rigProfile: manifest.rigProfile as BrowserAvatar['rigProfile'] }
        : {}),
    };
  } catch {
    return null;
  }
}

export async function browserAvatars(): Promise<BrowserAvatar[]> {
  const assets = await Promise.all(WEB_CHARACTERS.map((character) => browserAvatar({ character })));
  return assets.filter((asset): asset is BrowserAvatar => asset !== null);
}
