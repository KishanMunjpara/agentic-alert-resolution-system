# PowerShell script to set up GitHub repository for temporary account
# Usage: .\setup_github_repo.ps1 -RepoName "your-repo-name"

param(
    [Parameter(Mandatory=$true)]
    [string]$RepoName
)

Write-Host "Setting up GitHub repository: $RepoName" -ForegroundColor Green
Write-Host "Account: KishanMunjpara (kishanmunjpara2710@gmail.com)" -ForegroundColor Yellow
Write-Host ""

# Check if git is initialized
if (-not (Test-Path .git)) {
    Write-Host "Error: Git repository not initialized!" -ForegroundColor Red
    exit 1
}

# Set local git config (doesn't affect global)
Write-Host "Setting local git config..." -ForegroundColor Cyan
git config user.name "KishanMunjpara"
git config user.email "kishanmunjpara2710@gmail.com"

Write-Host "✓ Git config set for this repository only" -ForegroundColor Green
Write-Host ""

# Check if remote already exists
$remoteExists = git remote get-url origin 2>$null
if ($remoteExists) {
    Write-Host "Remote 'origin' already exists: $remoteExists" -ForegroundColor Yellow
    $response = Read-Host "Do you want to update it? (y/n)"
    if ($response -eq "y" -or $response -eq "Y") {
        git remote set-url origin "https://github.com/KishanMunjpara/$RepoName.git"
        Write-Host "✓ Remote updated" -ForegroundColor Green
    } else {
        Write-Host "Keeping existing remote" -ForegroundColor Yellow
    }
} else {
    git remote add origin "https://github.com/KishanMunjpara/$RepoName.git"
    Write-Host "✓ Remote added" -ForegroundColor Green
}

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Create the repository on GitHub: https://github.com/new" -ForegroundColor White
Write-Host "   - Name: $RepoName" -ForegroundColor White
Write-Host "   - DO NOT initialize with README, .gitignore, or license" -ForegroundColor White
Write-Host ""
Write-Host "2. Push to GitHub:" -ForegroundColor White
Write-Host "   git push -u origin main" -ForegroundColor Yellow
Write-Host ""
Write-Host "3. When prompted for credentials:" -ForegroundColor White
Write-Host "   - Username: KishanMunjpara" -ForegroundColor Yellow
Write-Host "   - Password: Use Personal Access Token (not password)" -ForegroundColor Yellow
Write-Host "   - Generate token: https://github.com/settings/tokens" -ForegroundColor Yellow
Write-Host ""
Write-Host "Repository is ready to push!" -ForegroundColor Green

