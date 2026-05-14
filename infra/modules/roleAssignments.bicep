@description('Grants Container App managed identities access to Key Vault secrets and Storage tables.')

param keyVaultName string
param storageAccountName string
param principalIds array

// Built-in role definitions (Azure RBAC GUIDs)
var kvSecretsUser = '4633458b-17de-408a-b874-0445c86b69e6'
var storageTableDataContributor = '0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3'

resource kv 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
}

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: storageAccountName
}

resource kvRoleAssignments 'Microsoft.Authorization/roleAssignments@2022-04-01' = [
  for (pid, i) in principalIds: {
    name: guid(kv.id, pid, kvSecretsUser)
    scope: kv
    properties: {
      principalId: pid
      principalType: 'ServicePrincipal'
      roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', kvSecretsUser)
    }
  }
]

resource storageRoleAssignments 'Microsoft.Authorization/roleAssignments@2022-04-01' = [
  for (pid, i) in principalIds: {
    name: guid(storage.id, pid, storageTableDataContributor)
    scope: storage
    properties: {
      principalId: pid
      principalType: 'ServicePrincipal'
      roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageTableDataContributor)
    }
  }
]
