#!/usr/bin/env bash
# Option C: build the Docker image locally, push to ACR, update the Container App.
# Uses your interactive az login (or existing az session).
#
# Azure Container Apps runs linux/amd64. On Apple Silicon, a plain "docker build"
# produces arm64 images and the revision will fail. This script defaults to
#   docker build --platform linux/amd64
# or use --acr-build to compile in Azure (no local emulation).
#
# Run from the repository root (or any directory; script cds to repo root).
#
# Examples:
#   az login
#   ./scripts/deploy_containerapp_local.sh \
#     --resource-group doldata-rg \
#     --acr-name YOUR_ACR_NAME \
#     --app-name YOUR_CONTAINER_APP_NAME
#
#   # Fill names from an earlier Bicep deployment:
#   ./scripts/deploy_containerapp_local.sh \
#     --resource-group doldata-rg \
#     --from-deployment ae-dashboard-deployment1

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

IMAGE_NAME="${IMAGE_NAME:-ae-dashboard}"

RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-}"
ACR_NAME="${ACR_NAME:-}"
CONTAINER_APP_NAME="${CONTAINER_APP_NAME:-}"
DEPLOYMENT_NAME=""
IMAGE_TAG=""
USE_ACR_BUILD=0
# Target OS/arch for the image in ACR (Azure Container Apps = amd64).
DOCKER_PLATFORM="${DOCKER_PLATFORM:-linux/amd64}"

usage() {
  sed -n '1,20p' "$0" | tail -n +2
  cat <<'EOF'

Options:
  -g, --resource-group NAME   Resource group (or set AZURE_RESOURCE_GROUP)
  --acr-name NAME             ACR resource name (or set ACR_NAME)
  --app-name NAME             Container App name (or set CONTAINER_APP_NAME)
  --from-deployment NAME      Read acrName + containerAppName from this deployment in -g
  --tag TAG                   Image tag (default: short git SHA, or timestamp if not a git repo)
  --image-name NAME           Repository name in ACR (default: ae-dashboard)
  --acr-build                 Build in ACR with 'az acr build' (linux/amd64, no local Docker needed for build)
  --platform OS/ARCH         docker build target (default: linux/amd64). Ignored with --acr-build.

  -h, --help

Requires: az, and permission to push to ACR + update the Container App. Docker is required unless --acr-build.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -g|--resource-group)
      RESOURCE_GROUP="$2"
      shift 2
      ;;
    --acr-name)
      ACR_NAME="$2"
      shift 2
      ;;
    --app-name)
      CONTAINER_APP_NAME="$2"
      shift 2
      ;;
    --from-deployment)
      DEPLOYMENT_NAME="$2"
      shift 2
      ;;
    --tag)
      IMAGE_TAG="$2"
      shift 2
      ;;
    --image-name)
      IMAGE_NAME="$2"
      shift 2
      ;;
    --acr-build)
      USE_ACR_BUILD=1
      shift
      ;;
    --platform)
      DOCKER_PLATFORM="$2"
      shift 2
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

command -v az >/dev/null 2>&1 || {
  echo "error: Azure CLI (az) not found" >&2
  exit 1
}

# Pull the latest Table Storage state into queries_snapshot.json so the deploy
# doesn't leave live edits un-tracked. Fails closed when the caller hasn't set
# AZURE_STORAGE_CONNECTION_STRING — pass --skip-sync to bypass.
if [[ "${SKIP_SYNC:-0}" != "1" ]]; then
  if [[ -z "${AZURE_STORAGE_CONNECTION_STRING:-}" ]]; then
    echo "error: AZURE_STORAGE_CONNECTION_STRING not set (needed to export query snapshot)." >&2
    echo "       Set it, or pass SKIP_SYNC=1 to bypass (not recommended)." >&2
    exit 1
  fi
  echo "==> Exporting Table Storage queries -> queries_snapshot.json..."
  "${PYTHON:-python3}" "$PROJECT_ROOT/scripts/sync_queries.py" --export
fi
if [[ "$USE_ACR_BUILD" -eq 0 ]]; then
  command -v docker >/dev/null 2>&1 || {
    echo "error: docker not found (install Docker or use --acr-build)" >&2
    exit 1
  }
fi

