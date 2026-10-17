# Workspace VIVAVerse — 17 octubre 2026

Carpetas activas: Avatar/ (SantiagoGarcia205/Avatar) y Edutech/ (sowiroar/Edutech).
Leer instrucciones propias de cada repo. Esta raíz no es un repositorio Git.
Base agentes: backp-fase1, voz de backup-fase-2 5e5abc3. Base assets: main.
Juan: Edutech feature/telemetry. Santiago: feature/avatar-presentation en Edutech
(interfaz/medios) y Avatar (assets/build). Jacobo: feature/voice-validation.

Fuentes actuales: Edutech/docs/mvp/README.md, specs, RUNBOOK y VALIDACION.
Especificación institucional: docs/md/VIVAVerse_Documento_Tecnico_v2.md.
Prioridad martes 20: voz estable + telemetría verificable; avatar opcional sin
comprometer voz. No mover prompts/roles/framework por copiar informe NeoIPS.
Moodle/identidad autenticada pendiente; visitante != estudiante identificado.
No prometer costos completos, SSO ni conversación por tests sintéticos.

Avatar conserva seis IDs prioritarios y originales históricos. Lira/Elian/Noa
aceptadas, Noa con SK_Noa_AlternateFace; no rediseñar. PR/LFS antes del pin Edutech.
Memoria medida antes corresponde al proceso Mac, no VRAM ni escalabilidad UAM.

archive/Edutech-legacy conserva la rama antigua y archivos locales; su .git contiene
metadatos de worktrees activos. NO BORRAR ni mover archive a ciegas. Las carpetas
Avatares y Edutech-integracion de la raíz son enlaces de compatibilidad, no clones.
tmp contiene worktrees históricos registrados: conservar. No git clean/reset.
El bridge grabado histórico sigue separado del bridge Gemini vigente.
La app Mac del 12 octubre solo incluye tres escenas, no las seis ni Gemini.

EDUTECH_SKIP_DEPLOY=1 en operaciones Git; no despliegues UAM automáticos.
No publicar credenciales VPN/RDP/.env/tokens. Revisar estado remoto con Jacobo
antes de actualizar servidor. RDP/VPN no equivalen a terminal remota disponible.
Historial de instrucciones: docs/history/2026-10-17-before-workspace-AGENTS.md.
