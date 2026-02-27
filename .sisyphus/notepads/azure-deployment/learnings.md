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

## [2026-02-26] Task 7: Azure DevOps CI/CD Pipeline (azure-pipelines.yml)

### Completed
- ✅ Created `azure-pipelines.yml` at project root (82 lines)
- ✅ Trigger: `branches.include: [main]`
- ✅ Build stage: `Docker@2` task with `buildAndPush` command
- ✅ Deploy stage: `AzureWebAppContainer@1` task with `deployment` job type (enables environments)
- ✅ `dependsOn: Build` + `condition: succeeded()` on Deploy stage
- ✅ Zero hardcoded values — all pipeline variable references `$(VAR_NAME)`
- ✅ Header comment block documents all 6 required pipeline variables
- ✅ YAML syntax valid (python3 yaml.safe_load ✓)
- ✅ Evidence saved to `.sisyphus/evidence/task-7/`
- ✅ Committed: `da7860e feat(ci): add Azure DevOps pipeline`

### Key Implementation Decisions

**ACR URL approach:**
- Used `ACR_LOGIN_SERVER` as explicit pipeline variable (e.g., `aedashboard.azurecr.io`)
- `containers` input: `$(acrLoginServer)/$(acrRepository):$(Build.BuildId)`
- This is cleaner than relying on `$(containerRegistry.loginServer)` which is not guaranteed by all service connection types

**`deployment` job vs regular `job`:**
- Deploy stage uses `deployment:` job type — this enables Azure DevOps environments + optional approval gates
- Strategy: `runOnce.deploy.steps` (required structure for deployment jobs)
- `environment: 'production'` — creates/uses the "production" environment in Azure DevOps

**Image tagging:**
- Both `$(Build.BuildId)` and `latest` tags pushed
- Deploy uses `$(Build.BuildId)` specifically — ensures exact build deployed (not ambiguous "latest")

**Variable block pattern:**
- Variables block maps short names (e.g., `acrServiceConnection`) to pipeline var refs (e.g., `$(ACR_SERVICE_CONNECTION)`)
- Inline comments explain purpose — helps pipeline editors understand without reading docs
- `resourceGroupName` variable defined but not directly used in pipeline tasks (informational, available for future steps)

### QA Results
- YAML valid: Stages: 2 ✓
- Triggers on main: PASS ✓
- Deploy depends on Build: PASS ✓
- No hardcoded Azure URLs in pipeline values: PASS ✓
  (`.azurecr.io` appears only in inline comments as examples, not as actual values)

### Required Pipeline Variables (set in Azure DevOps UI)
1. `ACR_SERVICE_CONNECTION` — Docker Registry service connection name for ACR
2. `AZURE_SERVICE_CONNECTION` — Azure Resource Manager service connection name
3. `ACR_LOGIN_SERVER` — ACR hostname (e.g., `aedashboard.azurecr.io`)
4. `ACR_REPOSITORY` — repository name within ACR (e.g., `ae-dashboard`)
5. `APP_NAME` — Azure App Service name
6. `RESOURCE_GROUP_NAME` — Resource group containing the App Service

### Dependency Chain
- Task 5 (Dockerfile) ✅ — `Docker@2` builds from `$(Build.SourcesDirectory)/Dockerfile`
- Task 6 (deploy.ps1) ✅ — infrastructure separate; this pipeline only handles CI/CD
- Task 3 (main.bicep) ✅ — ACR and App Service must be provisioned before pipeline can run

## [2026-02-26] F4: Scope Fidelity Check

### Summary
Final QA scope check — all 6 forbidden files untouched, all 9 planned files present, VERDICT: APPROVE.

### Findings
- **Forbidden files**: All 6 source files (streamlit_dashboard.py, src/salesforce_oauth.py, src/msal_auth.py,
  src/salesforce_queries.py, src/dashboard_calculations.py, src/dashboard_ui.py) had zero commits touching
  them since baseline 599c8be. Scope discipline was perfect.

- **Planned files all present**: 7 new files (Dockerfile, .dockerignore, .streamlit/config.toml,
  infra/main.bicep, infra/main.json, scripts/deploy.ps1, azure-pipelines.yml) + 2 modified
  (src/token_storage.py, requirements.txt). All 9/9 accounted for.

- **Unaccounted files**: Only `.sisyphus/` QA artifacts and `.gitignore` (planned side-effect of Task 1).
  Zero unplanned source-code changes.

- **Commit-level audit**: Each of the 7 commits touched only files appropriate to their task.
  Sisyphus QA evidence files (.sisyphus/evidence/task-N/) were bundled into implementation commits
  rather than separate commits — acceptable but worth noting for future plans.

