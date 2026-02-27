# Azure Deployment — AE Dashboard

## TL;DR

> **Quick Summary**: Containerize the Streamlit AE Dashboard for Azure App Service with full IaC (Bicep), a local PowerShell deployment script, and an Azure DevOps CI/CD pipeline. Includes Key Vault integration for Salesforce token persistence and production-ready Streamlit configuration.
>
> **Deliverables**:
> - `Dockerfile` + `.dockerignore` + `.streamlit/config.toml` (containerization)
> - `infra/main.bicep` (App Service, ACR, Key Vault, managed identity)
> - `scripts/deploy.ps1` (PowerShell local deployment)
> - `azure-pipelines.yml` (Azure DevOps CI/CD)
> - Modified `src/token_storage.py` (Key Vault adapter with filesystem fallback)
> - Updated `requirements.txt` (Azure SDK dependencies)
>
> **Estimated Effort**: Medium
> **Parallel Execution**: YES — 3 waves + final verification
> **Critical Path**: Task 1,2 → Task 5 → Task 7 → Final Verification

---

## Context

### Original Request
Deploy the existing Streamlit AE Dashboard to Azure. Need Bicep IaC for infrastructure, a PowerShell deployment script for local use, and an Azure DevOps YAML pipeline for CI/CD. All configuration and secrets managed through Azure App Service Application Settings.

### Interview Summary
**Key Discussions**:
- **Token storage**: Azure Key Vault replaces local filesystem (`~/.salesforce_tokens/`). Managed identity for credential-free access. Adapter pattern — same function signatures, backend chosen by `KEY_VAULT_NAME` env var.
- **Environments**: Production only. Single resource group (existing). Bicep parameterizes the RG name.
- **Pipeline**: Azure DevOps YAML, triggers on push to main. Build Docker → push to ACR → deploy to App Service.
- **Config loading**: `load_dotenv()` already works as dual-mode (loads .env locally, no-op on Azure). No code changes needed for this.
- **OAuth redirects**: Already env-var-driven (`SALESFORCE_REDIRECT_URI`, `AZURE_REDIRECT_URI`). Set correct URLs in App Settings.

**Research Findings**:
- No `.streamlit/config.toml` exists — **deployment blocker**. Streamlit defaults to `headless=false` and `address=localhost`, which won't work in a container behind Azure's reverse proxy.
- WebSockets must be explicitly enabled on App Service (`webSocketsEnabled: true`) — Streamlit's reactive model depends on them.
- Default App Service container startup timeout is 230s — may be tight with pandas + azure-identity cold starts. Need `WEBSITES_CONTAINER_START_TIME_LIMIT=300`.
- `load_dotenv()` with no `.env` file = no-op (verified). `load_dotenv(override=False)` is the default — won't override App Settings even if .env somehow existed.
- Only filesystem writes in entire codebase are in `token_storage.py` (confirmed via grep).
- OAuth callback works behind reverse proxy — code+state discrimination is parameter-based, not path-based.

### Metis Review
**Identified Gaps** (addressed):
- **Missing `.streamlit/config.toml`**: Added as Task 1 — headless mode, 0.0.0.0 binding, CORS/XSRF disabled for reverse proxy
- **Missing `.dockerignore`**: Added as Task 1 — prevents .env, .git, venv from entering Docker image
- **WebSockets not enabled**: Added to Bicep App Service config (Task 3)
- **Container startup timeout**: Added `WEBSITES_CONTAINER_START_TIME_LIMIT=300` to Bicep (Task 3)
- **ACR missing from plan**: Added to Bicep template with managed identity AcrPull role (Task 3)
- **Key Vault secret-not-found edge case**: Specified in Task 4 — mirror filesystem behavior (return `{}`)
- **Single-user token design**: Confirmed via code analysis — one shared token set. Key Vault stores one secret, not per-user.

---

## Work Objectives

### Core Objective
Make the AE Dashboard deployable to Azure App Service with infrastructure-as-code, automated CI/CD, and secure secret management — while keeping local development workflow unchanged.

### Concrete Deliverables
- `Dockerfile` — containerizes the Streamlit app
- `.dockerignore` — excludes secrets and dev files from Docker context
- `.streamlit/config.toml` — production Streamlit settings for reverse proxy
- `infra/main.bicep` — full Azure infrastructure (App Service Plan, App Service, ACR, Key Vault, managed identity, role assignments)
- `scripts/deploy.ps1` — PowerShell script for local deployment to Azure
- `azure-pipelines.yml` — Azure DevOps CI/CD pipeline
- Modified `src/token_storage.py` — Key Vault adapter pattern with filesystem fallback
- Updated `requirements.txt` — adds `azure-identity`, `azure-keyvault-secrets`

### Definition of Done
- [ ] `docker build -t ae-dashboard .` succeeds
- [ ] `docker run -p 8501:8501 ae-dashboard` starts and `curl http://localhost:8501/_stcore/health` returns `ok`
- [ ] `az bicep build --file infra/main.bicep` succeeds (valid Bicep syntax)
- [ ] `token_storage.py` works without `KEY_VAULT_NAME` (filesystem fallback for local dev)
- [ ] All env vars from `.env.example` are documented in deploy script as App Settings
- [ ] Pipeline YAML is syntactically valid

### Must Have
- All configuration via Azure App Service Application Settings (not .env files in container)
- Key Vault for Salesforce token persistence with managed identity access
- Docker container on Linux App Service
- ACR for container image storage
- PowerShell deployment script that handles end-to-end: Bicep deploy + Docker build/push + App Settings
- Azure DevOps pipeline triggered on push to main
- Local dev workflow unchanged (load_dotenv + filesystem tokens still work)
- WebSockets enabled on App Service
- HTTPS-only enforced
- Health check configured at `/_stcore/health`

### Must NOT Have (Guardrails)
- **No multi-user token storage** — maintain single shared Salesforce token design
- **No custom domains or SSL certificates** — use `*.azurewebsites.net` with default SSL
- **No Application Insights or monitoring** — use built-in App Service logs only
- **No deployment slots** — single slot, accept brief downtime on deploy
- **No auto-scaling rules** — single instance, manual scaling if needed
- **No VNet, NSG, or Private Endpoints** — public App Service
- **No dependency upgrades** — keep existing pinned versions, only add new Azure packages
- **No changes to `streamlit_dashboard.py`** — `load_dotenv()` already works dual-mode
- **No changes to `salesforce_oauth.py` or `msal_auth.py`** — already env-var-driven
- **No changes to `salesforce_queries.py`, `dashboard_calculations.py`, or `dashboard_ui.py`**
- **No test infrastructure** — no tests exist, don't add any
- **No Streamlit secrets.toml** — App Settings only, don't mix secret sources
- **No removal of plotly from requirements.txt** — unused but out of scope

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: NO
- **Automated tests**: None (no test infrastructure in project)
- **Framework**: N/A

