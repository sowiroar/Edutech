# Workspace Edutech · Familia VIVA

Esta carpeta reúne dos repositorios independientes:

```text
edutech/
├── AGENTS.md
├── CLAUDE.md
├── README.md
├── Avatar/       # Autoría Unreal de los seis personajes
├── Edutech/      # Agentes, frontend, telemetría e integración
└── docs/         # Referencias del workspace
```

La documentación versionada vigente está en **Edutech/docs/**. Una copia bajo
docs/ no se sincroniza automáticamente y no debe tomarse como un estado más reciente.

- [Aplicación y arranque](Edutech/README.md).
- [Avatares web: LIRA de Juan, NEXO y ELIAN](Edutech/docs/mvp/AVATAR_WEB.md).
- [Consumo medido](Edutech/docs/validation/2026-10-21-avatar-resources/README.md).
- [Trabajo del equipo y ramas](Edutech/docs/mvp/FLUJO.md).
- [Proyecto Unreal](Avatar/README.md).

Trabajar con Git dentro de cada repositorio. main es la base; backp-fase1 es
una referencia de compatibilidad, sin sincronización automática. El submódulo
Edutech/Avatar fija una versión y no sustituye el checkout de autoría hermano.
Compartir código por cambios revisados y modelos por la entrega privada del equipo;
no copiar entornos, claves, cachés o bases locales.
