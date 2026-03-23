<#
.SYNOPSIS
    End-to-end local deployment of the AE Dashboard to Azure App Service.

.DESCRIPTION
    Provisions Azure infrastructure via Bicep, builds and pushes a Docker image to ACR,
    configures App Settings, and verifies the deployment health endpoint.

.PARAMETER ResourceGroupName
    (Mandatory) Existing Azure resource group to deploy into.

.PARAMETER AppName
    (Mandatory) Base name for all Azure resources (e.g. "ae-dashboard").
    Drives naming: ACR = "${AppName -replace '-',''}acr", Key Vault = "${AppName}-kv".

.PARAMETER Location
    Azure region. Defaults to 'eastus'.

.PARAMETER AppServicePlanSku
    App Service Plan SKU. Defaults to 'B1'. Must be Linux-capable.

.PARAMETER AcrSku
    Azure Container Registry SKU. Defaults to 'Basic'.

.PARAMETER SkipBicep
    Skip infrastructure deployment (just redeploy the app image/settings).

.PARAMETER SkipDocker
    Skip Docker build and push (just update App Settings or restart).

.PARAMETER ConfigureSettings
    Interactively prompt for App Settings (Salesforce OAuth, Azure AD, etc.)
    and push them to the App Service.

.EXAMPLE
    .\deploy.ps1 -ResourceGroupName "ae-dashboard-rg" -AppName "ae-dashboard"

.EXAMPLE
    .\deploy.ps1 -ResourceGroupName "ae-dashboard-rg" -AppName "ae-dashboard" -SkipBicep -ConfigureSettings

.EXAMPLE
    .\deploy.ps1 -ResourceGroupName "ae-dashboard-rg" -AppName "ae-dashboard" -SkipBicep -SkipDocker -ConfigureSettings
#>

param(
    [Parameter(Mandatory=$true)]  [string]$ResourceGroupName,
    [Parameter(Mandatory=$true)]  [string]$AppName,
    [string]$Location = 'eastus',
    [string]$AppServicePlanSku = 'B1',
    [string]$AcrSku = 'Basic',
    [string]$AzureAdClientId = '',       # Azure AD app registration client ID
    [string]$AzureAdTenantId = '',       # Azure AD tenant ID
    [string]$AzureAdClientSecret = '',   # Azure AD client secret
    [string]$AzureAllowedDomains = '',   # Comma-separated allowed domains
    [string]$AzureAllowedEmails = '',    # Comma-separated allowed emails
    [switch]$SkipBicep,        # Skip infra deployment (just redeploy app)
    [switch]$SkipDocker,       # Skip Docker build/push (just update settings)
    [switch]$ConfigureSettings  # Interactive App Settings configuration
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ============================================================
# HELPER FUNCTIONS
# ============================================================

function Write-Section {
    param([string]$Title)
    Write-Host "`n=== $Title ===" -ForegroundColor Cyan
}

function Prompt-WithDefault {
    param(
        [string]$PromptText,
        [string]$Default = '',
        [switch]$Secret
    )
    $displayDefault = if ($Default -ne '') { " [$Default]" } else { '' }
    if ($Secret) {
        $value = Read-Host "$PromptText$displayDefault (leave blank to skip)"
    } else {
        $value = Read-Host "$PromptText$displayDefault"
    }
    if ($value -eq '' -and $Default -ne '') {
        return $Default
    }
    return $value
}

# ============================================================
# SECTION 1: PREREQUISITES CHECK
# ============================================================

Write-Section "PREREQUISITES CHECK"

# Check az CLI
Write-Host "Checking Azure CLI..." -ForegroundColor Yellow
if (-not (Get-Command 'az' -ErrorAction SilentlyContinue)) {
    Write-Error "Azure CLI ('az') not found. Install from https://docs.microsoft.com/cli/azure/install-azure-cli"
    exit 1
}
$azVersion = az version --query '"azure-cli"' -o tsv 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to query Azure CLI version. Ensure 'az' is on PATH."
    exit 1
}
Write-Host "  az CLI version: $azVersion" -ForegroundColor Green