### QA Policy
Every task MUST include agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Docker/Container**: Use Bash — `docker build`, `docker run`, `curl` health check
- **Bicep/IaC**: Use Bash — `az bicep build` for syntax validation
- **PowerShell scripts**: Use Bash — `pwsh -Command "& { Get-Help ... }"` for syntax check
- **Python code**: Use Bash — `python -c "from src.token_storage import ..."` for import/functionality check
- **YAML pipeline**: Use Bash — `python -c "import yaml; yaml.safe_load(open('azure-pipelines.yml'))"` for syntax validation

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately — foundation, all independent):
├── Task 1: Docker prep files (.dockerignore + .streamlit/config.toml) [quick]
├── Task 2: Add Azure SDK dependencies to requirements.txt [quick]
├── Task 3: Bicep infrastructure template (infra/main.bicep) [unspecified-high]
└── Task 4: Key Vault adapter for token_storage.py [unspecified-high]

Wave 2 (After Wave 1 — containerization + deployment):
├── Task 5: Create Dockerfile (depends: 1, 2) [quick]
└── Task 6: PowerShell deployment script (depends: 3) [unspecified-high]

Wave 3 (After Wave 2 — CI/CD):
└── Task 7: Azure DevOps YAML pipeline (depends: 3, 5) [unspecified-high]

Wave FINAL (After ALL tasks — independent review, 4 parallel):
├── Task F1: Plan compliance audit (oracle)
├── Task F2: Code quality review (unspecified-high)
├── Task F3: Real QA — Docker build + container test (unspecified-high)
└── Task F4: Scope fidelity check (deep)

Critical Path: Task 1,2 → Task 5 → Task 7 → Final Verification
Parallel Speedup: ~50% faster than sequential
Max Concurrent: 4 (Wave 1)
```

### Dependency Matrix

| Task | Depends On | Blocks | Wave |
|------|-----------|--------|------|
| 1 | — | 5 | 1 |
| 2 | — | 4, 5 | 1 |
| 3 | — | 6, 7 | 1 |
| 4 | — | — | 1 |
| 5 | 1, 2 | 7 | 2 |
| 6 | 3 | — | 2 |
| 7 | 3, 5 | — | 3 |
| F1-F4 | ALL | — | FINAL |

### Agent Dispatch Summary

- **Wave 1**: **4 tasks** — T1 → `quick`, T2 → `quick`, T3 → `unspecified-high`, T4 → `unspecified-high`
- **Wave 2**: **2 tasks** — T5 → `quick`, T6 → `unspecified-high`
- **Wave 3**: **1 task** — T7 → `unspecified-high`
- **FINAL**: **4 tasks** — F1 → `oracle`, F2 → `unspecified-high`, F3 → `unspecified-high`, F4 → `deep`

---

## TODOs

> Implementation + verification = ONE Task. Every task has QA Scenarios.


- [ ] 1. Docker Prep Files (`.dockerignore` + `.streamlit/config.toml`)

  **What to do**:
  - Create `.dockerignore` at project root with exclusions: `.env`, `.env.local`, `.env.example`, `.git/`, `venv/`, `env/`, `ENV/`, `__pycache__/`, `*.pyc`, `*.py[cod]`, `data/`, `tokens/`, `*.log`, `.vscode/`, `.idea/`, `docs/`, `*.md` (except README), `.sisyphus/`
  - Create `.streamlit/config.toml` directory and file with production settings:
    - `[server]`: `headless = true`, `address = "0.0.0.0"`, `port = 8501`, `enableCORS = false`, `enableXsrfProtection = false`
    - `[browser]`: `gatherUsageStats = false`, `serverAddress = "0.0.0.0"`
    - `[theme]`: leave empty or omit (use Streamlit defaults)
  - CORS and XSRF disabled because the app runs behind Azure App Service's trusted reverse proxy
  - Add comments in both files explaining WHY each setting exists

  **Must NOT do**:
  - Do NOT create a `.streamlit/secrets.toml` — secrets go in App Settings only
  - Do NOT modify any existing files
  - Do NOT add theme customization to the Streamlit config

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Two small config files, no logic, just declarations
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `playwright`: No browser work needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 3, 4)
  - **Blocks**: Task 5 (Dockerfile depends on .dockerignore and .streamlit/config.toml existing)
  - **Blocked By**: None (can start immediately)

  **References** (CRITICAL):

  **Pattern References**:
  - `.gitignore` (project root) — Use as basis for `.dockerignore`, then add Docker-specific exclusions (`.git/`, `docs/`)

  **External References**:
  - Streamlit server config docs: `server.headless`, `server.enableCORS`, `server.enableXsrfProtection` are the critical settings for reverse proxy deployment

  **WHY Each Reference Matters**:
  - `.gitignore` already lists what should be excluded from version control — `.dockerignore` needs the same plus `.git/` itself and docs
  - Streamlit defaults to `headless=false` (tries to open browser) and `address=localhost` (rejects external connections) — both are fatal in a container

  **Acceptance Criteria**:

  - [ ] `.dockerignore` file exists at project root
  - [ ] `.streamlit/config.toml` file exists
  - [ ] `.dockerignore` contains `.env`, `.git/`, `venv/`, `__pycache__/`
  - [ ] `.streamlit/config.toml` sets `headless = true` and `address = "0.0.0.0"`

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: .dockerignore excludes sensitive files
    Tool: Bash
    Preconditions: Project root exists with .dockerignore
    Steps:
      1. Run: cat .dockerignore
      2. Assert: output contains '.env'
      3. Assert: output contains '.git/'
      4. Assert: output contains 'venv/'
      5. Assert: output contains '__pycache__/'
      6. Assert: output does NOT contain 'src/' (app code must be included)
    Expected Result: All sensitive/dev paths excluded, all app code paths included
    Failure Indicators: Missing .env exclusion, or src/ accidentally excluded
    Evidence: .sisyphus/evidence/task-1-dockerignore-content.txt

  Scenario: Streamlit config has production settings
    Tool: Bash
    Preconditions: .streamlit/config.toml exists
    Steps:
      1. Run: python -c "import tomllib; c=tomllib.load(open('.streamlit/config.toml','rb')); print(c)"
      2. Assert: c['server']['headless'] == True
      3. Assert: c['server']['address'] == '0.0.0.0'
      4. Assert: c['server']['enableCORS'] == False
      5. Assert: c['server']['enableXsrfProtection'] == False
    Expected Result: All production settings correctly configured
    Failure Indicators: Missing keys, wrong values, TOML parse error
    Evidence: .sisyphus/evidence/task-1-streamlit-config.txt
  ```

  **Commit**: YES
  - Message: `chore: add Docker prep files (.dockerignore, Streamlit config)`
  - Files: `.dockerignore`, `.streamlit/config.toml`

