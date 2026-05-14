# AE Dashboard — Frontend (React + Tailwind + TanStack)

## Local dev

```bash
npm install
npm run dev
```

Vite dev server runs on `:5173` and proxies `/api/*` to `http://localhost:8000` (the FastAPI backend).

## Build

```bash
npm run build
```

Produces `dist/` for the nginx container to serve.

## Type-check & test

```bash
npm run typecheck
npm run test
```
