# Decisions — azure-deployment

## [2026-02-26] Architectural Decisions (from planning session)

### D001: Key Vault over Blob Storage for token persistence
- **Decision**: Use Azure Key Vault to store Salesforce refresh tokens
- **Rationale**: Low-frequency access (~startup + every 2hrs), secrets management built-in,
  managed identity integration is seamless, no additional SDK complexity vs blob

### D002: Adapter pattern for token_storage.py
- **Decision**: Same 3 function signatures, backend selected by KEY_VAULT_NAME env var
- **Rationale**: Zero changes to callers (streamlit_dashboard.py, salesforce_oauth.py)
- **Key Vault secret name**: `salesforce-tokens` (JSON string, same format as file)

### D003: System-assigned managed identity for App Service
- **Decision**: System-assigned (not user-assigned) managed identity
- **Rationale**: Simpler, auto-lifecycle-managed, sufficient for this use case

### D004: Docker on Linux App Service (not code deploy)
- **Decision**: Docker container deployment
- **Rationale**: Streamlit requires custom startup command; Docker is cleanest packaging

### D005: Production-only environment
- **Decision**: Single resource group, no dev/staging
- **Rationale**: Team dashboard, not customer-facing; simpler deployment model

### D006: Single-user shared Salesforce token
- **Decision**: One Key Vault secret for all app users (not per-user)
- **Rationale**: Existing design is single admin auth, all users see same dashboard data.
  Per-user tokens would require fundamental app redesign out of scope.

### D007: ACR created by Bicep (not pre-existing)
- **Decision**: Bicep creates ACR alongside other resources
- **Rationale**: Greenfield infrastructure for this app specifically; cleaner lifecycle

### D008: Infrastructure changes via deploy.ps1, not pipeline
- **Decision**: Pipeline does build+deploy only; Bicep runs from local PowerShell script
- **Rationale**: Infrastructure changes should be deliberate, not auto-triggered by every commit
