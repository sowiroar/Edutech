/** Public model metadata. This contains no room, identity, or credentials. */
export interface BrowserAvatar {
  engine: 'webgl';
  character: (typeof WEB_CHARACTERS)[number];
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

export const WEB_CHARACTERS = ['LIRA', 'NEXO', 'ELIAN', 'NOA', 'NOVA', 'ATLAS'] as const;

/** Retained identities from Avatar/avatars.json; a name alone is not an installed model. */
export const AVATAR_SOURCE_SCENES: Partial<Record<BrowserAvatar['character'], string>> = {
  LIRA: '/Game/VIVA/Avatars/Lira/Maps/L_Lira',
  ELIAN: '/Game/VIVA/Avatars/Elian/Maps/L_Elian',
  NOA: '/Game/VIVA/Avatars/Noa/Maps/L_Noa',
  NOVA: '/Game/VIVA/Avatars/Nova/Final/Maps/L_Nova_Final',
  ATLAS: '/Game/VIVA/Avatars/Atlas/Final/Maps/L_Atlas_Final',
};

/** Only an explicit agent signal chooses a model. Missing/unknown agents never borrow NEXO. */
export function avatarForAgent(character: string | undefined, assets: BrowserAvatar[]) {
  const signal = character?.trim().toUpperCase();
  const canonical = signal === 'NEXUS' ? 'NEXO' : signal;
  return assets.find((asset) => asset.character === canonical) ?? null;
}
