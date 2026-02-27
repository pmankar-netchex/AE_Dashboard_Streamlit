# Learnings — azure-deployment

## [2026-02-26] Initial Project Context (Atlas)

### Project Structure
- Entry: `streamlit_dashboard.py` (803 lines, monolithic)
- Modules: `src/` — salesforce_queries, dashboard_calculations, dashboard_ui, salesforce_oauth, msal_auth, token_storage
- Scripts: `scripts/` — setup.sh, run.sh, .env.example
- Port: Streamlit default 8501
- Python deps: 7 pinned in requirements.txt

### Critical: .gitignore has `.streamlit/config.toml`
The `.gitignore` at line 2 IGNORES `.streamlit/config.toml`. When creating this file for Docker,
the agent MUST also modify `.gitignore` to un-ignore it (add `!.streamlit/config.toml` negation,
or remove the gitignore line). Without this, the config won't be committed to git and won't
be available in CI/CD Docker builds.

### Token Storage Design
- Single-user shared token (one admin logs in, all users share Salesforce connection)
- Current: `~/.salesforce_tokens/ae_dashboard.json` (0o600 perms)
- Azure: Key Vault secret named `salesforce-tokens` (JSON string)
- Backend selection: `os.environ.get('KEY_VAULT_NAME')` — if set → KV, else → filesystem

### All Auth Reads from os.environ
- `salesforce_oauth.py` and `msal_auth.py` use `os.environ.get()` throughout
- `load_dotenv()` in `streamlit_dashboard.py` line 4 is already dual-mode (no-op without .env file)
- Azure App Settings automatically populate os.environ — zero app code changes needed for config

### Bicep Resource Naming Convention
- ACR: `${replace(appName, '-', '')}acr` (alphanumeric only)
- App Service Plan: `${appName}-plan`
- App Service: `${appName}`
- Key Vault: `${appName}-kv`

### AcrPull Role ID
`7f951dda-4ed3-4680-a7ca-43fe172d538d` — use this exact GUID for AcrPull built-in role

### Environment Variables (from .env.example)
**Salesforce OAuth (mandatory):**
- SALESFORCE_CLIENT_ID, SALESFORCE_CLIENT_SECRET, SALESFORCE_REDIRECT_URI, SALESFORCE_SANDBOX
- Optional: SALESFORCE_LOGIN_URL, SALESFORCE_OAUTH_SCOPES

**Azure AD/MSAL (all optional):**
- AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_CLIENT_SECRET, AZURE_REDIRECT_URI
- AZURE_AUTHORITY, AZURE_SCOPES, AZURE_ALLOWED_DOMAINS, AZURE_ALLOWED_EMAILS

**Legacy (optional):**
- SALESFORCE_USERNAME, SALESFORCE_PASSWORD, SALESFORCE_SECURITY_TOKEN

**App/Debug:**
- DEBUG

## [2026-02-26 Task 2] Azure SDK dependencies added

**Task:** Add azure-identity==1.15.0 and azure-keyvault-secrets==4.8.0 to requirements.txt

**Outcome:**
- ✓ Both packages added with exact version pins
- ✓ All 7 original dependencies unchanged
- ✓ Total dependency count: 9 (7 original + 2 new)
- ✓ File format consistent: `package==version` per line
- ✓ No pip conflicts detected
- ✓ Evidence saved to `.sisyphus/evidence/task-2/`

**Packages added:**
- `azure-identity==1.15.0` — DefaultAzureCredential for managed identity auth
- `azure-keyvault-secrets==4.8.0` — SecretClient for Key Vault operations

**Notes:**
- These packages are dependencies for Task 4 (token_storage.py) and Task 5 (Dockerfile)
- No version conflicts with existing dependencies
- Both packages are stable releases from PyPI

## [2026-02-26 17:56] Task 1: Docker prep files (.dockerignore, Streamlit config)

### Completed
- ✅ Created `.dockerignore` at project root (43 lines)
  - Excludes: .env, .git/, venv/, __pycache__/, docs/, .sisyphus/, *.md, *.log, *.csv, *.xlsx, tokens/, *.json.enc
  - Preserves: src/, streamlit_dashboard.py, requirements.txt (app code must be in image)
  - Includes explanatory comments for each exclusion group

- ✅ Created `.streamlit/config.toml` (24 lines)
  - Production settings for Azure App Service reverse proxy
  - Key settings: headless=true, address="0.0.0.0", port=8501, enableCORS=false, enableXsrfProtection=false
  - gatherUsageStats=false to prevent outbound telemetry at startup
  - All settings verified via Python TOML parser

