<#
.SYNOPSIS
    Deploy the AE Dashboard to Azure App Service (zip deploy).

.DESCRIPTION
    Two-step deployment:
      1. Deploy Bicep infrastructure (infra/main.bicep)
      2. Zip-deploy the application code to Azure App Service

.PARAMETER ResourceGroupName
    (Mandatory) Existing Azure resource group.

.PARAMETER AppName
    (Mandatory) Base name for Azure resources (e.g. "ae-dashboard").

.PARAMETER AppServicePlanId
    (Mandatory) Full resource ID of the shared App Service Plan.
    Example: /subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.Web/serverfarms/<plan>

.PARAMETER Location
    Azure region. Defaults to 'eastus'.

.PARAMETER AzureAdClientId
    Azure AD app registration client ID.

.PARAMETER AzureAdTenantId
    Azure AD tenant ID.

.PARAMETER AzureAdClientSecret
    Azure AD client secret.

.PARAMETER AzureAllowedDomains
    Comma-separated allowed domains.

.PARAMETER AzureAllowedEmails
    Comma-separated allowed emails.

.PARAMETER SkipInfra
    Skip Bicep infrastructure deployment.

.PARAMETER SkipDeploy
    Skip application code deployment.

.PARAMETER ConfigureSettings
    Interactively configure App Settings (Salesforce, Azure AD).

.EXAMPLE
    .\deploy.ps1 -ResourceGroupName "doldata-rg" -AppName "ae-dashboard" `
        -AppServicePlanId "/subscriptions/.../providers/Microsoft.Web/serverfarms/doldata-lead-gen-dev-plan"

.EXAMPLE
    .\deploy.ps1 -ResourceGroupName "doldata-rg" -AppName "ae-dashboard" `
        -AppServicePlanId "..." -SkipInfra
#>

[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory)] [string]$ResourceGroupName,
    [Parameter(Mandatory)] [string]$AppName,
    [Parameter(Mandatory)] [string]$AppServicePlanId,
    [string]$Location = 'eastus',
    [string]$AzureAdClientId = '',
    [string]$AzureAdTenantId = '',
    [string]$AzureAdClientSecret = '',
    [string]$AzureAllowedDomains = '',
    [string]$AzureAllowedEmails = '',
    [switch]$SkipInfra,
    [switch]$SkipDeploy,
    [switch]$ConfigureSettings
)

$ErrorActionPreference = 'Stop'

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
    if ($value -eq '' -and $Default -ne '') { return $Default }
    return $value
}

# ============================================================
# PREREQUISITES
# ============================================================

Write-Section "PREREQUISITES CHECK"

Write-Host "Checking Azure CLI..." -ForegroundColor Yellow
if (-not (Get-Command 'az' -ErrorAction SilentlyContinue)) {
    Write-Error "Azure CLI ('az') not found. Install from https://docs.microsoft.com/cli/azure/install-azure-cli"
    exit 1
}
$azVersion = az version --query '"azure-cli"' -o tsv 2>&1
Write-Host "  az CLI version: $azVersion" -ForegroundColor Green

Write-Host "Checking Azure login status..." -ForegroundColor Yellow
$accountJson = az account show -o json 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "Not logged into Azure CLI. Run 'az login' first."
    exit 1
}
$account = $accountJson | ConvertFrom-Json
Write-Host "  Logged in as: $($account.user.name)" -ForegroundColor Green
Write-Host "  Subscription: $($account.name) ($($account.id))" -ForegroundColor Green

# ============================================================
# RESOURCE NAMES
# ============================================================

Write-Section "RESOURCE NAMES"

$KeyVaultName = "$AppName-kv"

Write-Host "  App Service:      $AppName"           -ForegroundColor White
Write-Host "  Key Vault:        $KeyVaultName"       -ForegroundColor White
Write-Host "  Resource Group:   $ResourceGroupName"  -ForegroundColor White
Write-Host "  Plan (shared):    $AppServicePlanId"   -ForegroundColor White

# ============================================================
# STEP 1: BICEP DEPLOYMENT
# ============================================================

Write-Section "Step 1: Deploy Infrastructure"

