# Architecture

Beacon separates two jobs. People change configuration through the management API. Applications read a snapshot and evaluate it.

## Evaluation

A flag in an environment is either off or on. Off always returns the off variation. On walks the targeting rules in order. A rule matches when every clause matches the user, including membership of a named segment. A rule may also carry a rollout. A user who misses that percentage falls through to the next rule.

If no rule matches, the environment rollout decides. The bucket is `SHA-256(flag, salt, user key) mod 10000`. Five percent means the first 500 buckets. The same user key always lands in the same bucket, so a gradual release does not reshuffle the audience when the process restarts.

## Cache

The snapshot for one environment is stored under `beacon:env:{id}`. A configuration write deletes that key after the database commit. The next evaluation rebuilds the snapshot and stores it again. With `REDIS_URL` set, every API process shares Redis. Without it, the process keeps the snapshot in memory.

The SDK does not query Postgres. It downloads the snapshot and evaluates locally, and it refreshes on a timer. Repeated flag checks do not become repeated database reads.

## Tenancy

An organisation, its applications, environments, flags, segments, and SDK keys are one tenant. A request for another organisation's slug returns the same `404` as a missing organisation. An SDK key is bound to one environment, and the token is stored only as a SHA-256 hash.

## Failure

Evaluation itself does not write a row. Event recording is a separate call, so a slow audit insert cannot sit on the flag check. If the configuration service is down, an SDK that already holds a snapshot keeps serving it and marks the answer stale. An SDK that has never loaded a snapshot fails closed instead of guessing.

## Authentication

Dashboard and management calls use an OAuth2 password grant. `POST /auth/token` accepts the form fields `username` and `password` and returns a signed JWT. When an OIDC issuer, audience, and JWKS URL are configured, `POST /auth/oidc` checks an identity-provider token and then issues the same kind of JWT. Sentry receives errors and traces only when a DSN is present.

## Storage

Postgres is the shared database. Alembic migration `0001` creates the tables. Useful indexes are the unique application and flag keys, the SDK token hash, and the time indexes on audit rows and evaluation events (`organisation_id, created_at` and `environment_id, created_at`). The API uses a SQLAlchemy pool against Postgres. SQLite is the single-process default so the demo and the tests can run without a server.
