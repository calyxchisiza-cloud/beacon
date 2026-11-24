# Beacon

Beacon lets an application turn a feature on or off without a new deploy. A flag has variations, an environment, and rules. Evaluation is deterministic: the same user stays inside or outside a percentage rollout.

A five percent rollout of `payment` prints:

```text
payment user-3 enabled
payment user-0 disabled
```

`user-3` receives the new variation. `user-0` stays on the old one. Running the demo again keeps those same two results.

## Run

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe demo.py
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000
```

The local default database is a SQLite file, `beacon.db`. Redis is optional. With `REDIS_URL` empty, the process keeps the environment snapshot in memory.

Postgres, Redis, and the API together:

```powershell
docker compose up --build
```

The API listens on `127.0.0.1:8000`. Interactive docs are at `http://127.0.0.1:8000/docs`.

## API

1. `POST /auth/register` or `POST /auth/token` with a form username and password. The token is a JWT.
2. Create an organisation, an application, and an environment such as `production`.
3. Create a flag and `PUT` its environment configuration, including `rollout_percent`.
4. Create an SDK key. The plaintext token is returned once.
5. `POST /sdk/v1/evaluate` with `Authorization: Bearer <sdk key>` and a user key.

`GET /sdk/v1/flags` returns the snapshot an SDK can evaluate on its own. `POST /sdk/v1/events` records evaluations. `GET /orgs/{slug}/audit` lists configuration changes.

Another organisation receives `404` for a slug it does not belong to.

OIDC login is `POST /auth/oidc`. It stays disabled until `OIDC_ISSUER`, `OIDC_AUDIENCE`, and `OIDC_JWKS_URL` are set. Sentry starts only when `SENTRY_DSN` is set.

## SDK

```python
from sdk.beacon import Client

client = Client("http://127.0.0.1:8000", sdk_key)
result = client.variation("payment", "user-3")
```

The client keeps the last snapshot. If the service cannot be reached, it evaluates that snapshot and marks the result stale. It does not invent a configuration it has never seen.

## Load

`locustfile.py` posts evaluations. Set `BEACON_SDK_KEY` and point Locust at the API:

```powershell
$env:BEACON_SDK_KEY = "bk_..."
.\.venv\Scripts\locust.exe -f locustfile.py --host http://127.0.0.1:8000
```
