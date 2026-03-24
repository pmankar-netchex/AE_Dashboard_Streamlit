// AE Dashboard — Azure Infrastructure (Zip Deploy)
// Provisions: App Service (Python/Linux), Key Vault.
// Reuses an existing App Service Plan (shared with DOL app).
//
// Usage:
//   az deployment group create \
//     --resource-group <existing-rg> \
//     --template-file infra/main.bicep \
//     --parameters appName=<name> appServicePlanId=<plan-resource-id>

// ============================================================
// PARAMETERS
// ============================================================

@description('Base name for all resources.')
param appName string

@description('Azure region. Defaults to resource group location.')
param location string = resourceGroup().location

@description('Resource ID of an existing App Service Plan to host this app. Example: /subscriptions/.../resourceGroups/.../providers/Microsoft.Web/serverfarms/<plan-name>')
param appServicePlanId string

// --- Azure AD / MSAL parameters ---

@description('Azure AD App Registration client ID. Leave empty to skip MSAL auth.')
param azureAdClientId string = ''

@description('Azure AD tenant ID.')
param azureAdTenantId string = ''

@secure()
@description('Azure AD App Registration client secret.')
param azureAdClientSecret string = ''

@description('Azure AD redirect URI. Defaults to the App Service URL.')
param azureAdRedirectUri string = ''

@description('Comma-separated list of allowed email domains.')
param azureAllowedDomains string = ''

@description('Comma-separated list of allowed email addresses.')
param azureAllowedEmails string = ''

// ============================================================
// VARIABLES
// ============================================================

var keyVaultName = '${appName}-kv'
var effectiveRedirectUri = azureAdRedirectUri != '' ? azureAdRedirectUri : 'https://${appName}.azurewebsites.net'

// ============================================================
// RESOURCE 1: App Service (Python 3.11 / Zip Deploy)
// ============================================================

resource appService 'Microsoft.Web/sites@2023-12-01' = {
  name: appName
  location: location
  kind: 'app,linux'
  identity: { type: 'SystemAssigned' }
  properties: {
    serverFarmId: appServicePlanId
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.11'
      appCommandLine: 'python -m streamlit run streamlit_dashboard.py --server.port 8000 --server.address 0.0.0.0 --server.headless true --server.enableCORS false --server.enableXsrfProtection false'
      alwaysOn: true
      webSocketsEnabled: true
      http20Enabled: true
      ftpsState: 'Disabled'
      minTlsVersion: '1.2'
      healthCheckPath: '/_stcore/health'
      appSettings: [
        { name: 'SCM_DO_BUILD_DURING_DEPLOYMENT', value: 'true' }
        { name: 'WEBSITES_PORT', value: '8000' }
        { name: 'WEBSITES_CONTAINER_START_TIME_LIMIT', value: '600' }
        { name: 'KEY_VAULT_NAME', value: keyVaultName }
        // --- Azure AD / MSAL ---
        { name: 'AZURE_CLIENT_ID', value: azureAdClientId }
        { name: 'AZURE_TENANT_ID', value: azureAdTenantId }
        { name: 'AZURE_CLIENT_SECRET', value: azureAdClientSecret }
        { name: 'AZURE_REDIRECT_URI', value: effectiveRedirectUri }
        { name: 'AZURE_AUTHORITY', value: azureAdTenantId != '' ? 'https://login.microsoftonline.com/${azureAdTenantId}' : '' }
        { name: 'AZURE_SCOPES', value: 'User.Read' }
        { name: 'AZURE_ALLOWED_DOMAINS', value: azureAllowedDomains }
        { name: 'AZURE_ALLOWED_EMAILS', value: azureAllowedEmails }
      ]
    }
  }
}

// ============================================================
// RESOURCE 2: Key Vault
// ============================================================

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  properties: {
    sku: { family: 'A', name: 'standard' }
    tenantId: subscription().tenantId
    accessPolicies: [
      {
        tenantId: subscription().tenantId
        objectId: appService.identity.principalId
        permissions: {
          secrets: ['get', 'set', 'delete']
        }
      }
    ]
    enabledForDeployment: true
    enabledForTemplateDeployment: true
  }
}

// ============================================================
// OUTPUTS
// ============================================================

output appServiceUrl string = 'https://${appService.properties.defaultHostName}'
output keyVaultName string = keyVault.name
output appServicePrincipalId string = appService.identity.principalId
