# =============================================================================
# Set up Cloud Build GitHub trigger for CI/CD
#
# Prerequisites (one-time, do this BEFORE running this script):
#   1. Go to: https://console.cloud.google.com/cloud-build/triggers?project=ai-agent-project-497604
#   2. Click "Connect Repository"
#   3. Choose "GitHub (Cloud Build GitHub App)"
#   4. Authenticate with GitHub and select: palanibsm/agentic-ai-platform
#   5. Click "Connect" — do NOT create a trigger in the wizard, exit after connecting
#   Then run this script.
#
# Usage: .\infra\setup-cicd.ps1
# =============================================================================

param(
    [string]$Project = "ai-agent-project-497604",
    [string]$Region  = "us-central1",
    [string]$Repo    = "agentic-ai-platform",
    [string]$Owner   = "palanibsm"
)

$ErrorActionPreference = "Continue"

Write-Host "`n=== Agentic AI Platform - CI/CD Setup ===" -ForegroundColor Cyan
Write-Host "Project : $Project"
Write-Host "Repo    : $Owner/$Repo`n"

# ── 1. Grant Cloud Build SA permission to deploy Cloud Run ───────────────────
Write-Host "[1/3] Granting Cloud Build service account permissions..." -ForegroundColor Yellow

$CB_SA = "$(gcloud projects describe $Project --format='value(projectNumber)')@cloudbuild.gserviceaccount.com"
Write-Host "  Cloud Build SA: $CB_SA"

$cbRoles = @(
    "roles/run.admin",
    "roles/iam.serviceAccountUser",
    "roles/artifactregistry.writer",
    "roles/storage.objectViewer"
)
foreach ($role in $cbRoles) {
    gcloud projects add-iam-policy-binding $Project `
        --member "serviceAccount:$CB_SA" `
        --role $role `
        --quiet 2>&1 | Out-Null
    Write-Host "  Granted $role" -ForegroundColor Green
}

# ── 2. Create Cloud Build trigger ────────────────────────────────────────────
Write-Host "`n[2/3] Creating Cloud Build trigger..." -ForegroundColor Yellow

# Check if trigger already exists
$existingTrigger = gcloud builds triggers list `
    --project $Project `
    --region $Region `
    --filter="name=deploy-on-push-to-main" `
    --format="value(name)" 2>&1

if ($existingTrigger -and $existingTrigger -notmatch "Listed 0") {
    Write-Host "  Trigger 'deploy-on-push-to-main' already exists — skipping." -ForegroundColor Yellow
} else {
    gcloud builds triggers create github `
        --project $Project `
        --region $Region `
        --repo-name $Repo `
        --repo-owner $Owner `
        --branch-pattern "^main$" `
        --build-config "infra/cloudbuild.yaml" `
        --name "deploy-on-push-to-main" `
        --description "Build and deploy all services on push to main" `
        --quiet

    if ($LASTEXITCODE -eq 0) {
        Write-Host "  Trigger created successfully." -ForegroundColor Green
    } else {
        Write-Host "  Trigger creation failed." -ForegroundColor Red
        Write-Host "  Make sure you connected the repo first -- see script header comments." -ForegroundColor Yellow
    }
}

# ── 3. Run a manual trigger test ────────────────────────────────────────────
Write-Host "`n[3/3] Running trigger manually to verify..." -ForegroundColor Yellow

$TRIGGER_NAME = "deploy-on-push-to-main"
$null = gcloud builds triggers run $TRIGGER_NAME `
    --project $Project `
    --region $Region `
    --branch main `
    --quiet 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "  Manual trigger fired. Monitor at:" -ForegroundColor Green
    Write-Host "  https://console.cloud.google.com/cloud-build/builds?project=$Project" -ForegroundColor Cyan
} else {
    Write-Host "  Could not fire manual trigger — check the console link above." -ForegroundColor Yellow
}

Write-Host "`n=== Done ===" -ForegroundColor Cyan
Write-Host "From now on, every 'git push origin main' will automatically:"
Write-Host "  1. Build all 6 service images in parallel"
Write-Host "  2. Push to Artifact Registry (tagged with commit SHA)"
Write-Host "  3. Deploy to Cloud Run in dependency order"
Write-Host ""
Write-Host "Monitor builds: https://console.cloud.google.com/cloud-build/builds?project=$Project"