if ($SkipInfra) {
    Write-Host "[SKIP] -SkipInfra specified." -ForegroundColor Yellow
} else {
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $RepoRoot  = Split-Path -Parent $ScriptDir
    $BicepFile = Join-Path $RepoRoot 'infra' 'main.bicep'

    if (-not (Test-Path $BicepFile)) {
        Write-Error "Bicep template not found at: $BicepFile"
        exit 1
    }

    Write-Host "Deploying Bicep template: $BicepFile" -ForegroundColor Yellow

    $bicepParams = "appName=$AppName location=$Location appServicePlanId=$AppServicePlanId"
    if ($AzureAdClientId -ne '')     { $bicepParams += " azureAdClientId=$AzureAdClientId" }
    if ($AzureAdTenantId -ne '')     { $bicepParams += " azureAdTenantId=$AzureAdTenantId" }
    if ($AzureAdClientSecret -ne '') { $bicepParams += " azureAdClientSecret=$AzureAdClientSecret" }
    if ($AzureAllowedDomains -ne '') { $bicepParams += " azureAllowedDomains=$AzureAllowedDomains" }
    if ($AzureAllowedEmails -ne '')  { $bicepParams += " azureAllowedEmails=$AzureAllowedEmails" }

    if ($PSCmdlet.ShouldProcess("$ResourceGroupName", "az deployment group create")) {
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

        $outputs = $deployOutput | ConvertFrom-Json
        $AppServiceUrl = $outputs.appServiceUrl.value
        $KvNameOut     = $outputs.keyVaultName.value

        Write-Host "[OK] Bicep deployment succeeded." -ForegroundColor Green
        Write-Host "  App Service URL: $AppServiceUrl" -ForegroundColor Green
        Write-Host "  Key Vault:       $KvNameOut"      -ForegroundColor Green
    }
}

# ============================================================
# STEP 2: ZIP DEPLOY
# ============================================================

Write-Section "Step 2: Deploy Application Code"