# Check az login
Write-Host "Checking Azure login status..." -ForegroundColor Yellow
$accountJson = az account show -o json 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "Not logged into Azure CLI. Run 'az login' first."
    exit 1
}
$account = $accountJson | ConvertFrom-Json
Write-Host "  Logged in as: $($account.user.name)" -ForegroundColor Green
Write-Host "  Subscription: $($account.name) ($($account.id))" -ForegroundColor Green

# Check Docker (only needed for build/push)
if (-not $SkipDocker) {
    Write-Host "Checking Docker..." -ForegroundColor Yellow
    if (-not (Get-Command 'docker' -ErrorAction SilentlyContinue)) {
        Write-Error "Docker not found. Install from https://docs.docker.com/get-docker/"
        exit 1
    }
    $dockerInfo = docker info 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Docker daemon is not running. Start Docker Desktop or the Docker service."
        exit 1
    }
    Write-Host "  Docker is running." -ForegroundColor Green
}

Write-Host "Prerequisites satisfied." -ForegroundColor Green

# ============================================================
# SECTION 2: DERIVE RESOURCE NAMES
# ============================================================

Write-Section "RESOURCE NAMES"

# ACR name: alphanumeric only (Bicep does the same: replace('-','') + 'acr')
$AcrName = ($AppName -replace '-', '') + 'acr'
$KeyVaultName = "$AppName-kv"
$AppServicePlanName = "$AppName-plan"

Write-Host "  App Service:      $AppName"           -ForegroundColor White
Write-Host "  App Service Plan: $AppServicePlanName" -ForegroundColor White
Write-Host "  ACR name:         $AcrName"            -ForegroundColor White
Write-Host "  Key Vault:        $KeyVaultName"        -ForegroundColor White
Write-Host "  Resource Group:   $ResourceGroupName"   -ForegroundColor White

# ============================================================
# SECTION 3: BICEP DEPLOYMENT
# ============================================================

if (-not $SkipBicep) {
    Write-Section "BICEP INFRASTRUCTURE DEPLOYMENT"

    # Locate template relative to repo root (script lives in scripts/)
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $RepoRoot  = Split-Path -Parent $ScriptDir
    $BicepFile = Join-Path $RepoRoot 'infra' 'main.bicep'

    if (-not (Test-Path $BicepFile)) {
        Write-Error "Bicep template not found at: $BicepFile"
        exit 1
    }

    Write-Host "Deploying Bicep template: $BicepFile" -ForegroundColor Yellow
    Write-Host "  Parameters: appName=$AppName location=$Location appServicePlanSku=$AppServicePlanSku acrSku=$AcrSku" -ForegroundColor White

    # Build Bicep parameters — include Azure AD params if provided
    $bicepParams = "appName=$AppName location=$Location appServicePlanSku=$AppServicePlanSku acrSku=$AcrSku"
    if ($AzureAdClientId -ne '')     { $bicepParams += " azureAdClientId=$AzureAdClientId" }
    if ($AzureAdTenantId -ne '')     { $bicepParams += " azureAdTenantId=$AzureAdTenantId" }
    if ($AzureAdClientSecret -ne '') { $bicepParams += " azureAdClientSecret=$AzureAdClientSecret" }
    if ($AzureAllowedDomains -ne '') { $bicepParams += " azureAllowedDomains=$AzureAllowedDomains" }
    if ($AzureAllowedEmails -ne '')  { $bicepParams += " azureAllowedEmails=$AzureAllowedEmails" }

    $deployOutput = az deployment group create `
        --resource-group $ResourceGroupName `
        --template-file $BicepFile `
        --parameters $bicepParams `
        --query 'properties.outputs' `
        -o json 2>&1

    if ($LASTEXITCODE -ne 0) {
        Write-Error "Bicep deployment failed:`n$deployOutput"
        exit 1
    }

    Write-Host "Bicep deployment succeeded." -ForegroundColor Green

    # Parse outputs
    $outputs = $deployOutput | ConvertFrom-Json
    $AcrLoginServer = $outputs.acrLoginServer.value
    $AppServiceUrl  = $outputs.appServiceUrl.value
    $KvNameOut      = $outputs.keyVaultName.value

    Write-Host "  ACR Login Server: $AcrLoginServer" -ForegroundColor Green
    Write-Host "  App Service URL:  $AppServiceUrl"  -ForegroundColor Green
    Write-Host "  Key Vault:        $KvNameOut"       -ForegroundColor Green

} else {
    Write-Host "`n[SkipBicep] Skipping infrastructure deployment." -ForegroundColor Yellow

    # Derive ACR login server without Bicep output (query existing ACR)
    Write-Host "Querying existing ACR login server..." -ForegroundColor Yellow
    $AcrLoginServer = az acr show --name $AcrName --resource-group $ResourceGroupName --query loginServer -o tsv 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Could not query ACR '$AcrName'. Docker push may fail."
        $AcrLoginServer = "$AcrName.azurecr.io"
    }
    $AppServiceUrl = "https://$AppName.azurewebsites.net"
    Write-Host "  ACR Login Server: $AcrLoginServer" -ForegroundColor White
    Write-Host "  App Service URL:  $AppServiceUrl"  -ForegroundColor White
}

