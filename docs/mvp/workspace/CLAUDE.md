## Main es la base única de desarrollo — 17 octubre 2026, cierre

Decisión final del usuario: trabajar desde origin/main en Edutech y Avatar.
Edutech conserva main, backp-fase1 (alineada al cerrar esta limpieza, sin sincronía
automática) y backup-fase-2 (respaldo intacto de Jacobo 5e5abc3). Avatar conserva main.
Gemini MVP y las features anteriores ya están integradas; se retiran sus nombres.
No recrear develop ni las ramas cerradas por seguir bloques históricos debajo.
Santiago crea una feature nueva desde origin/main actualizado; Juan y Jacobo igual.
PR a main, checks, merge y retiro de la rama terminada. Leer Edutech/docs/mvp/FLUJO.md y
AUDITORIA_RAMAS_2026-10-17.md en esa carpeta. CI permite features a main; releases
no abren back-merge a develop ni despliegan UAM. La cuenta WRITE no configura protección.
Las bases anteriores y pruebas se conservan en la historia. UAM/renderer/concurrencia
siguen pendientes de aceptación; este cambio no altera runtime, prompts ni assets.

# Workspace VIVAVerse — 17 octubre 2026

Carpetas activas: Avatar/ (SantiagoGarcia205/Avatar) y Edutech/ (sowiroar/Edutech).
Leer instrucciones propias de cada repo. Esta raíz no es un repositorio Git.
Base agentes y assets: origin/main en cada repositorio. backup-fase-2 conserva la voz de Jacobo en 5e5abc3.
Cada colaborador crea una feature nueva desde origin/main; se integra por PR a main
y se retira al terminar. Santiago: avatar; Juan: telemetría; Jacobo: validación de voz.

Fuentes actuales: Edutech/docs/mvp/README.md, specs, RUNBOOK y VALIDACION.
Especificación institucional: docs/md/VIVAVerse_Documento_Tecnico_v2.md.
Prioridad martes 20: voz estable + telemetría verificable; avatar opcional sin
comprometer voz. No mover prompts/roles/framework por copiar informe NeoIPS.
Moodle/identidad autenticada pendiente; visitante != estudiante identificado.
No prometer costos completos, SSO ni conversación por tests sintéticos.

Avatar conserva seis IDs prioritarios y originales históricos. Lira/Elian/Noa
aceptadas, Noa con SK_Noa_AlternateFace; no rediseñar. PR/LFS antes del pin Edutech.
Memoria medida antes corresponde al proceso Mac, no VRAM ni escalabilidad UAM.

archive/Edutech-legacy conserva el commit antiguo (HEAD separado) y archivos locales; su .git contiene
metadatos de worktrees activos. NO BORRAR ni mover archive a ciegas. Las carpetas
Avatares y Edutech-integracion de la raíz son enlaces de compatibilidad, no clones.
Los worktrees tmp históricos se retiraron por petición del usuario, después de
respaldar y verificar sus archivos en archive/tmp-backup-20261017. No git clean/reset.
El bridge grabado histórico sigue separado del bridge Gemini vigente.
La app Mac del 12 octubre solo incluye tres escenas, no las seis ni Gemini.

EDUTECH_SKIP_DEPLOY=1 en operaciones Git; no despliegues UAM automáticos.
No publicar credenciales VPN/RDP/.env/tokens. Revisar estado remoto con Jacobo
antes de actualizar servidor. RDP/VPN no equivalen a terminal remota disponible.
Historial de instrucciones: docs/history/2026-10-17-before-workspace-AGENTS.md.