### Pattern: .sisyphus/ artifacts in implementation commits
Tasks 4, 6, and 7 bundled their QA evidence files into the same commit as the implementation.
This is fine from a scope perspective but slightly inflates what `git diff --name-only` shows.
Future scope checks should explicitly exclude `.sisyphus/` from unaccounted-file analysis.

### Methodology Used
- `git log --oneline 599c8be..HEAD -- <file>` per forbidden file (clean = CLEAN)
- `ls -la` to verify new files present
- `git diff --name-only 599c8be HEAD` for full diff list
- `git show --stat <commit>` for each of the 7 commits
- Evidence saved to: `.sisyphus/evidence/final-qa/F4-scope.txt`

## [2026-02-26] F1: Plan Compliance Audit

### Audit Result: APPROVE (36/36 checks passed)

**Must Have:** 10/10 PASS
**Must NOT Have:** 13/13 PASS
**Deliverables:** 8/8 PASS
**Definition of Done:** 5/5 PASS

### Key Findings

1. **MNH8-10 interpretation**: `git log --oneline -- <file>` shows pre-baseline commits (599c8be, 3f0b43c) for some files — these predate the azure-deployment task series. The correct check is `git log --oneline 599c8be..HEAD -- <file>` to isolate azure-deployment task commits. Zero azure-deployment commits touched any protected source file.

2. **MH1 pattern**: Dockerfile uses `COPY . .` (not selective copy), making `.dockerignore` the critical control for `.env` exclusion. Both Dockerfile and .dockerignore correctly implement this.

3. **DoD2 BCP334 warning**: `az bicep build` exits 0 with a non-fatal WARNING BCP334 about ACR name minimum length. This is expected behavior noted in inherited wisdom — not a failure.

4. **DoD3 PASS pattern**: `python3 -c "... from src.token_storage import load_tokens; result = load_tokens(); print('PASS:', result)"` outputs `PASS: {}` — empty dict because no tokens are saved in test env, but no crash = filesystem fallback works correctly.

5. **MNH2-6 verification**: Empty grep output = PASS for "no forbidden resources" checks. Confirmed infra/main.bicep contains ONLY the 5 expected resources: App Service Plan, App Service, ACR, Key Vault, AcrPull role assignment.

6. **All 7 azure-deployment commits confirmed**: 2c0c51c → b2c0890 → b057058 → 51d1455 → b466e86 → 07baea4 → da7860e

### Evidence file
`.sisyphus/evidence/final-qa/F1-compliance.txt` (221 lines, full audit with per-check evidence)

## [2026-02-26] F2: Code Quality Review

### All 6 Checks PASSED — VERDICT: APPROVE

**Results Summary:**
- Bicep [PASS] — `az bicep build` exit code 0; BCP334 warning (known, ACR name length) is non-blocking
- Python [PASS] — `from src.token_storage import save_tokens, load_tokens, clear_tokens` succeeds without KEY_VAULT_NAME; `load_tokens()` returns `dict`
- PowerShell [PASS] — `Parser::ParseFile` reports 0 errors for `scripts/deploy.ps1` (442 lines)
- YAML [PASS] — `yaml.safe_load` succeeds; stages count = 2 (Build + Deploy)
- Dockerignore [PASS] — `.env`, `.git/`, `venv/`, `__pycache__/` all present; `src/` correctly NOT excluded
- Secrets Scan [CLEAN] — no credential literals; initial grep matched Streamlit widget `key=` params (false positives)

### Key Insights

1. **PowerShell Parser AST dump**: `[Parser]::ParseFile(...)` returns the parsed AST object; without `$null = ...` assignment, it dumps the entire script AST to stdout. Always assign: `$null = [System.Management.Automation.Language.Parser]::ParseFile(...)` to suppress.

2. **Secrets scan false positives**: The pattern `key\s*=\s*"[^"]{8,}"` matches Streamlit widget `key=` parameters (e.g., `key="filter_month"`). These are UI component identifiers, NOT credentials. A second pass with `| grep -v 'key="'` confirms CLEAN.

3. **Bicep BCP334**: Warning about ACR name length (minimum 5 chars) is expected when `appName` is short. Exit code is still 0, so this is PASS. The `acrName` variable strips hyphens from `appName` and appends `'acr'`, which may produce short names for short `appName` values.

4. **Dockerfile**: No `COPY .env` present (verified). ENTRYPOINT is exec form array. HEALTHCHECK uses `/_stcore/health` Streamlit built-in endpoint.

5. **YAML hardcoded values**: `azure-pipelines.yml` contains `.azurecr.io` only in comment lines (line 15-16 as examples). All actual pipeline values use `$(VARIABLE)` references. Pipeline is fully parameterized.

6. **Bicep scope**: No explicit `targetScope` in `main.bicep` = defaults to `resourceGroup`. This is correct for the deployment pattern used (`az deployment group create`).

### Evidence Location
`.sisyphus/evidence/final-qa/F2-quality.txt`
