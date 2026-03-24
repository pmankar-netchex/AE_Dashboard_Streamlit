#!/usr/bin/env bash
# After a successful Bicep deployment: show outputs, optionally configure GitHub Actions,
# trigger the deploy workflow, and/or push Salesforce-related env vars to the Container App.
#
# Prerequisites (install as needed):
#   - Azure CLI (az), logged in: az login
#   - Optional: GitHub CLI (gh), logged in: gh auth login
#   - Optional: .env at repo root with Salesforce vars (never committed)
#
# Examples:
#   ./scripts/azure_post_deploy_setup.sh --resource-group doldata-rg --deployment-name ae-dashboard-deployment1
#   ./scripts/azure_post_deploy_setup.sh -g doldata-rg -d ae-dashboard-deployment1 --set-github-vars --repo OWNER/REPO
#   export AZURE_CLIENT_ID=... AZURE_TENANT_ID=... AZURE_SUBSCRIPTION_ID=...
#   ./scripts/azure_post_deploy_setup.sh -g doldata-rg -d ae-dashboard-deployment1 --set-github-secrets --repo OWNER/REPO
#   ./scripts/azure_post_deploy_setup.sh -g doldata-rg -d ae-dashboard-deployment1 --apply-dotenv
#   ./scripts/azure_post_deploy_setup.sh -g doldata-rg -d ae-dashboard-deployment1 --all --repo OWNER/REPO --dotenv ../.env

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-doldata-rg}"
DEPLOYMENT_NAME="${AZ_DEPLOYMENT_NAME:-ae-dashboard-deployment1}"
GITHUB_REPO="${GITHUB_REPO:-}"
DOTENV_PATH="${DOTENV_PATH:-$PROJECT_ROOT/.env}"

SET_GITHUB_VARS=0
SET_GITHUB_SECRETS=0
TRIGGER_WORKFLOW=0
APPLY_DOTENV=0
PRINT_ONLY=0

usage() {
  sed -n '1,25p' "$0" | tail -n +2
  cat <<'EOF'

Options:
  -g, --resource-group NAME   Azure resource group (default: AZURE_RESOURCE_GROUP or doldata-rg)
  -d, --deployment-name NAME  Deployment name from az deployment group create (default: ae-dashboard-deployment1)
  --repo OWNER/REPO           GitHub repository for gh (default: GITHUB_REPO env or gh repo view --json nameWithOwner)
  --dotenv PATH               Path to .env for --apply-dotenv / --all (default: repo root .env)

  --print-only                Only print deployment outputs and next-step hints (default if no action flags)
  --set-github-vars           gh variable set AZURE_RESOURCE_GROUP, ACR_NAME, CONTAINER_APP_NAME
  --set-github-secrets        gh secret set AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_SUBSCRIPTION_ID from environment
  --trigger-deploy            gh workflow run "Deploy to Azure Container Apps" on main
  --apply-dotenv              az containerapp secret + update from .env (Salesforce vars)
  --all                       --set-github-vars --set-github-secrets --trigger-deploy --apply-dotenv

  -h, --help                  Show this help

For --set-github-secrets, export these first (do not commit them):
  export AZURE_CLIENT_ID=...
  export AZURE_TENANT_ID=...
  export AZURE_SUBSCRIPTION_ID=...
EOF
}

require_az() {
  command -v az >/dev/null 2>&1 || {
    echo "error: Azure CLI (az) not found" >&2
    exit 1
  }
}

require_gh() {
  command -v gh >/dev/null 2>&1 || {
    echo "error: GitHub CLI (gh) not found (install: https://cli.github.com/)" >&2
    exit 1
  }
  gh auth status >/dev/null 2>&1 || {
    echo "error: gh not authenticated. Run: gh auth login" >&2
    exit 1
  }
}

resolve_repo() {
  if [[ -n "$GITHUB_REPO" ]]; then
    echo "$GITHUB_REPO"
    return
  fi
  local slug
  slug="$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || true)"
  if [[ -n "$slug" ]]; then
    echo "$slug"
    return
  fi
  echo ""
}