- [ ] 2. Add Azure SDK Dependencies to `requirements.txt`

  **What to do**:
  - Add `azure-identity==1.15.0` to `requirements.txt` — provides `DefaultAzureCredential` for managed identity auth
  - Add `azure-keyvault-secrets==4.8.0` to `requirements.txt` — provides `SecretClient` for Key Vault access
  - Place new entries after existing dependencies, following the same format (package==version)
  - Keep all existing pinned versions unchanged
  - These packages are needed by the Key Vault adapter in `token_storage.py` (Task 4)

  **Must NOT do**:
  - Do NOT change any existing dependency version
  - Do NOT remove plotly (unused but out of scope)
  - Do NOT add packages not directly needed (no azure-mgmt-*, no azure-storage-*)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single file, 2 lines added, no logic
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 3, 4)
  - **Blocks**: Task 4 (token_storage needs to know which packages are available), Task 5 (Dockerfile pip install)
  - **Blocked By**: None (can start immediately)

  **References** (CRITICAL):

  **Pattern References**:
  - `requirements.txt` — Existing file uses `package==version` format with exact pins. Follow this pattern exactly.

  **External References**:
  - `azure-identity` PyPI: Provides `DefaultAzureCredential` which auto-discovers managed identity on Azure, falls back to CLI/env creds locally
  - `azure-keyvault-secrets` PyPI: Provides `SecretClient` for get/set/delete secret operations

  **WHY Each Reference Matters**:
  - `requirements.txt` format must match existing style (exact pins, no ranges, no comments on same line as package)
  - `azure-identity` is the credential provider — without it, Key Vault client can't authenticate
  - `azure-keyvault-secrets` is the Key Vault client — without it, can't read/write tokens

  **Acceptance Criteria**:

  - [ ] `requirements.txt` contains `azure-identity==1.15.0`
  - [ ] `requirements.txt` contains `azure-keyvault-secrets==4.8.0`
  - [ ] All 7 original dependencies unchanged
  - [ ] `pip install -r requirements.txt` succeeds (no conflicts)

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Dependencies install without conflicts
    Tool: Bash
    Preconditions: Python 3.11+ available
    Steps:
      1. Run: pip install --dry-run -r requirements.txt 2>&1
      2. Assert: exit code 0
      3. Assert: output does NOT contain 'ERROR' or 'Conflict'
      4. Run: grep -c '==' requirements.txt
      5. Assert: output is '9' (7 original + 2 new)
    Expected Result: All 9 dependencies resolve without conflicts
    Failure Indicators: Version conflict, missing package, broken pin
    Evidence: .sisyphus/evidence/task-2-pip-dryrun.txt

  Scenario: Original dependencies unchanged
    Tool: Bash
    Preconditions: requirements.txt updated
    Steps:
      1. Run: grep 'streamlit==1.31.0' requirements.txt
      2. Assert: match found
      3. Run: grep 'pandas==2.1.4' requirements.txt
      4. Assert: match found
      5. Run: grep 'simple-salesforce==1.12.5' requirements.txt
      6. Assert: match found
    Expected Result: All original pins preserved exactly
    Failure Indicators: Any original version changed or line missing
    Evidence: .sisyphus/evidence/task-2-original-deps.txt
  ```

  **Commit**: YES
  - Message: `chore: add Azure SDK dependencies`
  - Files: `requirements.txt`


- [ ] 3. Bicep Infrastructure Template (`infra/main.bicep`)

  **What to do**:
  - Create `infra/` directory at project root
  - Create `infra/main.bicep` with the following Azure resources:

  **Parameters** (all with sensible defaults):
  - `appName` (string, required) — base name for all resources (e.g., `ae-dashboard`)
  - `location` (string, default: `resourceGroup().location`)
  - `appServicePlanSku` (string, default: `B1`) — minimum for Linux containers + Always On
  - `acrSku` (string, default: `Basic`)

  **Resources to create:**
  1. **Azure Container Registry** (`Microsoft.ContainerRegistry/registries`)
     - Name: `${replace(appName, '-', '')}acr` (ACR names must be alphanumeric)
     - SKU: parameterized (default Basic)
     - Admin user: enabled (for initial deploy script; pipeline uses service connection)
  2. **App Service Plan** (`Microsoft.Web/serverfarms`)
     - Name: `${appName}-plan`
     - Kind: `linux`, reserved: true
     - SKU: parameterized (default B1)
  3. **App Service** (`Microsoft.Web/sites`)
     - Name: `${appName}`
     - Kind: `app,linux,container`
     - Identity: `SystemAssigned` (managed identity for Key Vault access)
     - `linuxFxVersion`: `DOCKER|${acrLoginServer}/${appName}:latest`
     - Properties: `httpsOnly: true`, `alwaysOn: true`
     - Site config: `webSocketsEnabled: true`, `http20Enabled: true`
     - App Settings:
       - `WEBSITES_PORT` = `8501`
       - `WEBSITES_CONTAINER_START_TIME_LIMIT` = `300`
       - `KEY_VAULT_NAME` = Key Vault name (reference)
       - `DOCKER_REGISTRY_SERVER_URL` = `https://${acrLoginServer}`
       - `DOCKER_REGISTRY_SERVER_USERNAME` = ACR admin username
       - `DOCKER_REGISTRY_SERVER_PASSWORD` = ACR admin password (listCredentials)
       - Placeholder comments for Salesforce + Azure AD settings (set via deploy script)
     - Health check path: `/_stcore/health`
  4. **Key Vault** (`Microsoft.KeyVault/vaults`)
     - Name: `${appName}-kv`
     - SKU: standard
     - Access policies: Grant the App Service managed identity `get`, `set`, `delete` on secrets
     - Enabled for template deployment: true
  5. **Role Assignment** — AcrPull role for App Service managed identity on ACR
     - Role: `7f951dda-4ed3-4680-a7ca-43fe172d538d` (AcrPull built-in role)
     - Principal: App Service system-assigned identity principalId

  **Outputs:**
  - `appServiceUrl` — `https://${appName}.azurewebsites.net`
  - `acrLoginServer` — ACR login server FQDN
  - `keyVaultName` — Key Vault resource name
  - `appServicePrincipalId` — managed identity principal ID

  **Must NOT do**:
  - Do NOT include application secrets (Salesforce keys, Azure AD keys) in Bicep — those go in App Settings via deploy script
  - Do NOT add VNet, NSG, Private Endpoints, or any networking
  - Do NOT add Application Insights or monitoring resources
  - Do NOT add deployment slots
  - Do NOT add auto-scale rules
  - Do NOT create the resource group (it's existing)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Complex IaC with 5 resources, role assignments, managed identity, and cross-resource references. Requires Bicep expertise.
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 4)
  - **Blocks**: Task 6 (deploy script references Bicep outputs), Task 7 (pipeline references Bicep file and ACR)
  - **Blocked By**: None (can start immediately)

  **References** (CRITICAL):

  **Pattern References**:
  - `scripts/.env.example` — Lines 11-67 list ALL environment variables the app uses. The Bicep template's App Settings section must include placeholder entries for each of these, commented or with empty values, so the deploy script knows what to configure.

  **API/Type References**:
  - Bicep resource types: `Microsoft.Web/serverfarms@2023-12-01`, `Microsoft.Web/sites@2023-12-01`, `Microsoft.ContainerRegistry/registries@2023-11-01-preview`, `Microsoft.KeyVault/vaults@2023-07-01`
  - AcrPull role ID: `7f951dda-4ed3-4680-a7ca-43fe172d538d`

  **External References**:
  - Azure Bicep docs for App Service Linux containers: linuxFxVersion format is `DOCKER|registry/image:tag`
  - Azure Key Vault access policies: `secrets` permissions array accepts `get`, `set`, `delete`, `list`
  - App Service health check: `healthCheckPath` property in siteConfig

  **WHY Each Reference Matters**:
  - `.env.example` is the canonical list of all config vars — missing any in App Settings means a broken deployment
  - Bicep API versions must be recent enough to support all properties (2023-12-01 for Web, 2023-07-01 for KeyVault)
  - AcrPull role is specific — using broader roles (Contributor) is a security anti-pattern

  **Acceptance Criteria**:

  - [ ] `infra/main.bicep` exists
  - [ ] `az bicep build --file infra/main.bicep` exits 0 (valid syntax)
  - [ ] Template defines all 5 resources: ACR, App Service Plan, App Service, Key Vault, role assignment
  - [ ] App Service has `webSocketsEnabled: true`
  - [ ] App Service has `httpsOnly: true`
  - [ ] App Service has `WEBSITES_PORT: '8501'` in app settings
  - [ ] App Service has `WEBSITES_CONTAINER_START_TIME_LIMIT: '300'` in app settings
  - [ ] Key Vault access policy grants managed identity `get`, `set`, `delete` on secrets
  - [ ] All parameters have defaults except `appName`

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Bicep template compiles without errors
    Tool: Bash
    Preconditions: Azure CLI with Bicep installed
    Steps:
      1. Run: az bicep build --file infra/main.bicep 2>&1
      2. Assert: exit code 0
      3. Assert: output does NOT contain 'Error' or 'BCP'
    Expected Result: Bicep compiles to ARM JSON successfully
    Failure Indicators: BCP error codes, missing resource properties, invalid references
    Evidence: .sisyphus/evidence/task-3-bicep-build.txt

  Scenario: Bicep template contains required resources
    Tool: Bash
    Preconditions: infra/main.bicep exists
    Steps:
      1. Run: grep -c 'Microsoft.Web/serverfarms' infra/main.bicep
      2. Assert: output >= 1 (App Service Plan)
      3. Run: grep -c 'Microsoft.Web/sites' infra/main.bicep
      4. Assert: output >= 1 (App Service)
      5. Run: grep -c 'Microsoft.ContainerRegistry/registries' infra/main.bicep
      6. Assert: output >= 1 (ACR)
      7. Run: grep -c 'Microsoft.KeyVault/vaults' infra/main.bicep
      8. Assert: output >= 1 (Key Vault)
      9. Run: grep -c 'webSocketsEnabled' infra/main.bicep
      10. Assert: output >= 1 (WebSockets enabled)
      11. Run: grep -c 'WEBSITES_PORT' infra/main.bicep
      12. Assert: output >= 1 (Port config)
    Expected Result: All 5 resource types present, critical config properties present
    Failure Indicators: Missing resource type, missing config property
    Evidence: .sisyphus/evidence/task-3-bicep-resources.txt

  Scenario: Bicep has no hardcoded secrets
    Tool: Bash
    Preconditions: infra/main.bicep exists
    Steps:
      1. Run: grep -iE '(password|secret|key)\s*[:=]\s*[\x27"]' infra/main.bicep | grep -v 'param\|listCredentials\|@secure\|DOCKER_REGISTRY'
      2. Assert: output is empty (no hardcoded secrets)
    Expected Result: Zero hardcoded credential values
    Failure Indicators: Any secret value in plain text
    Evidence: .sisyphus/evidence/task-3-bicep-secrets.txt
  ```

  **Commit**: YES
  - Message: `feat(infra): add Bicep template for Azure App Service, ACR, Key Vault`
  - Files: `infra/main.bicep`
  - Pre-commit: `az bicep build --file infra/main.bicep`

- [ ] 4. Key Vault Adapter for `token_storage.py`

  **What to do**:
  - Modify `src/token_storage.py` to support dual backends: Key Vault (Azure) and filesystem (local dev)
  - **Backend selection**: Check `os.environ.get('KEY_VAULT_NAME')` at module level
    - If set: use Azure Key Vault via `SecretClient` + `DefaultAzureCredential`
    - If not set: use existing filesystem logic (unchanged)
  - **Adapter pattern**: Keep EXACT same function signatures — `save_tokens(access_token, refresh_token, instance_url)`, `load_tokens() -> dict`, `clear_tokens()`
  - **Key Vault implementation:**
    - Secret name: `salesforce-tokens` (single secret, JSON-encoded, matching current file format)
    - `save_tokens()`: serialize to JSON, call `client.set_secret('salesforce-tokens', json_string)`
    - `load_tokens()`: call `client.get_secret('salesforce-tokens')`, deserialize JSON, validate keys
    - `clear_tokens()`: call `client.begin_delete_secret('salesforce-tokens')` — use purge if soft-delete
  - **Error handling:**
    - `load_tokens()` must return `{}` if secret not found (ResourceNotFoundError) — mirrors filesystem behavior for first deploy
    - `save_tokens()` must handle transient Key Vault errors with a retry or graceful warning
    - `clear_tokens()` must handle not-found gracefully (no error if secret doesn't exist)
  - **Lazy initialization**: Create `SecretClient` once at module level (or on first use) to avoid repeated auth
  - **Imports**: Conditional — only import `azure.identity` and `azure.keyvault.secrets` when Key Vault is configured (so local dev doesn't need Azure SDK installed)

  **Must NOT do**:
  - Do NOT change function signatures — callers in `streamlit_dashboard.py` and `salesforce_oauth.py` must not need changes
  - Do NOT implement per-user token storage — maintain single shared token design
  - Do NOT add encryption beyond what Key Vault provides natively
  - Do NOT modify any other file in `src/`
  - Do NOT add logging/telemetry beyond existing `st.warning()` pattern

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Requires understanding Azure SDK patterns (DefaultAzureCredential, SecretClient), error handling, and preserving existing API contract
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 3)
  - **Blocks**: None (no other task depends on this directly)
  - **Blocked By**: None conceptually (code references azure packages but doesn't need them installed to write)

  **References** (CRITICAL):

  **Pattern References**:
  - `src/token_storage.py:1-60` — The ENTIRE current file. Read line-by-line. The adapter must preserve: docstrings, function signatures, JSON format (`access_token`, `refresh_token`, `instance_url` keys), `0o600` file permissions for filesystem mode, and the `Path.home() / '.salesforce_tokens'` path for local dev.
  - `streamlit_dashboard.py:20-24` — Import of `save_tokens`, `load_tokens`, `clear_tokens`. These imports must NOT break.

  **API/Type References**:
  - `token_storage.py:13` — `save_tokens(access_token: str, refresh_token: str, instance_url: str)` — exact signature to preserve
  - `token_storage.py:35` — `load_tokens() -> dict` — returns dict with keys `access_token`, `refresh_token`, `instance_url` or empty dict
  - `token_storage.py:57` — `clear_tokens()` — void, no return

  **External References**:
  - `azure.identity.DefaultAzureCredential` — auto-discovers managed identity on Azure, falls back to CLI/env creds locally
  - `azure.keyvault.secrets.SecretClient` — `set_secret(name, value)`, `get_secret(name)`, `begin_delete_secret(name)`
  - `azure.core.exceptions.ResourceNotFoundError` — thrown when secret doesn't exist

  **WHY Each Reference Matters**:
  - Current file is 60 lines — read ALL of it. The adapter wraps this, it doesn't rewrite from scratch
  - Import lines in `streamlit_dashboard.py` prove the exact public API that must be preserved
  - `DefaultAzureCredential` is critical — it's what makes managed identity "just work" without explicit credentials
  - `ResourceNotFoundError` must be caught in `load_tokens()` to return `{}` on first deploy (no tokens yet)

  **Acceptance Criteria**:

  - [ ] `token_storage.py` has dual-backend logic (Key Vault when `KEY_VAULT_NAME` set, filesystem otherwise)
  - [ ] Function signatures unchanged: `save_tokens(access_token, refresh_token, instance_url)`, `load_tokens() -> dict`, `clear_tokens()`
  - [ ] `load_tokens()` returns `{}` when Key Vault secret doesn't exist (not an exception)
  - [ ] `load_tokens()` returns `{}` when filesystem file doesn't exist (preserved behavior)
  - [ ] Azure SDK imports are conditional (only when Key Vault mode)
  - [ ] Filesystem fallback works identically to current behavior

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Filesystem fallback works without Azure SDK
    Tool: Bash
    Preconditions: KEY_VAULT_NAME env var NOT set
    Steps:
      1. Run: python -c "
         import os
         os.environ.pop('KEY_VAULT_NAME', None)
         from src.token_storage import save_tokens, load_tokens, clear_tokens
         # Test save
         save_tokens('test_at', 'test_rt', 'https://test.sf.com')
         # Test load
         result = load_tokens()
         assert result['access_token'] == 'test_at', f'Got: {result}'
         assert result['refresh_token'] == 'test_rt'
         assert result['instance_url'] == 'https://test.sf.com'
         # Test clear
         clear_tokens()
         assert load_tokens() == {}, 'Tokens not cleared'
         print('PASS: filesystem fallback works')"
      2. Assert: output contains 'PASS: filesystem fallback works'
      3. Assert: exit code 0
    Expected Result: All three functions work identically to before
    Failure Indicators: ImportError, assertion failure, file permission error
    Evidence: .sisyphus/evidence/task-4-filesystem-fallback.txt

  Scenario: Module imports succeed without KEY_VAULT_NAME
    Tool: Bash
    Preconditions: KEY_VAULT_NAME env var NOT set
    Steps:
      1. Run: KEY_VAULT_NAME= python -c "from src.token_storage import save_tokens, load_tokens, clear_tokens; print('PASS')"
      2. Assert: output is 'PASS'
      3. Assert: no ImportError for azure.identity or azure.keyvault.secrets
    Expected Result: Module loads without requiring Azure SDK packages
    Failure Indicators: ImportError on azure.* packages when KEY_VAULT_NAME is not set
    Evidence: .sisyphus/evidence/task-4-import-no-kv.txt

  Scenario: Function signatures match expected API
    Tool: Bash
    Preconditions: src/token_storage.py updated
    Steps:
      1. Run: python -c "
         import inspect
         from src.token_storage import save_tokens, load_tokens, clear_tokens
         sig_save = str(inspect.signature(save_tokens))
         sig_load = str(inspect.signature(load_tokens))
         sig_clear = str(inspect.signature(clear_tokens))
         assert 'access_token' in sig_save, f'save_tokens sig: {sig_save}'
         assert 'refresh_token' in sig_save
         assert 'instance_url' in sig_save
         print(f'save_tokens{sig_save}')  
         print(f'load_tokens{sig_load}')  
         print(f'clear_tokens{sig_clear}')  
         print('PASS: signatures match')"
      2. Assert: output contains 'PASS: signatures match'
    Expected Result: All three function signatures preserved exactly
    Failure Indicators: Missing parameter, renamed parameter, changed return type
    Evidence: .sisyphus/evidence/task-4-signatures.txt
  ```

  **Commit**: YES
  - Message: `feat(auth): add Key Vault adapter for token storage`
  - Files: `src/token_storage.py`
  - Pre-commit: `python -c "from src.token_storage import save_tokens, load_tokens, clear_tokens"`


