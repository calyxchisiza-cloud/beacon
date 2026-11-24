"""A small client. It evaluates flags from a cached snapshot.

When the service cannot be reached, the last snapshot is used. A process that
has never received a snapshot cannot invent a configuration.
"""

from __future__ import annotations

import time

import httpx

from beacon_core.eval import evaluate_flag


class BeaconError(RuntimeError):
    pass


class Client:
    def __init__(self, base_url: str, sdk_key: str, ttl: float = 30.0, timeout: float = 2.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.sdk_key = sdk_key
        self.ttl = ttl
        self.timeout = timeout
        self.snapshot: dict | None = None
        self.loaded = 0.0
        self.stale = False

    def variation(self, flag: str, user_key: str, attributes: dict | None = None):
        snapshot = self._snapshot()
        found = next((item for item in snapshot.get("flags") or [] if item["key"] == flag), None)
        if found is None:
            raise BeaconError(f"flag {flag} is not in the snapshot")
        result = evaluate_flag(found, {"key": user_key, "attributes": attributes or {}}, snapshot.get("segments") or {})
        result["stale"] = self.stale
        return result

    def _snapshot(self) -> dict:
        fresh = self.snapshot is not None and (time.time() - self.loaded) < self.ttl
        if fresh:
            self.stale = False
            return self.snapshot
        try:
            response = httpx.get(
                f"{self.base_url}/sdk/v1/flags",
                headers={"Authorization": f"Bearer {self.sdk_key}"},
                timeout=self.timeout,
            )
            response.raise_for_status()
        except (httpx.HTTPError, OSError):
            if self.snapshot is None:
                raise BeaconError("configuration is unavailable") from None
            self.stale = True
            return self.snapshot
        self.snapshot = response.json()
        self.loaded = time.time()
        self.stale = False
        return self.snapshot
