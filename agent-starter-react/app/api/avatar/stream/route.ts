// Old unscoped shared MJPEG is retired. Frames now require a session proof.
export async function GET() {
  return new Response(null, { status: 410, headers: { 'Cache-Control': 'no-store' } });
}
