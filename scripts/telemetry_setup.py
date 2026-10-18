#!/usr/bin/env python3
"""Generate local-only telemetry secrets. Never prints secret values."""
import os
import secrets
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def initialize(path=ROOT/'.env.voice'):
    if not path.is_file():
        raise SystemExit('Run python3 scripts/voice_demo.py init first')
    content=path.read_text()
    existing={line.split('=',1)[0].strip():line.split('=',1)[1].strip() for line in content.splitlines() if '=' in line and not line.lstrip().startswith('#')}
    defaults={
        'TELEMETRY_SIGNING_SECRET':secrets.token_urlsafe(48),
        'TELEMETRY_INTERNAL_KEY':secrets.token_urlsafe(48),
        'TELEMETRY_DB_PASSWORD':secrets.token_urlsafe(32),
        'TELEMETRY_ADMIN_PASSWORD':secrets.token_urlsafe(24),
        'TELEMETRY_ENVIRONMENT':'local',
        'TELEMETRY_PUBLIC_ORIGIN':'http://localhost:3500',
        'TELEMETRY_COOKIE_SECURE':'false',
    }
    additions={k:v for k,v in defaults.items() if not existing.get(k)}
    if additions:
        # Replace empty declarations too: Compose uses the final occurrence.
        fd=os.open(path,os.O_WRONLY|os.O_APPEND,0o600)
        with os.fdopen(fd,'a') as dest:
            dest.write('\n# Local telemetry (private; never commit)\n')
            dest.write(''.join(f'{k}={v}\n' for k,v in additions.items()))
    path.chmod(0o600)
    print('Telemetry configuration ready. Admin password stays in .env.voice.')

if __name__=='__main__':
    initialize()