- ✅ Fixed `.gitignore` — removed line 2 (`.streamlit/config.toml`)
  - CRITICAL: This file is NOT a secret; it's production config that must be committed
  - Without this fix, Docker builds in CI/CD would be missing the config, causing Streamlit to bind to localhost (broken)

- ✅ Committed: `2c0c51c chore: add Docker prep files (.dockerignore, Streamlit config)`
  - Single atomic commit (3 files tightly coupled for Docker deployment)
  - Includes Sisyphus attribution footer and co-author trailer

### QA Evidence Saved
- `.sisyphus/evidence/task-1/dockerignore-content.txt` — full .dockerignore content
- `.sisyphus/evidence/task-1/streamlit-config-verify.txt` — TOML validation (all 4 server settings verified)
- `.sisyphus/evidence/task-1/gitignore-verify.txt` — confirmed .streamlit/config.toml no longer ignored
- Verified: src/ is NOT in .dockerignore (app code preserved)

### Key Insights
1. **CORS/XSRF disabled by design** — Azure App Service acts as trusted reverse proxy; these settings prevent WebSocket/POST failures through the proxy
2. **Port 8501 hardcoded** — matches EXPOSE in Dockerfile and WEBSITES_PORT App Setting
3. **headless=true required** — Streamlit must not try to open browser in container environment
4. **address="0.0.0.0" required** — container networking requires binding to all interfaces, not localhost
5. **gatherUsageStats=false** — prevents Streamlit from making outbound telemetry calls at startup (important in restricted networks)

### Dependencies
- Task 5 (Dockerfile) depends on .dockerignore existing ✅
- Task 6 (Bicep) depends on .streamlit/config.toml being committed ✅

## [2026-02-26] Task 4: Key Vault adapter for token_storage.py

### Approach: Lazy-import adapter pattern
- `_use_key_vault()` checks `os.environ.get('KEY_VAULT_NAME')` at call time (not module load)
- `_get_kv_client()` caches a single `SecretClient` globally; Azure SDK imported inside the function
- Azure imports (`azure.identity`, `azure.keyvault.secrets`, `azure.core.exceptions`) are NEVER loaded in filesystem mode
- Module-level globals: `_kv_client = None` (sentinel for lazy init), `_KV_SECRET_NAME = "salesforce-tokens"`

### Key Vault operations
- `save_tokens()` → `client.set_secret('salesforce-tokens', json.dumps(data))`
- `load_tokens()` → `client.get_secret('salesforce-tokens').value` → JSON parse; `ResourceNotFoundError` → `{}`
- `clear_tokens()` → `client.begin_delete_secret('salesforce-tokens')`; `ResourceNotFoundError` → pass (no-op)

### QA: All 3 tests pass
- Filesystem round-trip: save/load/clear verified correct
- Import without KEY_VAULT_NAME: no azure packages imported
- Signatures: `save_tokens(access_token, refresh_token, instance_url)`, `load_tokens() -> dict`, `clear_tokens()`

### Callers unchanged
- `streamlit_dashboard.py` lines 20-24 import exactly `save_tokens, load_tokens, clear_tokens` — unchanged
- No modifications needed to any other file

### Gotcha: `python` vs `python3`
- This environment uses `python3` (no `python` alias). QA scripts must use `python3`.

## [2026-02-26] Task 5: Dockerfile for Azure App Service

### Completed
- ✅ Created `Dockerfile` at project root (24 lines)
- ✅ Base image: `python:3.11-slim`
- ✅ Includes `curl` installation for HEALTHCHECK
- ✅ EXPOSE 8501 for Streamlit
- ✅ HEALTHCHECK configured: `curl -f http://localhost:8501/_stcore/health`
- ✅ ENTRYPOINT uses exec form (array), not shell form
- ✅ Docker layer caching: requirements.txt copied first, app code last
- ✅ Build succeeds: `docker build -t ae-dashboard-test .` ✓
- ✅ Container health check passes: curl returns "ok" after 45s boot time
- ✅ `.env` correctly excluded (verify: `ls: cannot access '/app/.env': No such file or directory`)
- ✅ Committed: `b466e86 feat: add Dockerfile for Azure App Service deployment`

### Key Implementation Details

