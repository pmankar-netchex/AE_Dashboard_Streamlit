# Infra (Bicep)

Composition: `main.bicep` calls per-resource modules under `modules/`.

| Module | Purpose |
|---|---|
| `logAnalytics.bicep` | Log Analytics workspace for Container Apps logs |
| `containerEnv.bicep` | Container Apps environment |
| `acr.bicep` | Azure Container Registry (admin-enabled for simple auth) |
| `storage.bicep` | Storage account + Table services for the 5 app tables (queries, querieshistory, users, schedules, audit) |
| `keyVault.bicep` | Key Vault for SF/SendGrid/internal secrets |
| `containerApp-api.bicep` | FastAPI app — internal ingress, single replica (scheduler owner) |
| `containerApp-ui.bicep` | Nginx + React build — external ingress, optional Easy Auth |
| `roleAssignments.bicep` | Managed identities → KV Secrets User + Storage Table Data Contributor |

## Easy Auth (Entra ID)

`parameters.example.json` ships with the Entra App Registration client ID
already filled in (`5fffa614-3447-439b-88e1-f52985fab497`). Easy Auth is
**enabled when both `entraClientId` and `entraClientSecret` are set**;
leave the secret empty for an unauthenticated first deploy.

### One-time Entra setup

In the Entra portal for the app registration (5fffa614-…):

1. **Authentication → Add a platform → Web** and add the redirect URI:
   ```
   https://<ui-app-fqdn>/.auth/login/aad/callback
   ```
   `<ui-app-fqdn>` is the `uiAppFqdn` output of the Bicep deployment.
   Bicep also emits `uiRedirectUri` as a deployment output — copy it
   from there.
2. **Certificates & secrets → New client secret**, then copy the value
   (you only see it once) — that's `entraClientSecret` below.
3. **API permissions** → add the OpenID Connect scopes
   `openid`, `profile`, `email`.
4. Make sure **Supported account types** is the right tenancy (probably
   single-tenant for Netchex).

## First deploy (without Easy Auth)

```bash
RG=ae-dashboard-dev
LOC=eastus
az group create -n $RG -l $LOC

az deployment group create \
  -g $RG \
  -f infra/main.bicep \
  -p infra/parameters.example.json \
  -p sfClientId=<...> sfClientSecret=<...> \
     sendgridApiKey=<...> internalApiKey=<random-64> \
     bootstrapAdminEmails=you@netchexonline.com \
     entraClientSecret=''
```

`entraClientSecret` empty → Easy Auth is **not** enabled and the UI is
publicly reachable. Useful for first-deploy smoke tests.

## Turn Easy Auth on

```bash
az deployment group create \
  -g $RG \
  -f infra/main.bicep \
  -p infra/parameters.example.json \
  -p sfClientId=<...> sfClientSecret=<...> \
     sendgridApiKey=<...> internalApiKey=<...> \
     bootstrapAdminEmails=you@netchexonline.com \
     entraClientSecret=<the-secret-from-Certificates-and-secrets>
```

The redeploy adds the `authConfigs/current` child resource on the UI app,
flipping Easy Auth to `RedirectToLoginPage` with the Entra IdP and the
client ID from `parameters.example.json`. Easy Auth injects
`X-MS-CLIENT-PRINCIPAL` on every authenticated request; nginx in the UI
container forwards it to the FastAPI backend, which extracts the email
and looks the user up in the `users` table.

The API container's `INTERNAL_API_KEY` provides defense-in-depth: nginx
attaches it on every `/api/*` call, so external callers who somehow
discover the API's internal FQDN still get rejected.

After the redeploy, check the auth status:

```bash
az containerapp auth show -g $RG -n aedash-ui --query "properties.platform.enabled"
# → true
```

Hitting `https://<ui-fqdn>/` should now redirect to login.microsoftonline.com.

## Build & push images

After the first deploy:

```bash
ACR=$(az acr list -g $RG --query "[0].loginServer" -o tsv)
az acr login -n $ACR

docker build -t $ACR/ae-dashboard-api:$(git rev-parse --short HEAD) ./backend
docker push    $ACR/ae-dashboard-api:$(git rev-parse --short HEAD)

docker build -t $ACR/ae-dashboard-ui:$(git rev-parse --short HEAD) ./frontend
docker push    $ACR/ae-dashboard-ui:$(git rev-parse --short HEAD)

az containerapp update -g $RG -n aedash-api --image $ACR/ae-dashboard-api:...
az containerapp update -g $RG -n aedash-ui  --image $ACR/ae-dashboard-ui:...
```

## Production query writes

`ALLOW_PROD_QUERY_WRITES` is `false` by default. To allow the SOQL editor's
Save button to mutate production templates, set it explicitly on the api app:

```bash
az containerapp update -g $RG -n aedash-api --set-env-vars ALLOW_PROD_QUERY_WRITES=true
```
