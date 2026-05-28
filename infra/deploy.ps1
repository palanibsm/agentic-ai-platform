# =============================================================================
# Agentic AI Platform - Cloud Run Deployment Script
# Usage: .\infra\deploy.ps1
# =============================================================================

param(
    [string]$Project  = "ai-agent-project-497604",
    [string]$Region   = "us-central1",
    [string]$Registry = "us-central1-docker.pkg.dev"
)

# Native gcloud commands return non-zero for "not found" checks - don't treat as fatal
$ErrorActionPreference = "Continue"

$Repo      = "agentic-ai"
$SA_NAME   = "agentic-ai-runner"
$SA_EMAIL  = "$SA_NAME@$Project.iam.gserviceaccount.com"
$IMAGE_BASE = "$Registry/$Project/$Repo"

Write-Host "`n=== Agentic AI Platform - Cloud Run Deploy ===" -ForegroundColor Cyan

Write-Host "Project : $Project"
Write-Host "Region  : $Region"
Write-Host "Registry: $IMAGE_BASE`n"

# ── 1. Enable required GCP APIs ───────────────────────────────────────────────
Write-Host "[1/7] Enabling GCP APIs..." -ForegroundColor Yellow
gcloud services enable `
    run.googleapis.com `
    artifactregistry.googleapis.com `
    cloudbuild.googleapis.com `
    secretmanager.googleapis.com `
    pubsub.googleapis.com `
    storage.googleapis.com `
    --project $Project

# ── 2. Create Artifact Registry repo ─────────────────────────────────────────
Write-Host "[2/7] Creating Artifact Registry repo..." -ForegroundColor Yellow
$repoExists = gcloud artifacts repositories describe $Repo --location $Region --project $Project 2>&1
if ($LASTEXITCODE -ne 0) {
    gcloud artifacts repositories create $Repo `
        --repository-format docker `
        --location $Region `
        --project $Project `
        --description "Agentic AI Platform images"
    if ($LASTEXITCODE -ne 0) { throw "Failed to create Artifact Registry repo" }
}
gcloud auth configure-docker "$Region-docker.pkg.dev" --quiet

# ── 3. Create service account + IAM roles ─────────────────────────────────────
Write-Host "[3/7] Setting up service account..." -ForegroundColor Yellow
$null = gcloud iam service-accounts describe $SA_EMAIL --project $Project 2>&1
if ($LASTEXITCODE -ne 0) {
    gcloud iam service-accounts create $SA_NAME `
        --display-name "Agentic AI Platform Runner" `
        --project $Project
}

$roles = @(
    "roles/pubsub.publisher",
    "roles/secretmanager.secretAccessor",
    "roles/storage.objectAdmin",   # needed for Qdrant GCS volume mount (read/write/delete)
    "roles/logging.logWriter"
)
foreach ($role in $roles) {
    gcloud projects add-iam-policy-binding $Project `
        --member "serviceAccount:$SA_EMAIL" `
        --role $role `
        --quiet 2>&1 | Out-Null
}
Write-Host "  Service account $SA_EMAIL configured." -ForegroundColor Green

# ── 4. Store secrets in Secret Manager ───────────────────────────────────────
Write-Host "[4/7] Storing secrets in Secret Manager..." -ForegroundColor Yellow

