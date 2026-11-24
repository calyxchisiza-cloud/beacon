from sdk.beacon import BeaconError, Client


SNAPSHOT = {
    "segments": {},
    "flags": [
        {
            "key": "payment",
            "enabled": True,
            "off": "old",
            "fallthrough": "new",
            "salt": "demo",
            "rollout": 10000,
            "rules": [],
            "variations": {"old": False, "new": True},
        }
    ],
}


def test_a_client_uses_the_last_snapshot_when_the_service_is_down():
    client = Client("http://127.0.0.1:9", "bk_missing", ttl=0, timeout=0.2)
    client.snapshot = SNAPSHOT
    client.loaded = 0
    result = client.variation("payment", "user-1")
    assert result["value"] is True
    assert result["stale"] is True


def test_a_client_without_a_snapshot_reports_the_outage():
    client = Client("http://127.0.0.1:9", "bk_missing", ttl=0, timeout=0.2)
    try:
        client.variation("payment", "user-1")
    except BeaconError as exc:
        assert "unavailable" in str(exc)
    else:
        raise AssertionError("expected an outage")
