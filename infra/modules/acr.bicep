param location string
param name string

@allowed([
  'Basic'
  'Standard'
  'Premium'
])
param sku string = 'Basic'

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: name
  location: location
  sku: {
    name: sku
  }
  properties: {
    adminUserEnabled: true
  }
}

output id string = acr.id
output name string = acr.name
output loginServer string = acr.properties.loginServer
output adminUsername string = acr.listCredentials().username
@secure()
output adminPassword string = acr.listCredentials().passwords[0].value
