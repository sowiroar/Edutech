const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright");
const fs = require("fs");
(async () => {
  const root = require("path").resolve(__dirname, "..");
  const env = Object.fromEntries(
    fs
      .readFileSync(root + "/.env.voice", "utf8")
      .split("\n")
      .filter((x) => x.includes("=") && !x.startsWith("#"))
      .map((x) => {
        const i = x.indexOf("=");
        return [
          x.slice(0, i),
          x
            .slice(i + 1)
            .trim()
            .replace(/^["']|["']$/g, ""),
        ];
      }),
  );
  fs.mkdirSync(root + "/.impeccable/review", { recursive: true });
  const run = JSON.parse(
    fs.readFileSync(
      root + "/docs/validation/2026-10-17-dashboard/runtime-privacy.json",
    ),
  );
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1000 },
  });
  const result = { errors: [], checks: {} };
  page.on("pageerror", () => result.errors.push("pageerror"));
  await page.goto("http://localhost:3500/admin");
  await page
    .getByLabel("Contraseña", { exact: true })
    .fill(env.TELEMETRY_ADMIN_PASSWORD);
  await page.getByRole("button", { name: "Entrar al panel" }).click();
  await page.getByRole("heading", { name: "Actividad del periodo" }).waitFor();
  const btn = page.getByRole("button", {
    name: "Ver eventos de sesión " + run.session_id.slice(0, 8),
  });
  await btn.click();
  await page
    .getByLabel("Transcripción", { exact: true })
    .getByText("[CORREO]", { exact: false })
    .waitFor();
  result.checks.detail_focused = await page.evaluate(
    () => document.activeElement.id === "session-detail-title",
  );
  result.checks.raw_synthetic_email_absent = !(
    await page.locator(".telemetry-detail").innerText()
  ).includes("prueba.telemetria@example.com");
  for (const [name, width, height] of [
    ["detail-desktop", 1440, 1000],
    ["detail-mobile", 390, 844],
  ]) {
    await page.setViewportSize({ width, height });
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({
      path: root + "/.impeccable/review/" + name + ".png",
      fullPage: true,
    });
    result.checks[name + "_no_overflow"] = await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    );
  }
  await page
    .getByRole("button", { name: "Herramientas y acciones", exact: true })
    .click();
  await page
    .getByLabel("Traza de eventos", { exact: true })
    .getByText("consultar_especializacion_ia", { exact: false })
    .first()
    .waitFor();
  result.checks.tools_visible = true;
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: root + "/.impeccable/review/actions-desktop.png",
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Todos los eventos", exact: true })
    .click();
  await page
    .getByLabel("Traza de eventos", { exact: true })
    .getByText("Consumo reportado", { exact: true })
    .first()
    .waitFor();
  result.checks.technical_events_visible = true;
  await page
    .getByRole("button", { name: "Cerrar detalle", exact: true })
    .click();
  result.checks.return_focus = await btn.evaluate(
    (el) => document.activeElement === el,
  );
  const sessions = (await (await page.request.get('http://localhost:3500/api/admin/sessions')).json()).items;
  let legacy;
  for (const session of sessions) {
    const detail = await (await page.request.get('http://localhost:3500/api/admin/sessions/'+session.id+'/events?view=conversation')).json();
    if (!detail.transcript_capture) { legacy=session.id; break; }
  }
  if (legacy) {
    await page.getByRole('button', {name:'Ver eventos de sesión '+legacy.slice(0,8)}).click();
    await page.getByText('Esta sesión no tenía activada la transcripción.',{exact:false}).waitFor();
    result.checks.legacy_explained=true;
    await page.getByRole('button',{name:'Cerrar detalle',exact:true}).click();
  } else result.checks.legacy_explained='not available';
  await page.getByRole("combobox").first().selectOption("test");
  await page.getByRole("button", { name: "Actualizar", exact: true }).click();
  await page
    .getByText("No hay sesiones para estos filtros.", { exact: true })
    .waitFor();
  result.checks.empty_filtered = true;
  const fixture=await (await page.request.get('http://localhost:3500/api/admin/metrics?environment=test')).json();
  let release, started;
  const held=new Promise(resolve=>{release=resolve;});
  const requested=new Promise(resolve=>{started=resolve;});
  await page.route('**/api/admin/metrics?*', async route=> {started();await held;await route.fulfill({json:fixture});});
  await page.getByRole('button',{name:'Actualizar',exact:true}).click();await requested;
  await page.getByRole('button',{name:'Cerrar sesión',exact:true}).click();
  release();await page.waitForTimeout(200);
  await page.getByLabel('Contraseña',{exact:true}).waitFor();
  result.checks.late_response_does_not_restore_private_dashboard=await page.getByRole('heading',{name:'Actividad del periodo'}).count()===0;
  await page.getByLabel("Contraseña", { exact: true }).waitFor();
  result.checks.logout = true;
  fs.writeFileSync(
    root + "/docs/validation/2026-10-17-dashboard/browser.json",
    JSON.stringify(result, null, 2) + "\n",
  );
  console.log(JSON.stringify(result));
  await browser.close();
})().catch((e) => {
  console.error(e.name);
  process.exit(1);
});