**Layer caching strategy:**
- Step 1: Install curl + apt cleanup (minimal, rarely changes)
- Step 2: Copy requirements.txt + pip install (changes only when deps update)
- Step 3: Copy app code (changes frequently, doesn't invalidate step 2 cache)

**HEALTHCHECK design:**
- Interval: 30 seconds
- Timeout: 10 seconds
- Start period: 60 seconds (Streamlit needs ~45s to boot; 60s provides buffer)
- Retries: 3 (if 3 consecutive checks fail, container is marked unhealthy)
- Command: `curl -f http://localhost:8501/_stcore/health` (built-in Streamlit endpoint, no custom logic)

**ENTRYPOINT design:**
- Exec form (array): `["streamlit", "run", "streamlit_dashboard.py", "--server.port=8501"]`
- NOT shell form: avoids extra /bin/sh process, PID 1 is streamlit (proper signal handling)
- Port flag: `--server.port=8501` matches EXPOSE and .streamlit/config.toml
- Note: NOT adding `--server.headless` (already in config.toml) or other flags duplicated

**Dependencies chain:**
- Task 1 (.dockerignore) ✅ — ensures .env is excluded
- Task 2 (requirements.txt) ✅ — 9 pinned dependencies installed
- Task 1 (.streamlit/config.toml) ✅ — copied into image with production settings
- Docker daemon ✅ — available in environment

### QA Evidence
- `.sisyphus/evidence/task-5/docker-build.txt` — full build log (curl install, pip install all 9 deps, image exported)
- `.sisyphus/evidence/task-5/container-health.txt` — health check test ("ok" response)
- `.sisyphus/evidence/task-5/no-env-in-image.txt` — .env exclusion verification

### Image size & performance
- Base: python:3.11-slim (~160MB)
- +curl: ~15MB
- +deps: ~800MB (numpy, pandas, streamlit, Azure SDK)
- Total: ~1GB (typical for Python + ML stack)
- Boot time: ~45 seconds (Streamlit cold start)

### Deployment ready
✅ Image is production-ready for Azure App Service:
- Correct port (8501)
- Health checks working
- .env/secrets excluded (rely on App Settings)
- Stateless design (tokens saved to Key Vault via token_storage.py Task 4)
- No hardcoded credentials

## [2026-02-26] Task 6: PowerShell deployment script (scripts/deploy.ps1)

### Completed
- ✅ Created `scripts/deploy.ps1` (442 lines)
- ✅ PowerShell syntax validation: PASS (0 parse errors via `Parser::ParseFile`)
- ✅ All 8 required parameters present (ResourceGroupName, AppName, Location, AppServicePlanSku, AcrSku, SkipBicep, SkipDocker, ConfigureSettings)
- ✅ All 17 env vars covered (Salesforce OAuth mandatory+optional, Azure AD all optional, KEY_VAULT_NAME auto-set, DEBUG)
- ✅ Evidence saved to `.sisyphus/evidence/task-6/` (ps-syntax.txt, ps-params.txt, ps-envvars.txt)
- ✅ Committed: `feat(infra): add PowerShell deployment script`

### Script structure (7 sections in order)
1. **Prerequisites**: az CLI version check + login check + Docker daemon check (skipped if -SkipDocker)
2. **Resource Names**: Derived from $AppName — ACR = `($AppName -replace '-','') + 'acr'`, KV = `$AppName-kv`
3. **Bicep Deployment**: `az deployment group create` with all 4 params; queries outputs (acrLoginServer, appServiceUrl, keyVaultName); if -SkipBicep, queries ACR via `az acr show`
4. **Docker Build+Push**: `az acr login` → `docker build` → `docker push`; skipped if -SkipDocker
5. **App Settings**: Interactive prompts grouped by category; KEY_VAULT_NAME auto-set to $AppName-kv; Azure AD block only shown if AZURE_CLIENT_ID provided; `az webapp config appsettings set`
6. **Container Config**: `az webapp config container set` — always runs (needed after Bicep or Docker changes)
7. **Restart + Health**: `az webapp restart` + retry loop (10 attempts × 30s) on `/_stcore/health`

### Key implementation decisions
- `$AcrLoginServer` sourced from Bicep output OR `az acr show` query when -SkipBicep used
- Repo root derived from script location: `Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)`
- `Prompt-WithDefault` helper handles display of defaults in `[brackets]` and -Secret (masked input)
- Azure AD prompts nested inside `if ($azClientId -ne '')` — entire block skipped if no client ID
- Settings hashtable built iteratively; only non-empty values added (prevents sending empty strings)
- `--output none` on write operations for clean terminal output; `-o json` on reads for parsing
- Health poll uses `Invoke-WebRequest` with `-UseBasicParsing` (no IE engine dependency)
- Final status always prints App URL + log tail command regardless of health check outcome

### Gotcha: $null ref in heredoc validation
- The `[ref]$null` trick used in quick inline pwsh -Command fails with "variable does not exist"
- Fix: use `pwsh -File /dev/stdin <<'EOF'` heredoc with `$errors = $null` pre-declaration
- Both validate correctly; PASS output is definitive