if ($SkipDeploy) {
    Write-Host "[SKIP] -SkipDeploy specified." -ForegroundColor Yellow
} else {
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $RepoRoot  = Split-Path -Parent $ScriptDir
    $TempZip   = [System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), "ae-deploy-$(Get-Random).zip")

    Write-Host "Packaging application from: $RepoRoot" -ForegroundColor Yellow

    $ExcludePatterns = @(
        [System.IO.Path]::Combine($RepoRoot, '.git'),
        [System.IO.Path]::Combine($RepoRoot, '.venv'),
        [System.IO.Path]::Combine($RepoRoot, 'venv'),
        [System.IO.Path]::Combine($RepoRoot, '.env'),
        [System.IO.Path]::Combine($RepoRoot, '.env.local'),
        [System.IO.Path]::Combine($RepoRoot, 'infra'),
        [System.IO.Path]::Combine($RepoRoot, 'scripts'),
        [System.IO.Path]::Combine($RepoRoot, 'docs'),
        [System.IO.Path]::Combine($RepoRoot, 'data'),
        [System.IO.Path]::Combine($RepoRoot, '.sisyphus'),
        [System.IO.Path]::Combine($RepoRoot, 'deploy-package')
    )

    $FilesToZip = Get-ChildItem -Path $RepoRoot -Recurse -File | Where-Object {
        $filePath = $_.FullName

        if ($filePath -match '__pycache__') { return $false }
        if ($filePath -match '\.pyc$')      { return $false }
        if ($_.Extension -eq '.zip')         { return $false }
        if ($_.Extension -eq '.md')          { return $false }

        foreach ($ex in $ExcludePatterns) {
            if ($filePath -eq $ex) { return $false }
            $exDir = $ex.TrimEnd([System.IO.Path]::DirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar
            if ($filePath.StartsWith($exDir, [System.StringComparison]::OrdinalIgnoreCase)) { return $false }
        }

        return $true
    }

    Write-Host "  Files selected: $($FilesToZip.Count)" -ForegroundColor Gray

    if ($PSCmdlet.ShouldProcess($TempZip, "Compress-Archive")) {
        $StageDir = [System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), "ae-stage-$(Get-Random)")
        New-Item -ItemType Directory -Path $StageDir | Out-Null

        try {
            foreach ($file in $FilesToZip) {
                $relative = $file.FullName.Substring($RepoRoot.Length).TrimStart([System.IO.Path]::DirectorySeparatorChar)
                $dest = [System.IO.Path]::Combine($StageDir, $relative)
                $destDir = [System.IO.Path]::GetDirectoryName($dest)
                if (-not (Test-Path $destDir)) {
                    New-Item -ItemType Directory -Path $destDir -Force | Out-Null
                }
                Copy-Item -LiteralPath $file.FullName -Destination $dest
            }

            Compress-Archive -Path "$StageDir${[System.IO.Path]::DirectorySeparatorChar}*" -DestinationPath $TempZip -Force
            Write-Host "  Zip: $TempZip ($([math]::Round((Get-Item $TempZip).Length / 1MB, 1)) MB)" -ForegroundColor Gray
        } finally {
            Remove-Item -Recurse -Force $StageDir -ErrorAction SilentlyContinue
        }

        Write-Host "Deploying zip to '$AppName' ..." -ForegroundColor Yellow

        az webapp deploy `
            --resource-group $ResourceGroupName `
            --name $AppName `
            --src-path $TempZip `
            --type zip `
            --async false

        $deployExitCode = $LASTEXITCODE
        Remove-Item -LiteralPath $TempZip -ErrorAction SilentlyContinue

        if ($deployExitCode -ne 0) {
            Write-Error "Zip deployment failed (exit $deployExitCode)."
            exit $deployExitCode
        }

        Write-Host "[OK] Application code deployed." -ForegroundColor Green
    }
}

# ============================================================
# STEP 3: APP SETTINGS CONFIGURATION
# ============================================================

if ($ConfigureSettings) {
    Write-Section "Step 3: App Settings Configuration"

    Write-Host "Press Enter to accept defaults in [brackets]. Leave optional fields blank to skip.`n" -ForegroundColor White

    $settings = [ordered]@{}

    # --- Salesforce OAuth ---
    Write-Host "--- Salesforce OAuth (mandatory) ---" -ForegroundColor Cyan

    $sfClientId = Prompt-WithDefault "SALESFORCE_CLIENT_ID (Connected App Consumer Key)"
    if ($sfClientId -ne '') { $settings['SALESFORCE_CLIENT_ID'] = $sfClientId }

    $sfClientSecret = Prompt-WithDefault "SALESFORCE_CLIENT_SECRET" -Secret
    if ($sfClientSecret -ne '') { $settings['SALESFORCE_CLIENT_SECRET'] = $sfClientSecret }

    $defaultRedirectUri = "https://$AppName.azurewebsites.net"
    $sfRedirectUri = Prompt-WithDefault "SALESFORCE_REDIRECT_URI" -Default $defaultRedirectUri
    if ($sfRedirectUri -ne '') { $settings['SALESFORCE_REDIRECT_URI'] = $sfRedirectUri }

    $sfSandbox = Prompt-WithDefault "SALESFORCE_SANDBOX (true/false)" -Default 'false'
    if ($sfSandbox -ne '') { $settings['SALESFORCE_SANDBOX'] = $sfSandbox }

    # --- Salesforce optional ---
    Write-Host "`n--- Salesforce OAuth (optional) ---" -ForegroundColor Cyan

    $sfLoginUrl = Prompt-WithDefault "SALESFORCE_LOGIN_URL (custom domain)" -Secret
    if ($sfLoginUrl -ne '') { $settings['SALESFORCE_LOGIN_URL'] = $sfLoginUrl }

    $sfOauthScopes = Prompt-WithDefault "SALESFORCE_OAUTH_SCOPES" -Default 'api refresh_token offline_access'
    if ($sfOauthScopes -ne '') { $settings['SALESFORCE_OAUTH_SCOPES'] = $sfOauthScopes }

    # --- Azure AD / MSAL ---
    Write-Host "`n--- Azure AD / MSAL (optional) ---" -ForegroundColor Cyan

    $azClientId = Prompt-WithDefault "AZURE_CLIENT_ID" -Secret
    if ($azClientId -ne '') {
        $settings['AZURE_CLIENT_ID'] = $azClientId

        $azTenantId = Prompt-WithDefault "AZURE_TENANT_ID" -Secret
        if ($azTenantId -ne '') { $settings['AZURE_TENANT_ID'] = $azTenantId }

        $azClientSecret = Prompt-WithDefault "AZURE_CLIENT_SECRET" -Secret
        if ($azClientSecret -ne '') { $settings['AZURE_CLIENT_SECRET'] = $azClientSecret }

        $azRedirectUri = Prompt-WithDefault "AZURE_REDIRECT_URI" -Default "https://$AppName.azurewebsites.net"
        if ($azRedirectUri -ne '') { $settings['AZURE_REDIRECT_URI'] = $azRedirectUri }

        $azAuthority = Prompt-WithDefault "AZURE_AUTHORITY" -Secret
        if ($azAuthority -ne '') { $settings['AZURE_AUTHORITY'] = $azAuthority }

        $azScopes = Prompt-WithDefault "AZURE_SCOPES" -Default 'User.Read'
        if ($azScopes -ne '') { $settings['AZURE_SCOPES'] = $azScopes }

        $azAllowedDomains = Prompt-WithDefault "AZURE_ALLOWED_DOMAINS (comma-separated)" -Secret
        if ($azAllowedDomains -ne '') { $settings['AZURE_ALLOWED_DOMAINS'] = $azAllowedDomains }

        $azAllowedEmails = Prompt-WithDefault "AZURE_ALLOWED_EMAILS (comma-separated)" -Secret
        if ($azAllowedEmails -ne '') { $settings['AZURE_ALLOWED_EMAILS'] = $azAllowedEmails }
    } else {
        Write-Host "  Azure AD skipped." -ForegroundColor White
    }

    # --- Key Vault ---
    Write-Host "`n--- Key Vault (auto-configured) ---" -ForegroundColor Cyan
    $settings['KEY_VAULT_NAME'] = $KeyVaultName
    Write-Host "  KEY_VAULT_NAME = $KeyVaultName" -ForegroundColor Green

    if ($settings.Count -gt 0) {
        Write-Host "`nApplying $($settings.Count) App Settings..." -ForegroundColor Yellow

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
        Write-Host "[OK] App Settings applied." -ForegroundColor Green
    }
} else {
    Write-Host "`n[ConfigureSettings not set] Run with -ConfigureSettings to set credentials." -ForegroundColor Yellow
}