# ============================================================
# SECTION 4: DOCKER BUILD + PUSH
# ============================================================

if (-not $SkipDocker) {
    Write-Section "DOCKER BUILD + PUSH"

    $ImageTag = "$AcrLoginServer/${AppName}:latest"
    Write-Host "Image tag: $ImageTag" -ForegroundColor Yellow

    # ACR login
    Write-Host "Authenticating with ACR '$AcrName'..." -ForegroundColor Yellow
    az acr login --name $AcrName
    if ($LASTEXITCODE -ne 0) {
        Write-Error "ACR login failed for '$AcrName'."
        exit 1
    }
    Write-Host "ACR login succeeded." -ForegroundColor Green

    # Docker build from repo root
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $RepoRoot  = Split-Path -Parent $ScriptDir

    Write-Host "Building Docker image from: $RepoRoot" -ForegroundColor Yellow
    docker build -t $ImageTag $RepoRoot
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Docker build failed."
        exit 1
    }
    Write-Host "Docker build succeeded." -ForegroundColor Green

    # Docker push
    Write-Host "Pushing image to ACR..." -ForegroundColor Yellow
    docker push $ImageTag
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Docker push failed."
        exit 1
    }
    Write-Host "Docker push succeeded: $ImageTag" -ForegroundColor Green

} else {
    Write-Host "`n[SkipDocker] Skipping Docker build and push." -ForegroundColor Yellow
}

# ============================================================
# SECTION 5: APP SETTINGS CONFIGURATION
# ============================================================

