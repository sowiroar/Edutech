"""Bounded, memory-only latest image uploaded by the local Unreal capture."""

import time


class Frames:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.image = None
        self.received_at = None
        self.count = 0
        self.started = clock()
        self.source = None

    def push(self, data):
        if (
            not isinstance(data, bytes)
            or len(data) > 4 * 1024 * 1024
            or not data.startswith(b"\xff\xd8")
            or not data.endswith(b"\xff\xd9")
        ):
            raise ValueError("Expected bounded JPEG")
        self.image, self.received_at = data, self.clock()
        self.count += 1

    def clear(self):
        self.image = self.received_at = self.source = None

    def snapshot(self):
        if self.received_at is None or self.clock() - self.received_at >= 0.75:
            return None
        return self.image

    def metrics(self):
        return {
            "ready": self.snapshot() is not None,
            "frames_received": self.count,
            "elapsed_seconds": self.clock() - self.started,
            "frame_age_ms": (self.clock() - self.received_at) * 1000
            if self.received_at is not None
            else None,
        }
