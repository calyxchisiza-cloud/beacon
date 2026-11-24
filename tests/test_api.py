def _setup(client, headers, rollout=5):
    assert client.post("/orgs", headers=headers, json={"name": "Acme", "slug": "acme"}).status_code == 201
    assert client.post("/orgs/acme/applications", headers=headers, json={"key": "shop", "name": "Shop"}).status_code == 201
    assert (
        client.post(
            "/orgs/acme/applications/shop/environments",
            headers=headers,
            json={"key": "production", "name": "Production"},
        ).status_code
        == 201
    )
    created = client.post(
        "/orgs/acme/applications/shop/flags",
        headers=headers,
        json={
            "key": "payment",
            "name": "Payment",
            "variations": {"old": False, "new": True},
            "off_variation": "old",
            "fallthrough_variation": "new",
        },
    )
    assert created.status_code == 201, created.text
    updated = client.put(
        "/orgs/acme/applications/shop/flags/payment/environments/production",
        headers=headers,
        json={
            "enabled": True,
            "off_variation": "old",
            "fallthrough_variation": "new",
            "rollout_percent": rollout,
            "salt": "demo",
            "rules": [],
        },
    )
    assert updated.status_code == 200, updated.text
    key = client.post(
        "/orgs/acme/applications/shop/environments/production/keys",
        headers=headers,
        json={"name": "server"},
    )
    assert key.status_code == 201, key.text
    return {"Authorization": f"Bearer {key.json()['token']}"}


def test_rollout_and_tenant_isolation(client):
    owner = client.post("/auth/register", json={"email": "ada@acme.com", "name": "Ada", "password": "correct-horse"})
    assert owner.status_code == 201
    headers = {"Authorization": f"Bearer {owner.json()['access_token']}"}
    token = client.post("/auth/token", data={"username": "ada@acme.com", "password": "correct-horse"})
    assert token.status_code == 200
    sdk = _setup(client, headers)

    first = client.post("/sdk/v1/evaluate", headers=sdk, json={"user": {"key": "user-1"}, "flag": "payment"})
    second = client.post("/sdk/v1/evaluate", headers=sdk, json={"user": {"key": "user-1"}, "flag": "payment"})
    assert first.status_code == 200
    assert first.json() == second.json()
    assert first.json()["flag"] == "payment"

    stranger = client.post("/auth/register", json={"email": "bea@other.com", "name": "Bea", "password": "correct-horse"})
    other = {"Authorization": f"Bearer {stranger.json()['access_token']}"}
    hidden = client.get("/orgs/acme/applications", headers=other)
    assert hidden.status_code == 404

    turned_off = client.put(
        "/orgs/acme/applications/shop/flags/payment/environments/production",
        headers=headers,
        json={
            "enabled": False,
            "off_variation": "old",
            "fallthrough_variation": "new",
            "rollout_percent": 100,
            "salt": "demo",
            "rules": [],
        },
    )
    assert turned_off.status_code == 200
    disabled = client.post("/sdk/v1/evaluate", headers=sdk, json={"user": {"key": "user-1"}, "flag": "payment"})
    assert disabled.json()["reason"] == "off"
    assert disabled.json()["value"] is False

    audit = client.get("/orgs/acme/audit", headers=headers)
    assert audit.status_code == 200
    assert any(row["action"] == "flag.update" for row in audit.json())


def test_oidc_is_refused_until_it_is_configured(client):
    response = client.post("/auth/oidc", json={"id_token": "not-a-token"})
    assert response.status_code == 503


def test_events_are_accepted(client):
    headers = client.post(
        "/auth/register", json={"email": "ada@acme.com", "name": "Ada", "password": "correct-horse"}
    )
    sdk = _setup(client, {"Authorization": f"Bearer {headers.json()['access_token']}"}, rollout=100)
    accepted = client.post(
        "/sdk/v1/events",
        headers=sdk,
        json={"events": [{"flag": "payment", "user_key": "user-1", "variation": "new", "reason": "rollout"}]},
    )
    assert accepted.status_code == 202
    assert accepted.json() == {"accepted": 1}


def test_home_page(client):
    page = client.get("/")
    assert page.status_code == 200
    assert "Hello" in page.text