if ($ConfigureSettings) {
    Write-Section "APP SETTINGS CONFIGURATION"

    Write-Host "Configuring Salesforce and Azure AD settings for '$AppName'." -ForegroundColor Yellow
    Write-Host "Press Enter to accept defaults shown in [brackets]. Leave optional fields blank to skip.`n" -ForegroundColor White

    $settings = [ordered]@{}

    # --- Salesforce OAuth (mandatory) ---
    Write-Host "--- Salesforce OAuth (mandatory) ---" -ForegroundColor Cyan

    $sfClientId = Prompt-WithDefault "SALESFORCE_CLIENT_ID (Connected App Consumer Key)"
    if ($sfClientId -ne '') { $settings['SALESFORCE_CLIENT_ID'] = $sfClientId }

    $sfClientSecret = Prompt-WithDefault "SALESFORCE_CLIENT_SECRET (Connected App Consumer Secret)" -Secret
    if ($sfClientSecret -ne '') { $settings['SALESFORCE_CLIENT_SECRET'] = $sfClientSecret }

    $defaultRedirectUri = "https://$AppName.azurewebsites.net"
    $sfRedirectUri = Prompt-WithDefault "SALESFORCE_REDIRECT_URI" -Default $defaultRedirectUri
    if ($sfRedirectUri -ne '') { $settings['SALESFORCE_REDIRECT_URI'] = $sfRedirectUri }

    $sfSandbox = Prompt-WithDefault "SALESFORCE_SANDBOX (true/false)" -Default 'false'
    if ($sfSandbox -ne '') { $settings['SALESFORCE_SANDBOX'] = $sfSandbox }

    # --- Salesforce OAuth (optional) ---
    Write-Host "`n--- Salesforce OAuth (optional) ---" -ForegroundColor Cyan

    $sfLoginUrl = Prompt-WithDefault "SALESFORCE_LOGIN_URL (custom domain, e.g. https://myorg.my.salesforce.com)" -Secret
    if ($sfLoginUrl -ne '') { $settings['SALESFORCE_LOGIN_URL'] = $sfLoginUrl }

    $sfOauthScopes = Prompt-WithDefault "SALESFORCE_OAUTH_SCOPES" -Default 'api refresh_token offline_access'
    if ($sfOauthScopes -ne '') { $settings['SALESFORCE_OAUTH_SCOPES'] = $sfOauthScopes }

    # --- Azure AD / MSAL (all optional) ---
    Write-Host "`n--- Azure AD / MSAL (all optional — leave blank to skip) ---" -ForegroundColor Cyan

    $azClientId = Prompt-WithDefault "AZURE_CLIENT_ID" -Secret
    if ($azClientId -ne '') {
        $settings['AZURE_CLIENT_ID'] = $azClientId

        $azTenantId = Prompt-WithDefault "AZURE_TENANT_ID" -Secret
        if ($azTenantId -ne '') { $settings['AZURE_TENANT_ID'] = $azTenantId }

        $azClientSecret = Prompt-WithDefault "AZURE_CLIENT_SECRET" -Secret
        if ($azClientSecret -ne '') { $settings['AZURE_CLIENT_SECRET'] = $azClientSecret }

        $azRedirectUri = Prompt-WithDefault "AZURE_REDIRECT_URI" -Default "https://$AppName.azurewebsites.net"
        if ($azRedirectUri -ne '') { $settings['AZURE_REDIRECT_URI'] = $azRedirectUri }

        $azAuthority = Prompt-WithDefault "AZURE_AUTHORITY (e.g. https://login.microsoftonline.com/TENANT_ID)" -Secret
        if ($azAuthority -ne '') { $settings['AZURE_AUTHORITY'] = $azAuthority }

        $azScopes = Prompt-WithDefault "AZURE_SCOPES (space-separated)" -Default 'User.Read'
        if ($azScopes -ne '') { $settings['AZURE_SCOPES'] = $azScopes }

        $azAllowedDomains = Prompt-WithDefault "AZURE_ALLOWED_DOMAINS (comma-separated, e.g. company.com)" -Secret
        if ($azAllowedDomains -ne '') { $settings['AZURE_ALLOWED_DOMAINS'] = $azAllowedDomains }

        $azAllowedEmails = Prompt-WithDefault "AZURE_ALLOWED_EMAILS (comma-separated specific users)" -Secret
        if ($azAllowedEmails -ne '') { $settings['AZURE_ALLOWED_EMAILS'] = $azAllowedEmails }
    } else {
        Write-Host "  Azure AD skipped (no AZURE_CLIENT_ID provided)." -ForegroundColor White
    }

    # --- Key Vault (auto-set, no prompt) ---
    Write-Host "`n--- Key Vault (auto-configured) ---" -ForegroundColor Cyan
    $settings['KEY_VAULT_NAME'] = $KeyVaultName
    Write-Host "  KEY_VAULT_NAME = $KeyVaultName (auto-set, no prompt needed)" -ForegroundColor Green

    # --- Debug (optional) ---
    Write-Host "`n--- Debug (optional) ---" -ForegroundColor Cyan
    $debugValue = Prompt-WithDefault "DEBUG (0 or 1, leave blank to disable)" -Default ''
    if ($debugValue -ne '') { $settings['DEBUG'] = $debugValue }

    # Build the --settings argument list
    if ($settings.Count -eq 0) {
        Write-Warning "No settings provided — skipping App Settings update."
    } else {
        Write-Host "`nApplying $($settings.Count) App Settings to '$AppName'..." -ForegroundColor Yellow

        # Build key=value array for az cli
        $settingArgs = @()
        foreach ($kv in $settings.GetEnumerator()) {
            $settingArgs += "$($kv.Key)=$($kv.Value)"
        }

        az webapp config appsettings set `
            --resource-group $ResourceGroupName `
            --name $AppName `
            --settings @settingArgs `
            --output none

        if ($LASTEXITCODE -ne 0) {
            Write-Error "Failed to apply App Settings."
            exit 1
        }
        Write-Host "App Settings applied successfully." -ForegroundColor Green
    }

} else {
    Write-Host "`n[ConfigureSettings not set] Skipping App Settings configuration." -ForegroundColor Yellow
    Write-Host "  Run with -ConfigureSettings to configure Salesforce/Azure AD credentials." -ForegroundColor White
}

