"""One renderer, one explicitly selected room. No tokens in logs or URLs."""

import secrets
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class Lease:
    room: str
    token: str
    expires: float


class RendererLease:
    def __init__(self, clock=time.monotonic, ttl=30.0):
        self.clock = clock
        self.ttl = ttl
        self._current = None

    @property
    def current(self):
        if self._current and self._current.expires <= self.clock():
            self._current = None
        return self._current

    def acquire(self, room):
        if self.current or not room.startswith("viva_") or len(room) > 100:
            return None
        self._current = Lease(room, secrets.token_urlsafe(32), self.clock() + self.ttl)
        return self._current

    def matches(self, room, token):
        lease = self.current
        return bool(
            lease and lease.room == room and secrets.compare_digest(lease.token, token)
        )

    def renew(self, room, token):
        if not self.matches(room, token):
            return False
        self._current = Lease(room, token, self.clock() + self.ttl)
        return True

    def release(self, room, token):
        if not self.matches(room, token):
            return False
        self._current = None
        return True
