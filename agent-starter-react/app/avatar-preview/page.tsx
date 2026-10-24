import { existsSync } from 'node:fs';
import path from 'node:path';
import AvatarPreview from '@/components/avatar/avatar-preview';
import { WEB_CHARACTERS } from '@/lib/browser-avatar';
import { browserAvatar } from '@/lib/browser-avatar-server';

export const dynamic = 'force-dynamic';
export default async function Page({
  searchParams,
}: {
  searchParams: Promise<{ character?: string }>;
}) {
  const query = await searchParams;
  const character =
    WEB_CHARACTERS.find((name) => name === query.character?.toUpperCase()) ?? 'NEXO';
  return (
    <AvatarPreview
      key={character}
      character={character}
      sampleAvailable={existsSync(
        path.join(process.cwd(), 'public/avatars/articulation-sample.wav')
      )}
      assets={(
        await Promise.all(
          WEB_CHARACTERS.map((name) => browserAvatar({ preview: true, character: name }))
        )
      ).filter((asset) => asset !== null)}
    />
  );
}
