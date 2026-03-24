// Deploy into an EXISTING resource group (targetScope = resourceGroup).
// One-time: az group create (if needed), then az deployment group create ...

targetScope = 'resourceGroup'

@description('Azure region for resources. Defaults to the resource group location.')
param location string = resourceGroup().location

@description('Short prefix for resource names (lowercase letters, digits, hyphens). Keep short so the Container App name stays within limits.')
@maxLength(20)
param appNamePrefix string = 'aedash'

@description('Optional ACR name (alphanumeric only, 5–50 chars, globally unique). Leave empty to auto-generate from the resource group.')
param acrName string = ''

@allowed([
  'Basic'
  'Standard'
  'Premium'
])
param acrSku string = 'Basic'

@description('Minimum replicas. Default 1 avoids scale-to-zero and Streamlit cold starts. Set to 0 to allow scale-to-zero.')
@minValue(0)
@maxValue(30)
param minReplicas int = 1

@minValue(1)
@maxValue(30)
param maxReplicas int = 3

@description('CPU per replica (e.g. 0.25, 0.5, 0.75, 1.0). Must match a valid Consumption-plan combination with memory.')
param containerCpu string = '0.5'

@description('Memory per replica (e.g. 1.0Gi). Must match a valid Consumption-plan combination with CPU.')
param containerMemory string = '1.0Gi'

@description('Public image used only for the first revision until CI/CD pushes to ACR and updates the app.')
param initialContainerImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'

@description('Image repository name inside ACR (must match GitHub Actions env IMAGE_NAME).')
param containerImageRepository string = 'ae-dashboard'

var logAnalyticsName = '${appNamePrefix}-law'
var containerEnvName = '${appNamePrefix}-cae'
var containerAppName = '${appNamePrefix}-app'

var sanitizedAcrInput = replace(replace(toLower(acrName), '-', ''), '_', '')
var generatedAcrName = take(replace(toLower('acr${uniqueString(resourceGroup().id, appNamePrefix)}'), '-', ''), 50)
var effectiveAcrName = empty(acrName) ? generatedAcrName : sanitizedAcrInput

resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: logAnalyticsName
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: containerEnvName
  location: location
  properties: {
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalyticsWorkspace.properties.customerId
        sharedKey: logAnalyticsWorkspace.listKeys().primarySharedKey
      }
    }
  }
}

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: effectiveAcrName
  location: location
  sku: {
    name: acrSku
  }
  properties: {
    adminUserEnabled: true
  }
}

// AcrPull via role assignment needs Microsoft.Authorization/roleAssignments/write (Owner or User Access
// Administrator). Contributor cannot create role assignments. ACR admin + secret works with Contributor.
var acrCreds = acr.listCredentials()

resource containerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: containerAppName
  location: location
  properties: {
    managedEnvironmentId: containerAppsEnvironment.id
    configuration: {
      secrets: [
        {
          name: 'acr-password'
          value: acrCreds.passwords[0].value
        }
      ]
      ingress: {
        external: true
        // Sample image listens on 80; GitHub Actions sets 8501 after the real image is deployed.
        targetPort: 80
        transport: 'auto'
      }
      registries: [
        {
          server: acr.properties.loginServer
          username: acrCreds.username
          passwordSecretRef: 'acr-password'
        }
      ]
    }
    template: {
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
      }
      containers: [
        {
          name: 'ae-dashboard'
          image: initialContainerImage
          env: [
            {
              name: 'PORT'
              value: '8501'
            }
          ]
          resources: {
            cpu: json(containerCpu)
            memory: containerMemory
          }
        }
      ]
    }
  }
}

output containerAppName string = containerApp.name
output containerAppFqdn string = containerApp.properties.configuration.ingress.fqdn
output acrName string = acr.name
output acrLoginServer string = acr.properties.loginServer
output logAnalyticsWorkspaceName string = logAnalyticsWorkspace.name
output containerAppsEnvironmentName string = containerAppsEnvironment.name
output acrImageRepository string = containerImageRepository
output containerImageRepositoryUri string = '${acr.properties.loginServer}/${containerImageRepository}'
