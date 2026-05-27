# =============================================================================
# Set up Cloud Build trigger for CI/CD
# Run once after connecting your repo in Cloud Build console.
# =============================================================================

param(
    [string]$Project = "ai-agent-project-497604",
    [string]$Region  = "us-central1",
    [string]$Repo    = "your-github-repo-name",
    [string]$Owner   = "your-github-username"
)

# Create the Terraform state bucket (one-time)
Write-Host "Creating Terraform state bucket..." -ForegroundColor Yellow
gcloud storage buckets create "gs://$Project-tf-state" `
    --location $Region `
    --project $Project 2>&1 | Out-Null
Write-Host "  gs://$Project-tf-state ready" -ForegroundColor Green

# Create Cloud Build trigger on push to main
Write-Host "Creating Cloud Build trigger..." -ForegroundColor Yellow
gcloud builds triggers create github `
    --project $Project `
    --region $Region `
    --repo-name $Repo `
    --repo-owner $Owner `
    --branch-pattern "^main$" `
    --build-config "infra/cloudbuild.yaml" `
    --name "deploy-on-push-to-main" `
    --description "Build and deploy all services on push to main"

Write-Host "Done. Push to main branch will now trigger a full build + deploy." -ForegroundColor Green
Write-Host ""
Write-Host "Next: connect your GitHub repo in Cloud Build console:" -ForegroundColor Cyan
Write-Host "  https://console.cloud.google.com/cloud-build/triggers?project=$Project" -ForegroundColor Cyan
