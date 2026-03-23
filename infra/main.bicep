// AE Dashboard — Azure Infrastructure
// Provisions: App Service (Docker/Linux), Azure Container Registry, Key Vault,
//             App Service Plan, and managed identity role assignments.
//
// Usage:
//   az deployment group create \
//     --resource-group <existing-rg> \
//     --template-file infra/main.bicep \
//     --parameters appName=<your-app-name>
//
// Prerequisites: Existing resource group. Run from project root.

// ============================================================
// PARAMETERS
// ============================================================

@description('Base name for all resources. Used to derive resource names.')
param appName string

@description('Azure region. Defaults to resource group location.')
param location string = resourceGroup().location

@description('App Service Plan SKU. B1 is minimum for Linux containers + Always On.')
@allowed(['B1', 'B2', 'B3', 'S1', 'S2', 'S3', 'P1v3', 'P2v3'])
param appServicePlanSku string = 'B1'

@description('Azure Container Registry SKU.')
@allowed(['Basic', 'Standard', 'Premium'])
param acrSku string = 'Basic'

// --- Azure AD / MSAL parameters (for user authentication + restriction) ---

@description('Azure AD App Registration client ID. Leave empty to skip MSAL auth.')
param azureAdClientId string = ''

@description('Azure AD tenant ID.')
param azureAdTenantId string = ''

@secure()
@description('Azure AD App Registration client secret. Set via deploy.ps1 -ConfigureSettings if preferred.')
param azureAdClientSecret string = ''

@description('Azure AD redirect URI. Defaults to the App Service URL.')
param azureAdRedirectUri string = ''

@description('Comma-separated list of allowed email domains (e.g., "company.com,subsidiary.com"). Empty = no domain restriction.')
param azureAllowedDomains string = ''

@description('Comma-separated list of allowed email addresses. Empty = no email restriction.')
param azureAllowedEmails string = ''

// ============================================================
// VARIABLES
// ============================================================

// ACR names must be alphanumeric only — strip hyphens from appName
var acrName = replace(appName, '-', '')
var keyVaultName = '${appName}-kv'
var effectiveRedirectUri = azureAdRedirectUri != '' ? azureAdRedirectUri : 'https://${appName}.azurewebsites.net'

// ============================================================
// RESOURCE 1: Azure Container Registry
// ============================================================

resource acr 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' = {
  name: '${acrName}acr'
  location: location
  sku: { name: acrSku }
  properties: {
    adminUserEnabled: true // For initial deploy script; pipeline uses service connection
  }
}

// ============================================================
// RESOURCE 2: App Service Plan (Linux)
// ============================================================

resource appServicePlan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: '${appName}-plan'
  location: location
  kind: 'linux'
  sku: { name: appServicePlanSku }
  properties: {
    reserved: true // required for Linux App Service Plans
  }
}

// ============================================================
// RESOURCE 3: App Service (Docker/Linux container)
// ============================================================

resource appService 'Microsoft.Web/sites@2023-12-01' = {
  name: appName
  location: location
  kind: 'app,linux,container'
  identity: { type: 'SystemAssigned' }
  properties: {
    serverFarmId: appServicePlan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'DOCKER|${acr.properties.loginServer}/${appName}:latest'
      alwaysOn: true
      webSocketsEnabled: true // CRITICAL: Streamlit requires WebSockets for reactive UI
      http20Enabled: true
      healthCheckPath: '/_stcore/health'
      appSettings: [
        // --- Core container / port settings ---
        { name: 'WEBSITES_PORT', value: '8501' }
        { name: 'WEBSITES_CONTAINER_START_TIME_LIMIT', value: '300' }
        // --- Docker registry (ACR admin creds for initial convenience; managed identity pulls via AcrPull role) ---
        { name: 'DOCKER_REGISTRY_SERVER_URL', value: 'https://${acr.properties.loginServer}' }
        { name: 'DOCKER_REGISTRY_SERVER_USERNAME', value: acr.listCredentials().username }
        { name: 'DOCKER_REGISTRY_SERVER_PASSWORD', value: acr.listCredentials().passwords[0].value }
        // --- Key Vault reference so token_storage.py selects KV backend ---
        { name: 'KEY_VAULT_NAME', value: keyVaultName }
        // --- Salesforce OAuth (set via deploy.ps1 -ConfigureSettings after provisioning) ---
        // { name: 'SALESFORCE_CLIENT_ID', value: '' }
        // { name: 'SALESFORCE_CLIENT_SECRET', value: '' }
        // { name: 'SALESFORCE_REDIRECT_URI', value: 'https://${appName}.azurewebsites.net' }
        // { name: 'SALESFORCE_SANDBOX', value: 'false' }
        // { name: 'SALESFORCE_LOGIN_URL', value: '' }
        // { name: 'SALESFORCE_OAUTH_SCOPES', value: 'api refresh_token offline_access' }
        // --- Azure AD / MSAL (authentication + user restriction) ---
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
// RESOURCE 4: Key Vault
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
// RESOURCE 5: AcrPull role assignment — managed identity → ACR
// ============================================================

// AcrPull built-in role: 7f951dda-4ed3-4680-a7ca-43fe172d538d
// Allows App Service to pull container images from ACR without admin creds
resource acrPullRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acr.id, appService.id, '7f951dda-4ed3-4680-a7ca-43fe172d538d')
  scope: acr
  properties: {
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
    principalId: appService.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// ============================================================
// OUTPUTS
// ============================================================

output appServiceUrl string = 'https://${appService.properties.defaultHostName}'
output acrLoginServer string = acr.properties.loginServer
output keyVaultName string = keyVault.name
output appServicePrincipalId string = appService.identity.principalId
