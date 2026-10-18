// Read-only browser check against a previously recorded synthetic conversation.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
(async () => {
  const root = path.resolve(__dirname, '..');
  const env = Object.fromEntries(fs.readFileSync(path.join(root, '.env.voice'), 'utf8')
    .split('\n').filter(x => x.includes('=') && !x.startsWith('#'))
    .map(x => { const i = x.indexOf('='); return [x.slice(0, i), x.slice(i+1).trim().replace(/^["']|["']$/g, '')]; }));
  const session = JSON.parse(fs.readFileSync(path.join(root, 'docs/validation/2026-10-17-dashboard/browser-voice.json'))).session_id;
  assert.ok(session, 'Synthetic session is required');
  const out = path.join(root, 'docs/validation/2026-10-17-field-clarity');
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });
    const result = { session_id: session, checks: {}, page_errors: 0 };
    page.on('pageerror', () => result.page_errors++);
    await page.goto('http://localhost:3500/admin');
    await page.getByLabel('Contraseña', { exact: true }).fill(env.TELEMETRY_ADMIN_PASSWORD);
    await page.getByRole('button', { name: 'Entrar al panel' }).click();
    await page.getByRole('button', { name: 'Ver eventos de sesión ' + session.slice(0, 8) }).click();
    const message = page.locator('.telemetry-message').first();
    await message.locator('summary').first().click();
    const technical = JSON.parse(await message.locator('pre').innerText());
    assert.equal('agent_id' in technical, false);
    assert.equal('text' in technical.payload, false);
    assert.equal(technical.payload.interrupted, false);
    assert.equal(technical.trace_id, session.replaceAll('-', ''));
    result.checks.available_only_and_false_preserved = true;
    await message.locator('summary').filter({ hasText: 'Campos sin dato' }).click();
    assert.match(await message.innerText(), /aún no está enlazado/);
    assert.match(await message.innerText(), /Visitante sin autenticación/);
    assert.match(await message.innerText(), /no identifica de forma fiable/);
    result.checks.missing_explained = true;
    for (const [name, width, height] of [['desktop', 1440, 1100], ['tablet', 768, 1024], ['mobile', 390, 844]]) {
      await page.setViewportSize({ width, height });
      await message.locator('summary').first().evaluate(el => el.scrollIntoView({ block: 'start', behavior: 'instant' }));
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
      result.checks[name + '_no_overflow'] = true;
      await page.screenshot({ path: path.join(out, name + '.png') });
    }
    await page.setViewportSize({ width: 720, height: 550 }); // equivalent CSS viewport at 200% of desktop
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    result.checks.narrow_zoom_viewport = true;
    assert.equal(result.page_errors, 0);
    fs.writeFileSync(path.join(out, 'browser.json'), JSON.stringify(result, null, 2) + '\n');
    console.log(JSON.stringify(result));
  } finally { await browser.close(); }
})().catch(e => { console.error(e.message); process.exitCode = 1; });
