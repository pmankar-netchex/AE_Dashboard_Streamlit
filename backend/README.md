# AE Dashboard — Backend (FastAPI)

## Local dev

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp ../.env.example .env  # then edit
uvicorn app.main:app --reload --port 8000
```

`GET /healthz` → liveness.
`GET /api/me` → returns the dev user from `DEV_ROLE` + `DEV_USER_EMAIL` when `ENV=dev`.

## Tests

```bash
pytest
```

## Env vars

See `../.env.example` for the full list. In dev, auth is bypassed and identity comes from `DEV_ROLE` / `DEV_USER_EMAIL`. In prod, the API trusts the `X-MS-CLIENT-PRINCIPAL` header forwarded by Container Apps Easy Auth on the UI container.
