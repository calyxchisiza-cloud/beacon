import os

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["JWT_SECRET"] = "demo-secret-with-at-least-32-bytes"
os.environ["REDIS_URL"] = ""

from fastapi.testclient import TestClient

from app.main import app
from beacon_core.eval import evaluate_flag


def main() -> None:
    with TestClient(app) as client:
        owner = client.post("/auth/register", json={"email": "ada@acme.com", "name": "Ada", "password": "correct-horse"})
        headers = {"Authorization": f"Bearer {owner.json()['access_token']}"}
        client.post("/orgs", headers=headers, json={"name": "Acme", "slug": "acme"})
        client.post("/orgs/acme/applications", headers=headers, json={"key": "shop", "name": "Shop"})
        client.post(
            "/orgs/acme/applications/shop/environments",
            headers=headers,
            json={"key": "production", "name": "Production"},
        )
        client.post(
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
        client.put(
            "/orgs/acme/applications/shop/flags/payment/environments/production",
            headers=headers,
            json={
                "enabled": True,
                "off_variation": "old",
                "fallthrough_variation": "new",
                "rollout_percent": 5,
                "salt": "demo",
                "rules": [],
            },
        )
        spec = {
            "key": "payment",
            "enabled": True,
            "off": "old",
            "fallthrough": "new",
            "salt": "demo",
            "rollout": 500,
            "rules": [],
            "variations": {"old": False, "new": True},
        }
        enabled = disabled = None
        index = 0
        while enabled is None or disabled is None:
            key = f"user-{index}"
            result = evaluate_flag(spec, {"key": key, "attributes": {}})
            if result["variation"] == "new" and enabled is None:
                enabled = key
            if result["variation"] == "old" and disabled is None:
                disabled = key
            index += 1
        print(f"payment {enabled} enabled")
        print(f"payment {disabled} disabled")


if __name__ == "__main__":
    main()