function Set-Secret {
    param([string]$Name, [string]$EnvVar)
    $val = [System.Environment]::GetEnvironmentVariable($EnvVar)
    if (-not $val) {
        # Try reading from ../.env
        $envFile = Join-Path $PSScriptRoot "../.env"
        if (Test-Path $envFile) {
            $line = Get-Content $envFile | Where-Object { $_ -match "^$EnvVar=" } | Select-Object -First 1
            if ($line) { $val = $line.Split("=", 2)[1].Trim('"').Trim("'") }
        }
    }
    if (-not $val) { Write-Warning "  $EnvVar not found - skipping secret $Name"; return }

    $null = gcloud secrets describe $Name --project $Project 2>&1
    if ($LASTEXITCODE -ne 0) {
        gcloud secrets create $Name --project $Project --replication-policy automatic
    }
    $tmpFile = Join-Path $env:TEMP "gcp_secret_tmp.txt"
    $utf8NoBOM = [System.Text.UTF8Encoding]::new($false)
    [System.IO.File]::WriteAllText($tmpFile, $val.Trim(), $utf8NoBOM)
    gcloud secrets versions add $Name --data-file=$tmpFile --project $Project
    Remove-Item $tmpFile
    Write-Host "  Secret $Name stored." -ForegroundColor Green
}

Set-Secret "anthropic-api-key"   "ANTHROPIC_API_KEY"
Set-Secret "litellm-master-key"  "LITELLM_MASTER_KEY"
Set-Secret "openai-api-key"      "OPENAI_API_KEY"

# ── 5. Build and push images via Cloud Build ──────────────────────────────────
Write-Host "[5/7] Building and pushing images..." -ForegroundColor Yellow

$ROOT = Join-Path $PSScriptRoot ".."

# Build backend services (no build args needed)
$backendServices = @(
    @{ name = "governance";  ctx = "services/governance";  tag = "governance" },
    @{ name = "llm-gateway"; ctx = "services/llm-gateway"; tag = "llm-gateway" },
    @{ name = "rag-service"; ctx = "services/rag-service"; tag = "rag-service" },
    @{ name = "agent-core";  ctx = "services/agent-core";  tag = "agent-core" }
)