- [ ] 5. Create Dockerfile

  **What to do**:
  - Create `Dockerfile` at project root for Azure App Service deployment
  - Use `python:3.11-slim` as base image (matches dep compatibility, small footprint)
  - Structure:
    ```dockerfile
    FROM python:3.11-slim
    WORKDIR /app
    COPY requirements.txt .
    RUN pip install --no-cache-dir -r requirements.txt
    COPY . .
    EXPOSE 8501
    HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
      CMD curl -f http://localhost:8501/_stcore/health || exit 1
    ENTRYPOINT ["streamlit", "run", "streamlit_dashboard.py", \
      "--server.port=8501"]
    ```
  - Note: `.streamlit/config.toml` (from Task 1) handles `headless`, `address`, CORS, XSRF settings. The Dockerfile only needs to set the port via CLI flag.
  - `HEALTHCHECK` uses the Streamlit built-in health endpoint
  - `--no-cache-dir` on pip install reduces image size
  - Copy requirements first, then app code (Docker layer caching: deps change less often)
  - `.dockerignore` (from Task 1) ensures `.env`, `.git/`, `venv/` are excluded from build context

  **Must NOT do**:
  - Do NOT use multi-stage build (unnecessary complexity for this app)
  - Do NOT install system packages beyond what pip needs (python:3.11-slim is sufficient)
  - Do NOT copy `.env` files into the image (`.dockerignore` handles this)
  - Do NOT add `CMD` with shell form — use exec form (ENTRYPOINT with array)
  - Do NOT pin pip version or add pip upgrade step (unnecessary)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single file, well-defined structure, no complex logic
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Task 6)
  - **Blocks**: Task 7 (pipeline builds from this Dockerfile)
  - **Blocked By**: Task 1 (.dockerignore, .streamlit/config.toml must exist), Task 2 (requirements.txt must be updated)

  **References** (CRITICAL):

  **Pattern References**:
  - `requirements.txt` — Lists all pip dependencies. Dockerfile COPY + pip install this file.
  - `.dockerignore` (from Task 1) — Controls what enters the Docker build context. Verify it exists before writing Dockerfile.
  - `.streamlit/config.toml` (from Task 1) — Streamlit production config that will be COPY'd into the image. Do NOT duplicate these settings as Dockerfile CLI flags.

  **External References**:
  - Streamlit CLI: `streamlit run` accepts `--server.port=N`. Other settings come from `.streamlit/config.toml`.
  - Docker HEALTHCHECK: `--start-period=60s` gives Streamlit time to boot before health checks begin

  **WHY Each Reference Matters**:
  - `requirements.txt` is COPY'd before app code for Docker layer caching — deps rebuild only when requirements change
  - `.dockerignore` is critical — without it, `.env` with real secrets enters the image
  - `.streamlit/config.toml` must be in the image for headless mode — verify COPY includes the `.streamlit/` directory

  **Acceptance Criteria**:

  - [ ] `Dockerfile` exists at project root
  - [ ] Base image is `python:3.11-slim`
  - [ ] `EXPOSE 8501` present
  - [ ] `HEALTHCHECK` configured with `/_stcore/health`
  - [ ] `docker build -t ae-dashboard .` succeeds
  - [ ] Container starts and health check passes

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Docker image builds successfully
    Tool: Bash
    Preconditions: Docker daemon running, Tasks 1 and 2 complete
    Steps:
      1. Run: docker build -t ae-dashboard-test . 2>&1
      2. Assert: exit code 0
      3. Assert: output contains 'Successfully built' or 'Successfully tagged' or 'naming to docker.io'
      4. Run: docker images ae-dashboard-test --format '{{.Size}}'
      5. Assert: image exists (non-empty output)
    Expected Result: Image builds without errors
    Failure Indicators: pip install failure, COPY failure, syntax error in Dockerfile
    Evidence: .sisyphus/evidence/task-5-docker-build.txt

  Scenario: Container starts and serves Streamlit
    Tool: Bash
    Preconditions: ae-dashboard-test image built
    Steps:
      1. Run: docker run -d -p 8501:8501 --name ae-test-container ae-dashboard-test
      2. Wait: 45 seconds (Streamlit cold start)
      3. Run: curl -sf http://localhost:8501/_stcore/health
      4. Assert: output is 'ok'
      5. Run: curl -sf http://localhost:8501 | head -20
      6. Assert: output contains '<html' or 'streamlit'
      7. Cleanup: docker stop ae-test-container && docker rm ae-test-container
    Expected Result: Streamlit serves on port 8501 inside container
    Failure Indicators: Container exits immediately, health check fails, curl timeout
    Evidence: .sisyphus/evidence/task-5-container-health.txt

  Scenario: .env is NOT in the Docker image
    Tool: Bash
    Preconditions: ae-dashboard-test image built
    Steps:
      1. Run: docker run --rm ae-dashboard-test ls -la /app/.env 2>&1
      2. Assert: exit code != 0 (file not found)
      3. Assert: output contains 'No such file'
    Expected Result: .env file is excluded from image by .dockerignore
    Failure Indicators: .env file exists in /app/ inside container
    Evidence: .sisyphus/evidence/task-5-no-env-in-image.txt
  ```

  **Commit**: YES
  - Message: `feat: add Dockerfile for Azure App Service deployment`
  - Files: `Dockerfile`
  - Pre-commit: `docker build -t ae-dashboard .`

- [ ] 6. PowerShell Deployment Script (`scripts/deploy.ps1`)

  **What to do**:
  - Create `scripts/deploy.ps1` — a comprehensive PowerShell script for end-to-end local deployment to Azure
  - Script must handle the FULL deployment lifecycle:

  **Parameters:**
  ```powershell
  param(
    [Parameter(Mandatory=$true)]  [string]$ResourceGroupName,
    [Parameter(Mandatory=$true)]  [string]$AppName,
    [string]$Location = 'eastus',
    [string]$AppServicePlanSku = 'B1',
    [string]$AcrSku = 'Basic',
    [switch]$SkipBicep,        # Skip infra deployment (just redeploy app)
    [switch]$SkipDocker,       # Skip Docker build/push (just update settings)
    [switch]$ConfigureSettings  # Interactive App Settings configuration
  )
  ```

  **Script sections:**

  1. **Prerequisites check**: Verify `az` CLI installed + logged in, Docker running, `pwsh` version
  2. **Bicep deployment** (unless `$SkipBicep`):
     - `az deployment group create --resource-group $ResourceGroupName --template-file infra/main.bicep --parameters appName=$AppName location=$Location appServicePlanSku=$AppServicePlanSku acrSku=$AcrSku`
     - Capture outputs: `acrLoginServer`, `keyVaultName`, `appServiceUrl`
  3. **Docker build + push** (unless `$SkipDocker`):
     - `az acr login --name $AcrName`
     - `docker build -t $AcrLoginServer/${AppName}:latest .`
     - `docker push $AcrLoginServer/${AppName}:latest`
  4. **App Settings configuration** (if `$ConfigureSettings`):
     - Prompt for each Salesforce OAuth setting: `SALESFORCE_CLIENT_ID`, `SALESFORCE_CLIENT_SECRET`, `SALESFORCE_REDIRECT_URI` (default: App Service URL), `SALESFORCE_SANDBOX`
     - Prompt for each Azure AD setting (optional): `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_REDIRECT_URI`
     - Use `az webapp config appsettings set` to apply all settings at once
     - Mark sensitive values with `--slot-setting` so they don't swap with deployment slots
  5. **Container configuration**:
     - `az webapp config container set` with ACR image reference
  6. **Restart + verify**:
     - `az webapp restart`
     - Poll health endpoint: `https://$AppName.azurewebsites.net/_stcore/health` with retry (up to 5min)
     - Print final status + URL

  **Output formatting**: Use `Write-Host` with colors for status, `Write-Warning` for issues, `Write-Error` for failures. Each section starts with a header.

  **Must NOT do**:
  - Do NOT hardcode any secrets in the script
  - Do NOT create the resource group (it's existing)
  - Do NOT install Azure CLI or Docker (just check they exist)
  - Do NOT add multi-environment logic (production only)
  - Do NOT add rollback logic (out of scope)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Complex script with Azure CLI commands, Docker operations, error handling, interactive prompts, and health check polling
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Task 5)
  - **Blocks**: None directly (Task 7 references deploy concepts but doesn't depend on script)
  - **Blocked By**: Task 3 (Bicep template must exist for deployment)

  **References** (CRITICAL):

  **Pattern References**:
  - `scripts/.env.example:1-72` — The COMPLETE list of all environment variables. Lines 11-14 are Salesforce OAuth (mandatory). Lines 44-67 are Azure AD (optional). The deploy script's App Settings configuration section must prompt for ALL of these, grouping mandatory vs optional.
  - `infra/main.bicep` (from Task 3) — The Bicep template this script deploys. Script must match parameter names exactly: `appName`, `location`, `appServicePlanSku`, `acrSku`.
  - `scripts/setup.sh` and `scripts/run.sh` — Existing script style. While these are bash, note the user-facing output pattern (simple status messages). PowerShell should follow similar clarity.

  **External References**:
  - `az deployment group create` — `--query properties.outputs` to capture Bicep outputs as JSON
  - `az acr login` — authenticates Docker to ACR
  - `az webapp config appsettings set` — `--settings KEY=VALUE KEY2=VALUE2` format
  - `az webapp config container set` — `--docker-custom-image-name` for ACR image

  **WHY Each Reference Matters**:
  - `.env.example` is the CANONICAL list of settings — if the deploy script misses any, the app won't work on Azure
  - Bicep parameter names must match EXACTLY — typos cause deployment failure
  - `az` CLI output format matters — use `--query` and `-o tsv` for scriptable output

  **Acceptance Criteria**:

  - [ ] `scripts/deploy.ps1` exists
  - [ ] Script has `param()` block with `ResourceGroupName` and `AppName` as mandatory
  - [ ] Script checks for `az` CLI and Docker as prerequisites
  - [ ] Script runs `az deployment group create` with correct Bicep file and parameters
  - [ ] Script builds and pushes Docker image to ACR
  - [ ] Script has `-ConfigureSettings` switch for interactive App Settings
  - [ ] Script prompts for ALL env vars from `.env.example` when configuring settings
  - [ ] Script polls health endpoint after deployment
  - [ ] `pwsh -Command "Get-Help ./scripts/deploy.ps1"` shows parameter help

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: PowerShell script has valid syntax
    Tool: Bash
    Preconditions: pwsh (PowerShell 7+) installed
    Steps:
      1. Run: pwsh -Command "$null = [System.Management.Automation.Language.Parser]::ParseFile('scripts/deploy.ps1', [ref]$null, [ref]$errors); if ($errors.Count -gt 0) { $errors | ForEach-Object { Write-Error $_.Message }; exit 1 } else { Write-Output 'PASS' }"
      2. Assert: output contains 'PASS'
      3. Assert: exit code 0
    Expected Result: Script parses without syntax errors
    Failure Indicators: Parse errors, unclosed blocks, invalid PowerShell syntax
    Evidence: .sisyphus/evidence/task-6-ps-syntax.txt

  Scenario: Script has all required parameters
    Tool: Bash
    Preconditions: scripts/deploy.ps1 exists
    Steps:
      1. Run: grep -c 'ResourceGroupName' scripts/deploy.ps1
      2. Assert: output >= 1
      3. Run: grep -c 'AppName' scripts/deploy.ps1
      4. Assert: output >= 1
      5. Run: grep -c 'SkipBicep' scripts/deploy.ps1
      6. Assert: output >= 1
      7. Run: grep -c 'ConfigureSettings' scripts/deploy.ps1
      8. Assert: output >= 1
    Expected Result: All documented parameters present in script
    Failure Indicators: Missing parameter name
    Evidence: .sisyphus/evidence/task-6-ps-params.txt

  Scenario: Script references all env vars from .env.example
    Tool: Bash
    Preconditions: scripts/deploy.ps1 exists
    Steps:
      1. Run: grep -c 'SALESFORCE_CLIENT_ID' scripts/deploy.ps1
      2. Assert: output >= 1
      3. Run: grep -c 'SALESFORCE_CLIENT_SECRET' scripts/deploy.ps1
      4. Assert: output >= 1
      5. Run: grep -c 'SALESFORCE_REDIRECT_URI' scripts/deploy.ps1
      6. Assert: output >= 1
      7. Run: grep -c 'AZURE_CLIENT_ID' scripts/deploy.ps1
      8. Assert: output >= 1
      9. Run: grep -c 'KEY_VAULT_NAME' scripts/deploy.ps1
      10. Assert: output >= 1
    Expected Result: All critical env vars referenced in settings configuration
    Failure Indicators: Missing env var reference
    Evidence: .sisyphus/evidence/task-6-ps-envvars.txt
  ```

  **Commit**: YES
  - Message: `feat(infra): add PowerShell deployment script`
  - Files: `scripts/deploy.ps1`


- [ ] 7. Azure DevOps YAML Pipeline (`azure-pipelines.yml`)

  **What to do**:
  - Create `azure-pipelines.yml` at project root
  - Pipeline structure:

  ```yaml
  trigger:
    branches:
      include:
        - main

  pool:
    vmImage: 'ubuntu-latest'

  variables:
    - name: acrServiceConnection
      value: '$(ACR_SERVICE_CONNECTION)'    # Set in Azure DevOps pipeline variables
    - name: azureServiceConnection
      value: '$(AZURE_SERVICE_CONNECTION)'  # Set in Azure DevOps pipeline variables
    - name: acrRepository
      value: '$(ACR_REPOSITORY)'             # e.g., ae-dashboard
    - name: appName
      value: '$(APP_NAME)'                   # Azure App Service name
    - name: resourceGroupName
      value: '$(RESOURCE_GROUP_NAME)'

  stages:
    - stage: Build
      displayName: 'Build and Push Docker Image'
      jobs:
        - job: BuildAndPush
          steps:
            - task: Docker@2
              displayName: 'Build and push to ACR'
              inputs:
                containerRegistry: '$(acrServiceConnection)'
                repository: '$(acrRepository)'
                command: 'buildAndPush'
                Dockerfile: '$(Build.SourcesDirectory)/Dockerfile'
                tags: |
                  $(Build.BuildId)
                  latest

    - stage: Deploy
      displayName: 'Deploy to Azure App Service'
      dependsOn: Build
      condition: succeeded()
      jobs:
        - deployment: DeployToAppService
          displayName: 'Deploy container'
          environment: 'production'
          strategy:
            runOnce:
              deploy:
                steps:
                  - task: AzureWebAppContainer@1
                    displayName: 'Deploy to App Service'
                    inputs:
                      azureSubscription: '$(azureServiceConnection)'
                      appName: '$(appName)'
                      containers: '$(acrLoginServer)/$(acrRepository):$(Build.BuildId)'
  ```

  - All sensitive values (service connection names, resource names) come from pipeline variables, NOT hardcoded
  - Use `deployment` job type for the Deploy stage (enables Azure DevOps environments + approval gates if added later)
  - Build stage uses `Docker@2` task which handles login + build + push to ACR
  - Deploy stage uses `AzureWebAppContainer@1` which updates the App Service container image
  - Include comments in the YAML explaining what each pipeline variable should be set to
  - Include a header comment block explaining prerequisites:
    - Azure DevOps service connection to Azure subscription
    - Azure DevOps service connection to ACR
    - Pipeline variables configured in Azure DevOps UI

  **Must NOT do**:
  - Do NOT include test stages (no tests exist)
  - Do NOT include code quality gates or linting stages
  - Do NOT include approval gates (can be added later via Azure DevOps environments)
  - Do NOT include multi-environment deployment (production only)
  - Do NOT include App Settings configuration in pipeline (that's the deploy script's job)
  - Do NOT hardcode service connection names, resource names, or any Azure-specific values
  - Do NOT include Bicep deployment in pipeline (infrastructure changes are via deploy script, not CI/CD)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Azure DevOps pipeline with Docker and App Service deployment tasks requires knowledge of ADO YAML schema, task inputs, and variable patterns
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3 (solo)
  - **Blocks**: None (final implementation task before verification)
  - **Blocked By**: Task 3 (references Bicep for understanding resource names), Task 5 (Dockerfile must exist for Docker@2 task)

  **References** (CRITICAL):

  **Pattern References**:
  - `Dockerfile` (from Task 5) -- Pipeline's Docker@2 task builds from this. Verify it exists and note the `EXPOSE` port.
  - `infra/main.bicep` (from Task 3) -- Understand the resource naming convention (`appName` parameter drives all names). Pipeline variables must align.

  **External References**:
  - Azure DevOps `Docker@2` task: `containerRegistry` input takes the service connection name, `repository` is the ACR repo name (not full URL)
  - Azure DevOps `AzureWebAppContainer@1` task: `containers` input takes full image reference `registry/repo:tag`
  - Azure DevOps pipeline variables: `$(VARIABLE_NAME)` syntax, set in ADO UI under Pipeline > Variables
  - Azure DevOps `deployment` job: enables environment tracking and optional approval gates

  **WHY Each Reference Matters**:
  - `Dockerfile` location must match the `Dockerfile` input in Docker@2 task (`$(Build.SourcesDirectory)/Dockerfile`)
  - Bicep naming conventions must match pipeline variable expectations (same `appName` used everywhere)
  - `Docker@2` vs `Docker@1`: v2 handles multi-tag push, login, and build in a single task
  - `deployment` job type (vs regular `job`) is important for Azure DevOps environments feature

  **Acceptance Criteria**:

  - [ ] `azure-pipelines.yml` exists at project root
  - [ ] Triggers on push to `main` branch
  - [ ] Has `Build` stage with `Docker@2` task
  - [ ] Has `Deploy` stage with `AzureWebAppContainer@1` task
  - [ ] Deploy stage depends on Build stage
  - [ ] All resource names come from variables (zero hardcoded Azure values)
  - [ ] Header comment explains prerequisites and required pipeline variables
  - [ ] YAML is syntactically valid

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Pipeline YAML is syntactically valid
    Tool: Bash
    Preconditions: azure-pipelines.yml exists
    Steps:
      1. Run: python -c "import yaml; data=yaml.safe_load(open('azure-pipelines.yml')); print('VALID'); print(f'Stages: {len(data.get(\"stages\", []))}')"
      2. Assert: output contains 'VALID'
      3. Assert: output contains 'Stages: 2'
    Expected Result: YAML parses successfully with exactly 2 stages
    Failure Indicators: YAML parse error, wrong number of stages
    Evidence: .sisyphus/evidence/task-7-yaml-valid.txt

  Scenario: Pipeline has correct trigger
    Tool: Bash
    Preconditions: azure-pipelines.yml exists
    Steps:
      1. Run: python -c "import yaml; data=yaml.safe_load(open('azure-pipelines.yml')); trigger=data.get('trigger',{}); branches=trigger.get('branches',{}).get('include',[]); assert 'main' in branches, f'Branches: {branches}'; print('PASS: triggers on main')"
      2. Assert: output contains 'PASS: triggers on main'
    Expected Result: Pipeline triggers on push to main branch
    Failure Indicators: Missing trigger, wrong branch name
    Evidence: .sisyphus/evidence/task-7-trigger.txt

  Scenario: No hardcoded Azure values
    Tool: Bash
    Preconditions: azure-pipelines.yml exists
    Steps:
      1. Run: grep -E '\.(azurecr\.io|azurewebsites\.net)' azure-pipelines.yml
      2. Assert: exit code != 0 (no matches) or output is empty
      3. Run: grep -c '\$(' azure-pipelines.yml
      4. Assert: output >= 4 (at least 4 variable references)
    Expected Result: All Azure-specific values come from variables
    Failure Indicators: Hardcoded ACR URL, hardcoded app name, hardcoded resource group
    Evidence: .sisyphus/evidence/task-7-no-hardcoded.txt

  Scenario: Pipeline stages have correct dependency
    Tool: Bash
    Preconditions: azure-pipelines.yml exists
    Steps:
      1. Run: python -c "
         import yaml
         data = yaml.safe_load(open('azure-pipelines.yml'))
         stages = data['stages']
         build = [s for s in stages if s['stage'] == 'Build'][0]
         deploy = [s for s in stages if s['stage'] == 'Deploy'][0]
         assert deploy.get('dependsOn') == 'Build', f'dependsOn: {deploy.get(\"dependsOn\")}'
         print('PASS: Deploy depends on Build')"
      2. Assert: output contains 'PASS: Deploy depends on Build'
    Expected Result: Deploy stage explicitly depends on Build stage
    Failure Indicators: Missing dependsOn, wrong dependency
    Evidence: .sisyphus/evidence/task-7-stage-deps.txt
  ```

  **Commit**: YES
  - Message: `feat(ci): add Azure DevOps pipeline`
  - Files: `azure-pipelines.yml`

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 4 review agents run in PARALLEL. ALL must APPROVE. Rejection → fix → re-run.

- [ ] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, check Bicep resource, check script section). For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist in `.sisyphus/evidence/`. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [ ] F2. **Code Quality Review** — `unspecified-high`
  Review all new/changed files for: syntax errors, hardcoded secrets, missing error handling, inconsistent patterns. Check Bicep with `az bicep build`. Check Python imports work. Check PowerShell syntax with `pwsh -c "Get-Command"`. Check YAML validity. Verify `.dockerignore` excludes `.env`, `.git/`, `venv/`, `__pycache__/`. Verify no secrets in any committed file.
  Output: `Bicep [PASS/FAIL] | Python [PASS/FAIL] | PowerShell [PASS/FAIL] | YAML [PASS/FAIL] | Secrets [CLEAN/FOUND] | VERDICT`

