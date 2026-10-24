import { NextResponse } from 'next/server';
import { browserAvatars } from '@/lib/browser-avatar-server';

export const dynamic = 'force-dynamic';
const headers = { 'Cache-Control': 'no-store' };
export async function GET() {
  const assets = await browserAvatars();
  return NextResponse.json(
    {
      availability: assets.length ? 'available' : 'offline',
      engine: 'webgl',
      asset: assets.find((asset) => asset.character === 'LIRA') ?? null,
      assets,
      muteAgentAudio: false,
    },
    { headers }
  );
}