foreach ($svc in $backendServices) {
    $img = "$IMAGE_BASE/$($svc.tag):latest"
    Write-Host "  Building $($svc.name) → $img" -ForegroundColor Cyan
    $ctxPath = Join-Path $ROOT $svc.ctx
    gcloud builds submit $ctxPath `
        --tag $img `
        --project $Project `
        --quiet
    Write-Host "  $($svc.name) pushed." -ForegroundColor Green
}
# Portal and ide-chat are built after agent-core is deployed (need its URL as build arg)

# ── 6. Deploy services to Cloud Run ──────────────────────────────────────────
Write-Host "[6/7] Deploying to Cloud Run..." -ForegroundColor Yellow

# Read non-secret env vars from .env
$envFile = Join-Path $ROOT ".env"
function Get-EnvVal([string]$key) {
    $line = Get-Content $envFile | Where-Object { $_ -match "^$key=" } | Select-Object -First 1
    if ($line) { return $line.Split("=", 2)[1].Trim('"').Trim("'") }
    return ""
}

$GCP_PROJECT_ID  = Get-EnvVal "GCP_PROJECT_ID"
$GCP_REGION      = Get-EnvVal "GCP_REGION"
$GCS_BUCKET_NAME = Get-EnvVal "GCS_BUCKET_NAME"

# Common deploy flags
$commonFlags = @(
    "--region", $Region,
    "--project", $Project,
    "--service-account", $SA_EMAIL,
    "--allow-unauthenticated",
    "--quiet"
)

# 6a. Qdrant — deploy from public image (no build needed)
Write-Host "  Deploying qdrant..." -ForegroundColor Cyan
$QDRANT_BUCKET = "$Project-qdrant-storage"
# Ensure the GCS bucket for Qdrant storage exists
$null = gcloud storage buckets describe "gs://$QDRANT_BUCKET" 2>&1
if ($LASTEXITCODE -ne 0) {
    gcloud storage buckets create "gs://$QDRANT_BUCKET" --location $Region --project $Project
    Write-Host "  Created Qdrant storage bucket: $QDRANT_BUCKET" -ForegroundColor Green
}

gcloud run deploy qdrant `
    --image "qdrant/qdrant:v1.9.2" `
    --port 6333 `
    --set-env-vars "QDRANT__STORAGE__STORAGE_PATH=/qdrant/storage" `
    --add-volume "name=qdrant-storage,type=cloud-storage,bucket=$QDRANT_BUCKET" `
    --add-volume-mount "volume=qdrant-storage,mount-path=/qdrant/storage" `
    --memory 1Gi `
    @commonFlags

$QDRANT_URL = (gcloud run services describe qdrant --region $Region --project $Project --format "value(status.url)")
Write-Host "  qdrant: $QDRANT_URL" -ForegroundColor Green

# 6b. Governance
Write-Host "  Deploying governance..." -ForegroundColor Cyan
gcloud run deploy governance `
    --image "$IMAGE_BASE/governance:latest" `
    --port 8003 `
    --set-env-vars "GCP_PROJECT_ID=$GCP_PROJECT_ID,GCP_REGION=$GCP_REGION" `
    @commonFlags

$GOVERNANCE_URL = (gcloud run services describe governance --region $Region --project $Project --format "value(status.url)")
Write-Host "  governance: $GOVERNANCE_URL" -ForegroundColor Green

# 6c. LLM Gateway
Write-Host "  Deploying llm-gateway..." -ForegroundColor Cyan
gcloud run deploy llm-gateway `
    --image "$IMAGE_BASE/llm-gateway:latest" `
    --port 4000 `
    --set-env-vars "GCP_PROJECT_ID=$GCP_PROJECT_ID" `
    --set-secrets "ANTHROPIC_API_KEY=anthropic-api-key:latest,LITELLM_MASTER_KEY=litellm-master-key:latest,OPENAI_API_KEY=openai-api-key:latest" `
    --memory 1Gi `
    @commonFlags

$LLM_GATEWAY_URL = (gcloud run services describe llm-gateway --region $Region --project $Project --format "value(status.url)")
Write-Host "  llm-gateway: $LLM_GATEWAY_URL" -ForegroundColor Green

# 6c. RAG Service
Write-Host "  Deploying rag-service..." -ForegroundColor Cyan
gcloud run deploy rag-service `
    --image "$IMAGE_BASE/rag-service:latest" `
    --port 8001 `
    --set-env-vars "GCP_PROJECT_ID=$GCP_PROJECT_ID,GCP_REGION=$GCP_REGION,GCS_BUCKET_NAME=$GCS_BUCKET_NAME,QDRANT_URL=$QDRANT_URL,QDRANT_COLLECTION=knowledge-base" `
    --memory 2Gi `
    --cpu 2 `
    @commonFlags

$RAG_SERVICE_URL = (gcloud run services describe rag-service --region $Region --project $Project --format "value(status.url)")
Write-Host "  rag-service: $RAG_SERVICE_URL" -ForegroundColor Green

# 6d. Agent Core
Write-Host "  Deploying agent-core..." -ForegroundColor Cyan
gcloud run deploy agent-core `
    --image "$IMAGE_BASE/agent-core:latest" `
    --port 8002 `
    --set-env-vars "GCP_PROJECT_ID=$GCP_PROJECT_ID,GCP_REGION=$GCP_REGION,LLM_GATEWAY_URL=$LLM_GATEWAY_URL,RAG_SERVICE_URL=$RAG_SERVICE_URL,GOVERNANCE_URL=$GOVERNANCE_URL,AGENT_DEFAULT_MODEL=claude-sonnet" `
    --set-secrets "ANTHROPIC_API_KEY=anthropic-api-key:latest,LITELLM_MASTER_KEY=litellm-master-key:latest" `
    --memory 1Gi `
    --timeout 120 `
    @commonFlags

$AGENT_CORE_URL = (gcloud run services describe agent-core --region $Region --project $Project --format "value(status.url)")
Write-Host "  agent-core: $AGENT_CORE_URL" -ForegroundColor Green

# 6e. Portal - build with agent-core URL baked in, then push and deploy
Write-Host "  Building portal with NEXT_PUBLIC_AGENT_URL=$AGENT_CORE_URL..." -ForegroundColor Cyan
$portalCtx = Join-Path $ROOT "apps/portal"
$portalImg  = "$IMAGE_BASE/portal:latest"

# Cloud Build supports substitutions for build args
$buildConfig = @"
steps:
- name: 'gcr.io/cloud-builders/docker'
  args:
    - build
    - --build-arg
    - NEXT_PUBLIC_AGENT_URL=$AGENT_CORE_URL
    - -t
    - $portalImg
    - .
images:
- $portalImg
"@
$tmpYaml = Join-Path $env:TEMP "portal-cloudbuild.yaml"
$buildConfig | Set-Content $tmpYaml

gcloud builds submit $portalCtx `
    --config $tmpYaml `
    --project $Project `
    --quiet

Remove-Item $tmpYaml

gcloud run deploy portal `
    --image $portalImg `
    --port 3000 `
    --set-env-vars "NEXT_PUBLIC_AGENT_URL=$AGENT_CORE_URL" `
    @commonFlags

$PORTAL_URL = (gcloud run services describe portal --region $Region --project $Project --format "value(status.url)")
Write-Host "  portal: $PORTAL_URL" -ForegroundColor Green

# 6f. IDE Chat - build with agent-core URL, then deploy
Write-Host "  Building ide-chat with NEXT_PUBLIC_AGENT_URL=$AGENT_CORE_URL..." -ForegroundColor Cyan
$ideChatCtx = Join-Path $ROOT "apps/ide-chat"
$ideChatImg  = "$IMAGE_BASE/ide-chat:latest"

$ideBuildConfig = @"
steps:
- name: 'gcr.io/cloud-builders/docker'
  args:
    - build
    - --build-arg
    - NEXT_PUBLIC_AGENT_URL=$AGENT_CORE_URL
    - -t
    - $ideChatImg
    - .
images:
- $ideChatImg
"@
$ideTmpYaml = Join-Path $env:TEMP "ide-chat-cloudbuild.yaml"
$ideBuildConfig | Set-Content $ideTmpYaml

gcloud builds submit $ideChatCtx `
    --config $ideTmpYaml `
    --project $Project `
    --quiet

Remove-Item $ideTmpYaml

gcloud run deploy ide-chat `
    --image $ideChatImg `
    --port 3001 `
    --set-env-vars "AGENT_CORE_URL=$AGENT_CORE_URL,NEXT_PUBLIC_AGENT_URL=$AGENT_CORE_URL" `
    @commonFlags

$IDE_CHAT_URL = (gcloud run services describe ide-chat --region $Region --project $Project --format "value(status.url)")
Write-Host "  ide-chat: $IDE_CHAT_URL" -ForegroundColor Green

# ── 7. Summary ────────────────────────────────────────────────────────────────
Write-Host "`n[7/7] Deployment complete!" -ForegroundColor Yellow
Write-Host ""
Write-Host "=== Cloud Run Service URLs ===" -ForegroundColor Cyan
Write-Host "  portal      : $PORTAL_URL" -ForegroundColor Green
Write-Host "  ide-chat    : $IDE_CHAT_URL" -ForegroundColor Green
Write-Host "  agent-core  : $AGENT_CORE_URL" -ForegroundColor Green
Write-Host "  rag-service : $RAG_SERVICE_URL" -ForegroundColor Green
Write-Host "  llm-gateway : $LLM_GATEWAY_URL" -ForegroundColor Green
Write-Host "  governance  : $GOVERNANCE_URL" -ForegroundColor Green
Write-Host "  qdrant      : $QDRANT_URL" -ForegroundColor Green
Write-Host ""
Write-Host "Portal   : $PORTAL_URL" -ForegroundColor Cyan
Write-Host "IDE Chat : $IDE_CHAT_URL" -ForegroundColor Cyan