# ============================================================
# SECTION 6: CONTAINER CONFIGURATION
# ============================================================

Write-Section "CONTAINER CONFIGURATION"

$ImageTag = "$AcrLoginServer/${AppName}:latest"
Write-Host "Configuring App Service to use image: $ImageTag" -ForegroundColor Yellow

az webapp config container set `
    --resource-group $ResourceGroupName `
    --name $AppName `
    --docker-custom-image-name $ImageTag `
    --output none

if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to configure container image on App Service."
    exit 1
}
Write-Host "Container configuration applied." -ForegroundColor Green

# ============================================================
# SECTION 7: RESTART + HEALTH VERIFICATION
# ============================================================

Write-Section "RESTART + HEALTH VERIFICATION"

Write-Host "Restarting App Service '$AppName'..." -ForegroundColor Yellow
az webapp restart --resource-group $ResourceGroupName --name $AppName --output none
if ($LASTEXITCODE -ne 0) {
    Write-Warning "Restart command returned non-zero. The app may still be starting."
}
Write-Host "Restart initiated." -ForegroundColor Green

$HealthUrl = "https://$AppName.azurewebsites.net/_stcore/health"
$MaxAttempts = 10
$RetryDelaySecs = 30

Write-Host "`nPolling health endpoint: $HealthUrl" -ForegroundColor Yellow
Write-Host "Up to $MaxAttempts attempts, ${RetryDelaySecs}s between retries..." -ForegroundColor White

$healthy = $false
for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
    Write-Host "  Attempt $attempt/$MaxAttempts..." -ForegroundColor White -NoNewline
    try {
        $response = Invoke-WebRequest -Uri $HealthUrl -UseBasicParsing -TimeoutSec 15 -ErrorAction Stop
        $body = $response.Content.Trim()
        if ($response.StatusCode -eq 200 -and $body -eq 'ok') {
            Write-Host " HEALTHY (200 ok)" -ForegroundColor Green
            $healthy = $true
            break
        } else {
            Write-Host " Status=$($response.StatusCode) Body='$body'" -ForegroundColor Yellow
        }
    } catch {
        Write-Host " Failed: $($_.Exception.Message)" -ForegroundColor Red
    }

    if ($attempt -lt $MaxAttempts) {
        Write-Host "  Waiting ${RetryDelaySecs}s..." -ForegroundColor White
        Start-Sleep -Seconds $RetryDelaySecs
    }
}

# ============================================================
# FINAL STATUS
# ============================================================

Write-Section "DEPLOYMENT COMPLETE"

if ($healthy) {
    Write-Host "SUCCESS: App Service is healthy!" -ForegroundColor Green
} else {
    Write-Warning "Health check did not return 'ok' after $MaxAttempts attempts."
    Write-Warning "The app may still be starting. Check logs with:"
    Write-Warning "  az webapp log tail --resource-group $ResourceGroupName --name $AppName"
}

Write-Host "`nApp Service URL: https://$AppName.azurewebsites.net" -ForegroundColor Cyan
Write-Host "View logs:       az webapp log tail --resource-group $ResourceGroupName --name $AppName" -ForegroundColor White
Write-Host "Portal:          https://portal.azure.com/#resource/subscriptions/$($account.id)/resourceGroups/$ResourceGroupName/providers/Microsoft.Web/sites/$AppName/overview" -ForegroundColor White
