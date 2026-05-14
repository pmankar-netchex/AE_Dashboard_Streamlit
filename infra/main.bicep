// Composition root for the overhauled AE Dashboard infrastructure.
//
// Deploys: Log Analytics → Container Apps Environment → ACR → Storage (with
// tables) → Key Vault → API Container App (internal) → UI Container App
// (external, optional Easy Auth) → role assignments.

targetScope = 'resourceGroup'

@description('Azure region.')
param location string = resourceGroup().location

@description('Short prefix for resource names.')
@maxLength(15)
param appNamePrefix string = 'aedash'

@description('Optional ACR name override.')
param acrName string = ''

@allowed([
  'Basic'
  'Standard'
  'Premium'
])
param acrSku string = 'Basic'

@description('Optional Key Vault name (3–24 chars, globally unique).')
param keyVaultName string = ''

@description('Optional storage account name (3–24 chars, alphanumeric).')
param storageAccountName string = ''

@description('Entra App Registration client ID for Easy Auth on UI. Leave empty to disable Easy Auth (first deploy before app registration exists).')
param entraClientId string = ''

@description('Sender email for SendGrid.')
param sendgridFromEmail string = 'dashboard@example.com'

@description('Comma-separated bootstrap admin emails.')
param bootstrapAdminEmails string = ''

@description('Salesforce login URL (e.g. https://netchex.my.salesforce.com).')
param sfLoginUrl string = 'https://login.salesforce.com'

@description('Scheduler timezone.')
param schedulerTz string = 'America/Chicago'

@description('Initial container image to deploy for both apps (used until you push real images).')
param initialContainerImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'

// ----- Secret inputs (pass at deploy time, e.g. via az deployment ... --parameters) -----

@secure()
@description('Salesforce Connected App client_id (client-credentials flow).')
param sfClientId string = ''

@secure()
@description('Salesforce Connected App client_secret.')
param sfClientSecret string = ''

@secure()
@description('SendGrid API key.')
param sendgridApiKey string = ''

@secure()
@description('Internal API key shared between UI and API for defense-in-depth.')
param internalApiKey string = ''

// ----- Derived names -----

var logAnalyticsName = '${appNamePrefix}-law'
var containerEnvName = '${appNamePrefix}-cae'
var apiAppName = '${appNamePrefix}-api'
var uiAppName = '${appNamePrefix}-ui'

var sanitizedAcr = replace(replace(toLower(acrName), '-', ''), '_', '')
var generatedAcrName = take(replace(toLower('acr${uniqueString(resourceGroup().id, appNamePrefix)}'), '-', ''), 50)
var effectiveAcrName = empty(acrName) ? generatedAcrName : sanitizedAcr

var generatedKvName = take(replace(toLower('${appNamePrefix}kv${uniqueString(resourceGroup().id, appNamePrefix)}'), '-', ''), 24)
var effectiveKvName = empty(keyVaultName) ? generatedKvName : keyVaultName

var generatedStorageName = take(replace(toLower('${appNamePrefix}st${uniqueString(resourceGroup().id, appNamePrefix)}'), '-', ''), 24)
var effectiveStorageName = empty(storageAccountName) ? generatedStorageName : toLower(storageAccountName)

// ----- Modules -----

module logAnalytics 'modules/logAnalytics.bicep' = {
  name: 'logAnalytics'
  params: {
    location: location
    name: logAnalyticsName
  }
}

module containerEnv 'modules/containerEnv.bicep' = {
  name: 'containerEnv'
  params: {
    location: location
    name: containerEnvName
    logAnalyticsCustomerId: logAnalytics.outputs.customerId
    logAnalyticsSharedKey: logAnalytics.outputs.primarySharedKey
  }
}

module acr 'modules/acr.bicep' = {
  name: 'acr'
  params: {
    location: location
    name: effectiveAcrName
    sku: acrSku
  }
}

module storage 'modules/storage.bicep' = {
  name: 'storage'
  params: {
    location: location
    name: effectiveStorageName
  }
}

module keyVault 'modules/keyVault.bicep' = {
  name: 'keyVault'
  params: {
    location: location
    name: effectiveKvName
  }
}

module apiApp 'modules/containerApp-api.bicep' = {
  name: 'apiApp'
  params: {
    location: location
    name: apiAppName
    managedEnvironmentId: containerEnv.outputs.id
    acrLoginServer: acr.outputs.loginServer
    acrUsername: acr.outputs.adminUsername
    acrPassword: acr.outputs.adminPassword
    image: initialContainerImage
    storageConnectionString: storage.outputs.primaryConnectionString
    sfClientId: sfClientId
    sfClientSecret: sfClientSecret
    sfLoginUrl: sfLoginUrl
    sendgridApiKey: sendgridApiKey
    sendgridFromEmail: sendgridFromEmail
    internalApiKey: internalApiKey
    bootstrapAdminEmails: bootstrapAdminEmails
    schedulerTz: schedulerTz
  }
}

module uiApp 'modules/containerApp-ui.bicep' = {
  name: 'uiApp'
  params: {
    location: location
    name: uiAppName
    managedEnvironmentId: containerEnv.outputs.id
    acrLoginServer: acr.outputs.loginServer
    acrUsername: acr.outputs.adminUsername
    acrPassword: acr.outputs.adminPassword
    image: initialContainerImage
    apiHost: apiApp.outputs.fqdn
    internalApiKey: internalApiKey
    entraClientId: entraClientId
  }
}

module roles 'modules/roleAssignments.bicep' = {
  name: 'roles'
  params: {
    keyVaultName: keyVault.outputs.name
    storageAccountName: storage.outputs.name
    principalIds: [
      apiApp.outputs.principalId
      uiApp.outputs.principalId
    ]
  }
}

// ----- Outputs -----

output apiAppName string = apiApp.outputs.name
output apiAppFqdn string = apiApp.outputs.fqdn
output uiAppName string = uiApp.outputs.name
output uiAppFqdn string = uiApp.outputs.fqdn
output acrLoginServer string = acr.outputs.loginServer
output storageAccountName string = storage.outputs.name
output keyVaultName string = keyVault.outputs.name