# ============================================================
# STEP 4: HEALTH VERIFICATION
# ============================================================

Write-Section "Step 4: Health Verification"

$HealthUrl = "https://$AppName.azurewebsites.net/_stcore/health"
$MaxAttempts = 10
$RetryDelaySecs = 30

Write-Host "Polling: $HealthUrl (up to $MaxAttempts attempts, ${RetryDelaySecs}s interval)" -ForegroundColor Yellow

$healthy = $false
for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
    Write-Host "  Attempt $attempt/$MaxAttempts..." -ForegroundColor White -NoNewline
    try {
        $response = Invoke-WebRequest -Uri $HealthUrl -UseBasicParsing -TimeoutSec 15 -ErrorAction Stop
        $body = $response.Content.Trim()
        if ($response.StatusCode -eq 200 -and $body -eq 'ok') {
            Write-Host " HEALTHY" -ForegroundColor Green
            $healthy = $true
            break
        } else {
            Write-Host " Status=$($response.StatusCode) Body='$body'" -ForegroundColor Yellow
        }
    } catch {
        Write-Host " $($_.Exception.Message)" -ForegroundColor Red
    }
    if ($attempt -lt $MaxAttempts) {
        Start-Sleep -Seconds $RetryDelaySecs
    }
}

# ============================================================
# SUMMARY
# ============================================================

Write-Section "Deployment Complete"

if ($healthy) {
    Write-Host "SUCCESS: App is healthy!" -ForegroundColor Green
} else {
    Write-Warning "Health check did not pass after $MaxAttempts attempts."
    Write-Warning "Check logs: az webapp log tail --resource-group $ResourceGroupName --name $AppName"
}

Write-Host "`nApp URL: https://$AppName.azurewebsites.net" -ForegroundColor Cyan
Write-Host "Logs:    az webapp log tail --resource-group $ResourceGroupName --name $AppName" -ForegroundColor White
