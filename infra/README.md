# Infra (Bicep)

Composition: `main.bicep` calls per-resource modules under `modules/`.

| Module | Purpose |
|---|---|
| `logAnalytics.bicep` | Log Analytics workspace for Container Apps logs |
| `containerEnv.bicep` | Container Apps environment |
| `acr.bicep` | Azure Container Registry (admin-enabled for simple auth) |
| `storage.bicep` | Storage account + Table services for the 6 app tables (queries, querieshistory, users, schedules, audit, jobstore) |
| `keyVault.bicep` | Key Vault for SF/SendGrid/internal secrets |
| `containerApp-api.bicep` | FastAPI app — internal ingress, single replica (scheduler owner) |
| `containerApp-ui.bicep` | Nginx + React build — external ingress, optional Easy Auth |
| `roleAssignments.bicep` | Managed identities → KV Secrets User + Storage Table Data Contributor |

## First deploy (before Entra app registration)

```bash
RG=ae-dashboard-dev
LOC=eastus
az group create -n $RG -l $LOC

az deployment group create \
  -g $RG \
  -f infra/main.bicep \
  -p infra/parameters.example.json \
  -p sfClientId=<...> sfClientSecret=<...> sendgridApiKey=<...> internalApiKey=<random> \
     bootstrapAdminEmails=you@netchex.com
```

`entraClientId` is empty, so Easy Auth is **not** enabled and the UI is publicly reachable. Useful for first-deploy smoke tests; tighten before exposing real data.

## After Entra app registration exists

```bash
az deployment group create \
  -g $RG \
  -f infra/main.bicep \
  -p infra/parameters.example.json \
  -p sfClientId=<...> sfClientSecret=<...> sendgridApiKey=<...> internalApiKey=<...> \
     entraClientId=<entra-client-id> bootstrapAdminEmails=you@netchex.com
```

The redeploy adds the `authConfigs/current` child resource on the UI app, flipping on Entra ID Easy Auth with `RedirectToLoginPage`. The API container's `INTERNAL_API_KEY` provides defense-in-depth: nginx injects it on proxied `/api/*` calls, so external callers who bypass Easy Auth still get rejected.

## Build & push images

After the first deploy:

```bash
ACR=$(az acr list -g $RG --query "[0].loginServer" -o tsv)
az acr login -n $ACR

docker build -t $ACR/ae-dashboard-api:$(git rev-parse --short HEAD) ./backend
docker push    $ACR/ae-dashboard-api:$(git rev-parse --short HEAD)

docker build -t $ACR/ae-dashboard-ui:$(git rev-parse --short HEAD) ./frontend
docker push    $ACR/ae-dashboard-ui:$(git rev-parse --short HEAD)

# Update each Container App to the new image (replace tag below)
az containerapp update -g $RG -n aedash-api --image $ACR/ae-dashboard-api:...
az containerapp update -g $RG -n aedash-ui  --image $ACR/ae-dashboard-ui:...
```

## Production query writes

`ALLOW_PROD_QUERY_WRITES` is `false` by default. To allow the SOQL editor's
Save button to mutate production templates, set it explicitly on the api app:

```bash
az containerapp update -g $RG -n aedash-api --set-env-vars ALLOW_PROD_QUERY_WRITES=true
```