[[ -n "$RESOURCE_GROUP" ]] || {
  echo "error: set --resource-group or AZURE_RESOURCE_GROUP" >&2
  exit 1
}

if [[ -n "$DEPLOYMENT_NAME" ]]; then
  ACR_NAME="$(az deployment group show \
    --resource-group "$RESOURCE_GROUP" \
    --name "$DEPLOYMENT_NAME" \
    --query "properties.outputs.acrName.value" -o tsv 2>/dev/null || true)"
  CONTAINER_APP_NAME="$(az deployment group show \
    --resource-group "$RESOURCE_GROUP" \
    --name "$DEPLOYMENT_NAME" \
    --query "properties.outputs.containerAppName.value" -o tsv 2>/dev/null || true)"
  if [[ -z "$ACR_NAME" || -z "$CONTAINER_APP_NAME" ]]; then
    echo "error: could not read acrName/containerAppName from deployment '$DEPLOYMENT_NAME'" >&2
    exit 1
  fi
fi

[[ -n "$ACR_NAME" ]] || {
  echo "error: set --acr-name, ACR_NAME, or --from-deployment" >&2
  exit 1
}
[[ -n "$CONTAINER_APP_NAME" ]] || {
  echo "error: set --app-name, CONTAINER_APP_NAME, or --from-deployment" >&2
  exit 1
}

if [[ -z "$IMAGE_TAG" ]]; then
  if tag="$(git -C "$PROJECT_ROOT" rev-parse --short HEAD 2>/dev/null)"; then
    IMAGE_TAG="$tag"
  else
    IMAGE_TAG="local-$(date +%Y%m%d%H%M%S)"
  fi
fi

echo "==> Context: subscription $(az account show --query name -o tsv) ($(az account show --query id -o tsv))"
echo "==> Target: RG=$RESOURCE_GROUP ACR=$ACR_NAME APP=$CONTAINER_APP_NAME IMAGE=${IMAGE_NAME}:$IMAGE_TAG"

az extension add --name containerapp --upgrade 2>/dev/null || az extension update --name containerapp

ACR_LOGIN_SERVER="$(az acr show -n "$ACR_NAME" --resource-group "$RESOURCE_GROUP" --query loginServer -o tsv)"

if [[ "$USE_ACR_BUILD" -eq 1 ]]; then
  echo "==> az acr build (linux/amd64 in Azure, context: $PROJECT_ROOT)..."
  az acr build \
    --registry "$ACR_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    -t "${IMAGE_NAME}:${IMAGE_TAG}" \
    -t "${IMAGE_NAME}:latest" \
    --file Dockerfile \
    "$PROJECT_ROOT"
else
  echo "==> ACR login (for docker push)..."
  az acr login --name "$ACR_NAME"

  echo "==> Docker build for $DOCKER_PLATFORM (required for Azure Container Apps)..."
  docker build \
    --platform "$DOCKER_PLATFORM" \
    -t "$ACR_LOGIN_SERVER/${IMAGE_NAME}:$IMAGE_TAG" \
    "$PROJECT_ROOT"

  echo "==> Docker push..."
  docker push "$ACR_LOGIN_SERVER/${IMAGE_NAME}:$IMAGE_TAG"
  docker tag "$ACR_LOGIN_SERVER/${IMAGE_NAME}:$IMAGE_TAG" "$ACR_LOGIN_SERVER/${IMAGE_NAME}:latest"
  docker push "$ACR_LOGIN_SERVER/${IMAGE_NAME}:latest"
fi

echo "==> Update Container App..."
az containerapp update \
  --name "$CONTAINER_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --image "$ACR_LOGIN_SERVER/${IMAGE_NAME}:$IMAGE_TAG"

echo "==> Ingress target port 8501 (Streamlit)..."
az containerapp ingress update \
  --name "$CONTAINER_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --target-port 8501

FQDN="$(az containerapp show \
  --name "$CONTAINER_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query "properties.configuration.ingress.fqdn" -o tsv 2>/dev/null || true)"

echo ""
echo "Done. Image: $ACR_LOGIN_SERVER/${IMAGE_NAME}:$IMAGE_TAG"
[[ -n "$FQDN" ]] && echo "App URL: https://$FQDN"
