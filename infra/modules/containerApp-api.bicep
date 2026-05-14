@description('FastAPI Container App with INTERNAL ingress (only the UI container can reach it).')

param location string
param name string
param managedEnvironmentId string
param acrLoginServer string
param acrUsername string
@secure()
param acrPassword string
param image string
@secure()
param storageConnectionString string
@secure()
param sfClientId string
@secure()
param sfClientSecret string
param sfLoginUrl string
@secure()
param sendgridApiKey string
param sendgridFromEmail string
@secure()
param internalApiKey string
param bootstrapAdminEmails string
param schedulerTz string = 'America/Chicago'

@minValue(0)
@maxValue(30)
param minReplicas int = 1
@minValue(1)
@maxValue(30)
param maxReplicas int = 1

param containerCpu string = '0.5'
param containerMemory string = '1.0Gi'

@description('Enables the SOQL-template write path. Writes still require an admin role at the API layer; this is a deployment-level kill switch on top of that.')
param allowProdQueryWrites bool = true

resource apiApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: name
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    managedEnvironmentId: managedEnvironmentId
    configuration: {
      secrets: union(
        [
          { name: 'acr-password', value: acrPassword }
          { name: 'azure-storage-connection-string', value: storageConnectionString }
          { name: 'sf-client-id', value: sfClientId }
          { name: 'sf-client-secret', value: sfClientSecret }
          { name: 'internal-api-key', value: internalApiKey }
        ],
        empty(sendgridApiKey)
          ? []
          : [ { name: 'sendgrid-api-key', value: sendgridApiKey } ]
      )
      // INTERNAL ingress — only UI container in the same environment can hit /api/*
      ingress: {
        external: false
        targetPort: 8000
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
        // Single replica is intentional — the scheduler runs in-process and
        // we want exactly one cron-firing owner.
        minReplicas: minReplicas
        maxReplicas: maxReplicas
      }
      containers: [
        {
          name: 'api'
          image: image
          env: union(
            [
              { name: 'ENV', value: 'prod' }
              { name: 'PORT', value: '8000' }
              { name: 'AZURE_STORAGE_CONNECTION_STRING', secretRef: 'azure-storage-connection-string' }
              { name: 'SF_CLIENT_ID', secretRef: 'sf-client-id' }
              { name: 'SF_CLIENT_SECRET', secretRef: 'sf-client-secret' }
              { name: 'SF_LOGIN_URL', value: sfLoginUrl }
              { name: 'SENDGRID_FROM_EMAIL', value: sendgridFromEmail }
              { name: 'INTERNAL_API_KEY', secretRef: 'internal-api-key' }
              { name: 'BOOTSTRAP_ADMIN_EMAILS', value: bootstrapAdminEmails }
              { name: 'SCHEDULER_TZ', value: schedulerTz }
              { name: 'ALLOW_PROD_QUERY_WRITES', value: allowProdQueryWrites ? 'true' : 'false' }
            ],
            empty(sendgridApiKey)
              ? []
              : [ { name: 'SENDGRID_API_KEY', secretRef: 'sendgrid-api-key' } ]
          )
          resources: {
            cpu: json(containerCpu)
            memory: containerMemory
          }
        }
      ]
    }
  }
}

output name string = apiApp.name
output fqdn string = apiApp.properties.configuration.ingress.fqdn
output principalId string = apiApp.identity.principalId
