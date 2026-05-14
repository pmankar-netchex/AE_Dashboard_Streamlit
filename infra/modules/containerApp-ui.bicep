@description('React UI Container App (nginx). External ingress + Easy Auth.')

param location string
param name string
param managedEnvironmentId string
param acrLoginServer string
param acrUsername string
@secure()
param acrPassword string
param image string

@description('Internal FQDN of the API container app (without scheme).')
param apiHost string
@secure()
param internalApiKey string

@description('Entra App Registration client ID for Easy Auth. Empty disables Easy Auth (e.g. for first deploy before app registration exists).')
param entraClientId string = ''
param tenantId string = subscription().tenantId

@minValue(0)
@maxValue(30)
param minReplicas int = 1
@minValue(1)
@maxValue(30)
param maxReplicas int = 3

param containerCpu string = '0.25'
param containerMemory string = '0.5Gi'

resource uiApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: name
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    managedEnvironmentId: managedEnvironmentId
    configuration: {
      secrets: [
        { name: 'acr-password', value: acrPassword }
        { name: 'internal-api-key', value: internalApiKey }
      ]
      ingress: {
        external: true
        targetPort: 80
        transport: 'http'
      }
      registries: [
        {
          server: acrLoginServer
          username: acrUsername
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
          name: 'ui'
          image: image
          env: [
            { name: 'API_HOST', value: apiHost }
            { name: 'INTERNAL_API_KEY', secretRef: 'internal-api-key' }
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

// Easy Auth (Entra ID). Only created when entraClientId is provided —
// the user's plan is to add app registration as the last step, so the
// initial deploy runs without it and re-deploys flip this on.
resource authConfig 'Microsoft.App/containerApps/authConfigs@2024-03-01' = if (!empty(entraClientId)) {
  parent: uiApp
  name: 'current'
  properties: {
    platform: {
      enabled: true
    }
    globalValidation: {
      unauthenticatedClientAction: 'RedirectToLoginPage'
      redirectToProvider: 'azureactivedirectory'
    }
    identityProviders: {
      azureActiveDirectory: {
        enabled: true
        registration: {
          openIdIssuer: 'https://login.microsoftonline.com/${tenantId}/v2.0'
          clientId: entraClientId
        }
        validation: {
          allowedAudiences: [
            'api://${entraClientId}'
          ]
        }
      }
    }
    login: {
      tokenStore: {
        enabled: true
      }
    }
  }
}

output name string = uiApp.name
output fqdn string = uiApp.properties.configuration.ingress.fqdn
output principalId string = uiApp.identity.principalId
