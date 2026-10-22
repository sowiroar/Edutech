/** Public model metadata. This contains no room, identity, or credentials. */
export interface BrowserAvatar {
  engine: 'webgl';
  character: 'NEXO' | 'LIRA' | 'ELIAN';
  modelUrl: string;
  backgroundUrl: string;
  backgroundColor?: string;
  bytes: number;
  sha256: string;
  frontYaw: number;
  mouthMorph?: string;
  rigProfile?: 'metahuman-mateo-web-v1' | 'metahuman-web-v1';
}

export const AVATAR_MAX_BYTES = 20 * 1024 * 1024;
export const AVATAR_MAX_TRIANGLES = 100_000;

export const WEB_CHARACTERS = ['LIRA', 'NEXO', 'ELIAN'] as const;

/** Only an explicit agent signal chooses a model. Missing/unknown agents never borrow NEXO. */
export function avatarForAgent(character: string | undefined, assets: BrowserAvatar[]) {
  const signal = character?.trim().toUpperCase();
  const canonical = signal === 'NEXUS' ? 'NEXO' : signal;
  return assets.find((asset) => asset.character === canonical) ?? null;
}