ensure_github_repo() {
  require_gh
  REPO_SLUG="$(resolve_repo)"
  if [[ -z "$REPO_SLUG" ]]; then
    echo "error: pass --repo OWNER/REPO or set GITHUB_REPO, or run from a git directory with gh auth." >&2
    exit 1
  fi
  REPO_FLAG=(--repo "$REPO_SLUG")
}

# GitHub often returns HTTP 404 (not 403) for private repos or tokens without access.
print_github_actions_404_help() {
  cat >&2 <<EOF

GitHub Actions API returned 404 for: repos/${REPO_SLUG}/actions/variables

Personal (user-owned) repo — check first:
  • OWNER in OWNER/REPO must be your GitHub username exactly as in the URL:
      https://github.com/OWNER/REPO  →  use: --repo OWNER/REPO
    (If you used an org name by mistake, switch to your username.)
  • This shell must be logged into GitHub as that user:
      gh auth status
      gh repo view "${REPO_SLUG}"
  • Private repo: classic PAT needs the \"repo\" scope; fine-grained PAT needs
    \"Variables\" (read/write) on this repository.

Organization repo — also check:
  • SAML SSO: https://github.com/settings/connections/applications
    → Authorize the GitHub CLI / token for that organization.

Manual fallback: Repo → Settings → Secrets and variables → Actions → Variables (tab)
EOF
}

assert_github_actions_variables_api() {
  if gh api "repos/${REPO_SLUG}/actions/variables" --method GET >/dev/null 2>&1; then
    return 0
  fi
  echo "error: cannot reach GitHub Actions variables API for '${REPO_SLUG}'." >&2
  print_github_actions_404_help
  exit 1
}

gh_variable_set_or_fail() {
  local var_name="$1" var_value="$2"
  if ! gh variable set "$var_name" --body "$var_value" "${REPO_FLAG[@]}"; then
    echo "error: failed to set GitHub variable '${var_name}'." >&2
    print_github_actions_404_help
    exit 1
  fi
}

get_output() {
  local key="$1"
  az deployment group show \
    --resource-group "$RESOURCE_GROUP" \
    --name "$DEPLOYMENT_NAME" \
    --query "properties.outputs.${key}.value" \
    -o tsv 2>/dev/null || true
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -g|--resource-group)
      RESOURCE_GROUP="$2"
      shift 2
      ;;
    -d|--deployment-name)
      DEPLOYMENT_NAME="$2"
      shift 2
      ;;
    --repo)
      GITHUB_REPO="$2"
      shift 2
      ;;
    --dotenv)
      DOTENV_PATH="$2"
      shift 2
      ;;
    --print-only)
      PRINT_ONLY=1
      shift
      ;;
    --set-github-vars)
      SET_GITHUB_VARS=1
      shift
      ;;
    --set-github-secrets)
      SET_GITHUB_SECRETS=1
      shift
      ;;
    --trigger-deploy)
      TRIGGER_WORKFLOW=1
      shift
      ;;
    --apply-dotenv)
      APPLY_DOTENV=1
      shift
      ;;
    --all)
      SET_GITHUB_VARS=1
      SET_GITHUB_SECRETS=1
      TRIGGER_WORKFLOW=1
      APPLY_DOTENV=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

ACTION_SUMMARY=$((SET_GITHUB_VARS + SET_GITHUB_SECRETS + TRIGGER_WORKFLOW + APPLY_DOTENV))
if [[ "$PRINT_ONLY" -eq 1 ]] || [[ "$ACTION_SUMMARY" -eq 0 ]]; then
  PRINT_ONLY=1
fi

require_az

echo "==> Deployment: $DEPLOYMENT_NAME in resource group: $RESOURCE_GROUP"
if ! az group show --name "$RESOURCE_GROUP" &>/dev/null; then
  echo "error: resource group not found: $RESOURCE_GROUP" >&2
  exit 1
fi

if ! az deployment group show --resource-group "$RESOURCE_GROUP" --name "$DEPLOYMENT_NAME" &>/dev/null; then
  echo "error: deployment not found: $DEPLOYMENT_NAME" >&2
  exit 1
fi