- [ ] F3. **Real QA — Docker Build + Container Test** — `unspecified-high`
  Build Docker image: `docker build -t ae-dashboard .` — must succeed. Run container: `docker run -d -p 8501:8501 --name ae-test ae-dashboard`. Wait 30s for startup. Health check: `curl -s http://localhost:8501/_stcore/health` — must return `ok`. Verify Streamlit serves HTML: `curl -s http://localhost:8501 | grep -q "streamlit"`. Verify token_storage filesystem fallback: `docker exec ae-test python -c "from src.token_storage import load_tokens; assert load_tokens() == {}"`. Stop container: `docker stop ae-test && docker rm ae-test`. Save all output to `.sisyphus/evidence/final-qa/`.
  Output: `Build [PASS/FAIL] | Start [PASS/FAIL] | Health [PASS/FAIL] | Serve [PASS/FAIL] | Tokens [PASS/FAIL] | VERDICT`

- [ ] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual file changes (git diff). Verify 1:1 — everything in spec was built (no missing), nothing beyond spec was built (no creep). Check "Must NOT do" compliance: no changes to `streamlit_dashboard.py`, `salesforce_oauth.py`, `msal_auth.py`, `salesforce_queries.py`, `dashboard_calculations.py`, `dashboard_ui.py`. Detect unaccounted changes. Flag anything that modifies files outside the plan scope.
  Output: `Tasks [N/N compliant] | Forbidden Files [CLEAN/N modified] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

- **Task 1**: `chore: add Docker prep files (.dockerignore, Streamlit config)` — `.dockerignore`, `.streamlit/config.toml`
- **Task 2**: `chore: add Azure SDK dependencies` — `requirements.txt`
- **Task 3**: `feat(infra): add Bicep template for Azure App Service, ACR, Key Vault` — `infra/main.bicep`
- **Task 4**: `feat(auth): add Key Vault adapter for token storage` — `src/token_storage.py`
- **Task 5**: `feat: add Dockerfile for Azure App Service deployment` — `Dockerfile`
- **Task 6**: `feat(infra): add PowerShell deployment script` — `scripts/deploy.ps1`
- **Task 7**: `feat(ci): add Azure DevOps pipeline` — `azure-pipelines.yml`

---

## Success Criteria

### Verification Commands
```bash
# Docker build succeeds
docker build -t ae-dashboard .

# Container serves Streamlit
docker run -d -p 8501:8501 --name ae-test ae-dashboard
sleep 30
curl -s http://localhost:8501/_stcore/health  # Expected: "ok"
docker stop ae-test && docker rm ae-test

# Bicep is valid
az bicep build --file infra/main.bicep  # Expected: no errors

# Token storage fallback works
python -c "from src.token_storage import load_tokens; print(load_tokens())"  # Expected: {}

# YAML is valid
python -c "import yaml; yaml.safe_load(open('azure-pipelines.yml')); print('VALID')"
```

### Final Checklist
- [ ] All "Must Have" present
- [ ] All "Must NOT Have" absent
- [ ] Docker image builds and runs
- [ ] Bicep template valid
- [ ] PowerShell script complete with all App Settings
- [ ] Pipeline YAML valid and references correct stages
- [ ] Token storage works in both modes (Key Vault + filesystem)
- [ ] No secrets in any committed file