ACR_NAME="$(get_output acrName)"
CONTAINER_APP_NAME="$(get_output containerAppName)"
CONTAINER_FQDN="$(get_output containerAppFqdn)"
ACR_LOGIN_SERVER="$(get_output acrLoginServer)"

if [[ -z "$ACR_NAME" || -z "$CONTAINER_APP_NAME" ]]; then
  echo "error: could not read acrName / containerAppName from deployment outputs." >&2
  echo "       Check deployment name and that the template defines these outputs." >&2
  exit 1
fi

echo ""
echo "Outputs (save these):"
echo "  ACR_NAME=$ACR_NAME"
echo "  CONTAINER_APP_NAME=$CONTAINER_APP_NAME"
echo "  ACR_LOGIN_SERVER=$ACR_LOGIN_SERVER"
echo "  CONTAINER_FQDN=$CONTAINER_FQDN"
echo ""
echo "App URL: https://${CONTAINER_FQDN}"
echo ""
echo "Salesforce: set Connected App callback URL to match SALESFORCE_REDIRECT_URI (often https://${CONTAINER_FQDN}/ or without trailing slash — exact match required)."
echo ""

if [[ "$PRINT_ONLY" -eq 1 ]] && [[ "$ACTION_SUMMARY" -eq 0 ]]; then
  echo "Next (manual or re-run with flags):"
  echo "  1. GitHub → Settings → Actions → Variables: AZURE_RESOURCE_GROUP, ACR_NAME, CONTAINER_APP_NAME"
  echo "  2. GitHub → Secrets: AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_SUBSCRIPTION_ID (OIDC app registration)"
  echo "  3. Run workflow \"Deploy to Azure Container Apps\" or push to main"
  echo "  4. Container App env vars / secrets for Salesforce (see README)"
  echo ""
  echo "Automate with this script, e.g.:"
  echo "  $0 -g $RESOURCE_GROUP -d $DEPLOYMENT_NAME --set-github-vars --repo OWNER/REPO"
  echo "  export AZURE_CLIENT_ID=... AZURE_TENANT_ID=... AZURE_SUBSCRIPTION_ID=..."
  echo "  $0 -g $RESOURCE_GROUP -d $DEPLOYMENT_NAME --set-github-secrets --repo OWNER/REPO"
  echo "  $0 -g $RESOURCE_GROUP -d $DEPLOYMENT_NAME --trigger-deploy --repo OWNER/REPO"
  echo "  $0 -g $RESOURCE_GROUP -d $DEPLOYMENT_NAME --apply-dotenv --dotenv $DOTENV_PATH"
  exit 0
fi

GITHUB_ACTIONS=$((SET_GITHUB_VARS + SET_GITHUB_SECRETS + TRIGGER_WORKFLOW))
if [[ "$GITHUB_ACTIONS" -gt 0 ]]; then
  ensure_github_repo
fi

if [[ "$SET_GITHUB_VARS" -eq 1 ]]; then
  echo "==> Setting GitHub Actions variables on ${REPO_SLUG}..."
  assert_github_actions_variables_api
  gh_variable_set_or_fail AZURE_RESOURCE_GROUP "$RESOURCE_GROUP"
  gh_variable_set_or_fail ACR_NAME "$ACR_NAME"
  gh_variable_set_or_fail CONTAINER_APP_NAME "$CONTAINER_APP_NAME"
  echo "    Done."
fi

if [[ "$SET_GITHUB_SECRETS" -eq 1 ]]; then
  [[ -n "${AZURE_CLIENT_ID:-}" ]] || {
    echo "error: AZURE_CLIENT_ID not set" >&2
    exit 1
  }
  [[ -n "${AZURE_TENANT_ID:-}" ]] || {
    echo "error: AZURE_TENANT_ID not set" >&2
    exit 1
  }
  [[ -n "${AZURE_SUBSCRIPTION_ID:-}" ]] || {
    echo "error: AZURE_SUBSCRIPTION_ID not set" >&2
    exit 1
  }
  echo "==> Setting GitHub Actions secrets (OIDC) on ${REPO_SLUG}..."
  gh secret set AZURE_CLIENT_ID --body "$AZURE_CLIENT_ID" "${REPO_FLAG[@]}"
  gh secret set AZURE_TENANT_ID --body "$AZURE_TENANT_ID" "${REPO_FLAG[@]}"
  gh secret set AZURE_SUBSCRIPTION_ID --body "$AZURE_SUBSCRIPTION_ID" "${REPO_FLAG[@]}"
  echo "    Done."
fi

if [[ "$TRIGGER_WORKFLOW" -eq 1 ]]; then
  echo "==> Triggering workflow \"Deploy to Azure Container Apps\" (branch main)..."
  gh workflow run "Deploy to Azure Container Apps" --ref main "${REPO_FLAG[@]}"
  echo "    Submitted. Watch: gh run watch --repo $REPO_SLUG"
fi

if [[ "$APPLY_DOTENV" -eq 1 ]]; then
  if [[ ! -f "$DOTENV_PATH" ]]; then
    echo "error: .env not found: $DOTENV_PATH" >&2
    exit 1
  fi
  echo "==> Loading $DOTENV_PATH (values not printed)..."

  # shellcheck disable=SC1090
  set -a
  # shellcheck source=/dev/null
  source "$DOTENV_PATH"
  set +a

  SECRET_ARGS=()
  ENV_VARS=()

  if [[ -n "${SALESFORCE_CLIENT_SECRET:-}" ]]; then
    SECRET_ARGS+=("salesforce-client-secret=${SALESFORCE_CLIENT_SECRET}")
  fi

  [[ -n "${SALESFORCE_CLIENT_ID:-}" ]] && ENV_VARS+=("SALESFORCE_CLIENT_ID=${SALESFORCE_CLIENT_ID}")
  [[ -n "${SALESFORCE_REDIRECT_URI:-}" ]] && ENV_VARS+=("SALESFORCE_REDIRECT_URI=${SALESFORCE_REDIRECT_URI}")
  [[ -n "${SALESFORCE_SANDBOX:-}" ]] && ENV_VARS+=("SALESFORCE_SANDBOX=${SALESFORCE_SANDBOX}")
  [[ -n "${SALESFORCE_LOGIN_URL:-}" ]] && ENV_VARS+=("SALESFORCE_LOGIN_URL=${SALESFORCE_LOGIN_URL}")
  [[ -n "${SALESFORCE_OAUTH_SCOPES:-}" ]] && ENV_VARS+=("SALESFORCE_OAUTH_SCOPES=${SALESFORCE_OAUTH_SCOPES}")
  [[ -n "${SALESFORCE_USERNAME:-}" ]] && ENV_VARS+=("SALESFORCE_USERNAME=${SALESFORCE_USERNAME}")
  [[ -n "${SALESFORCE_PASSWORD:-}" ]] && ENV_VARS+=("SALESFORCE_PASSWORD=${SALESFORCE_PASSWORD}")
  [[ -n "${SALESFORCE_SECURITY_TOKEN:-}" ]] && ENV_VARS+=("SALESFORCE_SECURITY_TOKEN=${SALESFORCE_SECURITY_TOKEN}")

  if [[ ${#SECRET_ARGS[@]} -gt 0 ]]; then
    echo "==> Setting Container App secret(s)..."
    az containerapp secret set \
      --name "$CONTAINER_APP_NAME" \
      --resource-group "$RESOURCE_GROUP" \
      --secrets "${SECRET_ARGS[@]}"
  fi

  if [[ -n "${SALESFORCE_CLIENT_SECRET:-}" ]]; then
    ENV_VARS+=("SALESFORCE_CLIENT_SECRET=secretref:salesforce-client-secret")
  fi

  if [[ ${#ENV_VARS[@]} -eq 0 ]]; then
    echo "warning: no Salesforce-related variables found in .env; nothing to apply." >&2
  else
    echo "==> Updating Container App environment variables..."
    az containerapp update \
      --name "$CONTAINER_APP_NAME" \
      --resource-group "$RESOURCE_GROUP" \
      --set-env-vars "${ENV_VARS[@]}"
  fi

  echo "    Done."
fi

echo ""
echo "Finished."
